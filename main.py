"""
主程序 - 巨潮资讯网公告下载器
"""
import os
import sys
from config import Config
from cache_manager import CacheManager
from stock_searcher import StockSearcher
from plate_parser import PlateParser
from announcement_fetcher import AnnouncementFetcher
from file_downloader import FileDownloader
from dotenv import load_dotenv

class AnnouncementDownloader:
    """公告下载器主类"""
    
    def __init__(self):
        self.config = Config()
        self.cache_manager = CacheManager(cache_dir=Config.CACHE_DIR)
        self.stock_searcher = StockSearcher(self.cache_manager)
        self.plate_parser = PlateParser(self.cache_manager)
        self.announcement_fetcher = AnnouncementFetcher(self.cache_manager)
        self.file_downloader = FileDownloader()
    
    def run(self, stock_code, category_filter=None, incremental_update=False, market='a'):
        """
        运行下载流程
        
        Args:
            stock_code (str): 股票代码
            category_filter (str|None): 分类过滤（中文名或key）
            incremental_update (bool): 是否增量更新
            market (str): 市场 'a'(A股巨潮) 或 'hk'(港股HKEXnews)
        """
        print(f"开始处理股票: {stock_code}")
        print("=" * 50)

        # 港股走独立数据源（HKEXnews），跳过巨潮的 搜索/板块/分类 流程
        if market == 'hk':
            return self._run_hk(stock_code, incremental_update, category_filter)

        # 1. 加载配置文件
        print("步骤1: 加载配置文件")
        self.config.load_list_search()
        if not self.config.list_search:
            print("错误: 无法加载配置文件")
            return False
        
        # 2. 搜索股票信息
        print("\n步骤2: 搜索股票信息")
        stock_info = self.stock_searcher.search_stock(stock_code)
        if not stock_info:
            print("错误: 无法获取股票信息")
            return False
        
        # 设置股票信息到配置
        self.config.set_stock_info(stock_info)
        # 设置缓存目录到股票专属目录
        self.cache_manager.set_stock(stock_info['code'], stock_info['zwjc'])
        
        # 3. 获取板块信息
        print("\n步骤3: 获取板块信息")
        plate = self.plate_parser.get_plate(
            stock_info['code'],
            stock_info['orgId'],
            stock_info['sjstsBond']
        )
        if not plate:
            print("错误: 无法获取板块信息")
            return False
        
        # 设置板块信息到配置
        self.config.set_plate(plate)

        # 港股自动路由：板块识别为 hke 时，跳过巨潮的分类流程，
        # 直接切换至 HKEXnews 下载分支（无需用户加 --market hk）。
        if plate == 'hke':
            print("检测到港股代码，自动切换至港股(HKEXnews)下载分支")
            return self._run_hk(stock_info['code'], incremental_update, category_filter,
                                stock_info.get('zwjc'))

        # 4. 获取分类列表
        print("\n步骤4: 获取分类列表")
        category_list = self.config.get_category_list()
        if not category_list:
            print("错误: 无法获取分类列表")
            return False
        
        print(f"找到 {len(category_list)} 个分类")
        
        # 获取只包含关键词
        include_keywords = self.config.get_include_keywords()
        if include_keywords:
            print(f"只包含关键词: {include_keywords}")
        
        # 获取排除关键字
        exclude_keywords = self.config.get_exclude_keywords()
        if exclude_keywords:
            print(f"排除关键字: {exclude_keywords}")
        
        # 如果指定了分类过滤，只保留匹配的分类
        if category_filter:
            # 支持逗号分隔的多个分类过滤
            for sep in [',', '，', ';', '；']:
                category_filter = category_filter.replace(sep, ',')
            filter_list = [f.strip() for f in category_filter.split(',')]
            filtered = []
            for item in category_list:
                # key，value精确匹配，
                for filter_item in filter_list:
                    if filter_item == item.get('key') or item.get('value') == filter_item:
                        filtered.append(item)
                        break  # 找到匹配项后跳出内层循环
            if not filtered:
                print(f"未找到指定分类: {category_filter}")
                return False
            category_list = filtered
            print(f"仅下载指定分类: {category_filter}")
        
        # 5. 创建下载目录
        stock_name = stock_info['zwjc']
        download_dir = os.path.join(self.config.download_base_dir, stock_name)
        os.makedirs(download_dir, exist_ok=True)
        
        # 6. 循环处理每个分类
        total_downloaded = 0
        
        for category_item in category_list:
            category_key = category_item.get('key', '')
            category_name = category_item.get('value', '')
            
            if not category_key or not category_name:
                continue
            
            print(f"\n处理分类: {category_name} ({category_key})")
            print("-" * 30)
            
            # 增量更新时不使用缓存
            fetcher = self.announcement_fetcher
            cache_manager_backup = None
            if incremental_update:
                cache_manager_backup = fetcher.cache_manager
                fetcher.cache_manager = None
            
            # 使用生成器逐条获取和下载公告
            category_downloaded = 0
            announcement_count = 0
            skip_this_category = False
            
            for announcement in fetcher.fetch_announcements_generator(
                stock_info['code'],
                stock_info['orgId'],
                plate,
                category_key,
                category_value=category_name
            ):
                announcement_count += 1
                title = announcement.get('announcementTitle', '')
                # 先判断只包含关键词
                if include_keywords and not any(kw in title for kw in include_keywords):
                    print(f"跳过公告: {title} (不包含指定关键词)")
                    continue
                # 再判断排除关键词
                if exclude_keywords and any(kw in title for kw in exclude_keywords):
                    print(f"跳过公告: {title} (命中排除关键字)")
                    continue
                # 立即下载当前公告
                result = self.file_downloader.download_announcement(
                    announcement,
                    download_dir,
                    category_name
                )
                if result == 'skip_category' and incremental_update:
                    print(f"增量更新：遇到已存在文件，跳过当前分类 {category_name}")
                    skip_this_category = True
                    break
                if result is True:
                    category_downloaded += 1
                
                # 每下载10个文件显示一次进度
                if announcement_count % 10 == 0:
                    print(f"分类 {category_name} 进度: {announcement_count} 个公告，成功下载 {category_downloaded} 个")
            
            print(f"分类 {category_name} 下载完成: {category_downloaded}/{announcement_count}")
            total_downloaded += category_downloaded

            # 恢复cache_manager
            if incremental_update and cache_manager_backup is not None:
                fetcher.cache_manager = cache_manager_backup
            
            if skip_this_category:
                continue
        
        print("\n" + "=" * 50)
        print(f"下载完成! 总共下载 {total_downloaded} 个文件")
        print(f"文件保存在: {download_dir}")
        
        # 显示缓存信息
        cache_info = self.cache_manager.get_cache_info()
        print(f"缓存信息: 股票搜索{cache_info['top_search_count']}个, 股票页面{cache_info['stock_count']}个, 公告查询{cache_info['announcement_count']}个")
        
        return True

    def _run_hk(self, stock_code, incremental_update=False, category_filter=None,
                sec_name_hint=None):
        """
        港股(HKEXnews)下载分支：复用 FileDownloader，按类别分子目录。
        兼容 A股原有逻辑：CATEGORY_FILTER 限定分类、INCLUDE/EXCLUDE_KEYWORDS 过滤标题。
        sec_name_hint: A股搜索返回的简体简称(zwjc)，优先作目录名/文件名。
        """
        from hk_fetcher import HKAnnouncementFetcher

        print("市场: 港股 (HKEXnews)")
        fetcher = HKAnnouncementFetcher()
        announcements = fetcher.fetch(stock_code, sec_name_hint=sec_name_hint)
        if not announcements:
            print("未找到符合条件的港股公告（年报/半年报/一季报/三季报/业务更新/业绩公告）")
            return False

        stock_name = sec_name_hint or announcements[0]['secName'] or f"HK{stock_code.zfill(5)}"
        download_dir = os.path.join(self.config.download_base_dir, stock_name)
        os.makedirs(download_dir, exist_ok=True)

        # 按类别分组（年报/半年报/一季报/三季报/业务更新/业绩公告 -> 子目录）
        by_cat = {}
        for a in announcements:
            by_cat.setdefault(a['category'], []).append(a)

        # 分类过滤（兼容 A股逻辑：CATEGORY_FILTER 限定只下某些类）。
        # 港股分类名与 A股不同，做一层轻量别名映射，让用户用 A股习惯词也能命中。
        if category_filter:
            for sep in [',', '，', ';', '；']:
                category_filter = category_filter.replace(sep, ',')
            filters = [f.strip() for f in category_filter.split(',') if f.strip()]
            if filters:
                # 港股分类名采用 A股习惯：年报 / 半年报 / 一季报 / 三季报 / 业务更新 / 业绩公告
                # 别名映射：用户用 A股习惯词(中报/中期/季报/季度 等)也能命中
                alias = {
                    '半年报': '半年报', '中报': '半年报', '中期报告': '半年报', '中期': '半年报',
                    'interim': '半年报', 'interim report': '半年报', '半年': '半年报', '半年度': '半年报',
                    '年报': '年报', '年度报告': '年报', 'annual': '年报', 'annual report': '年报',
                    '一季报': '一季报', '第一季度': '一季报', '第一季': '一季报',
                    '三季报': '三季报', '第三季度': '三季报', '第三季': '三季报',
                    '业绩公告': '业绩公告', '業績公告': '业绩公告', '業績': '业绩公告',
                    '业绩': '业绩公告', 'results': '业绩公告',
                    '业务更新': '业务更新', '業務更新': '业务更新',
                    '最新业务状况': '业务更新', '业务状况': '业务更新',
                }
                # 泛指"季报/季度"展开为一季报+三季报（A股习惯下一季/三季分列，但用户写"季报"是想要两者）
                broad = {'季报', '季度', '季度报告', 'quarterly', 'quarterly report'}
                keep = set()
                for f in filters:
                    fl = f.lower()
                    if fl in broad:
                        keep.add('一季报')
                        keep.add('三季报')
                        continue
                    keep.add(alias.get(fl, f))   # 未命中别名则按原名匹配
                by_cat = {c: items for c, items in by_cat.items() if c in keep}
                if not by_cat:
                    print(f"未找到指定分类: {category_filter}（港股可用分类: 年报/半年报/一季报/三季报/业务更新/业绩公告）")
                    return False
                print(f"仅下载指定分类(映射后): {sorted(keep)}")

        # 关键词过滤（与 A股逻辑一致：先只含、再排除）
        include_keywords = self.config.get_include_keywords()
        exclude_keywords = self.config.get_exclude_keywords()
        if include_keywords:
            print(f"只包含关键词: {include_keywords}")
        if exclude_keywords:
            print(f"排除关键字: {exclude_keywords}")

        total_downloaded = 0
        print(f"找到 {len(announcements)} 个公告，涉及分类: {list(by_cat.keys())}")

        for category_name, items in by_cat.items():
            print(f"\n处理分类: {category_name} ({len(items)} 个)")
            print("-" * 30)
            cat_downloaded = 0
            for idx, announcement in enumerate(items, 1):
                title = announcement.get('announcementTitle', '')
                # 先判断只包含关键词
                if include_keywords and not any(kw in title for kw in include_keywords):
                    continue
                # 再判断排除关键词
                if exclude_keywords and any(kw in title for kw in exclude_keywords):
                    continue
                result = self.file_downloader.download_announcement(
                    announcement, download_dir, category_name
                )
                # 增量模式下：已存在的文件返回 'skip_category'，仅跳过该文件本身，
                # 继续处理本分类其余文件（不能因首个文件已存在就放弃整个分类，
                # 否则在文件名变化/存在缺口时会漏下本应下载的文件）。
                if result == 'skip_category':
                    continue
                if result is True:
                    cat_downloaded += 1
                if idx % 10 == 0:
                    print(f"分类 {category_name} 进度: {idx} 个，成功下载 {cat_downloaded} 个")
            print(f"分类 {category_name} 下载完成: {cat_downloaded}/{len(items)}")
            total_downloaded += cat_downloaded

        print("\n" + "=" * 50)
        print(f"下载完成! 总共下载 {total_downloaded} 个文件")
        print(f"文件保存在: {download_dir}")
        return True

def main():
    """主函数"""
    load_dotenv()
    # 市场：默认 A股；支持 --market hk 或环境变量 MARKET=hk
    market = os.getenv("MARKET", "a").lower()
    args = sys.argv[1:]
    if "--market" in args:
        i = args.index("--market")
        if i + 1 < len(args):
            market = args[i + 1].lower()
        del args[i:i + 2]

    stock_code = None
    category_filter = None
    # 优先命令行参数
    if len(args) >= 1:
        stock_code = args[0]
        category_filter = args[1] if len(args) > 1 else None
    else:
        # 从环境变量读取
        stock_code = os.getenv("STOCK_CODE")
        category_filter = os.getenv("CATEGORY_FILTER")
        if not stock_code:
            print("使用方法: python main.py <股票代码> [分类名或key] [--market hk] 或在.env中设置")
            print("示例(A股): python main.py 601225 年度报告")
            print("示例(港股): python main.py 00700 --market hk")
            print("或在.env中添加: STOCK_CODE=601225  (港股另设 MARKET=hk)")
            return
    # 增量更新参数
    incremental_update = os.getenv("INCREMENTAL_UPDATE", "false").lower() == "true"
    # 创建下载器实例并运行
    downloader = AnnouncementDownloader()
    success = downloader.run(stock_code, category_filter, incremental_update, market)
    if success:
        print("\n程序执行成功!")
    else:
        print("\n程序执行失败!")
        sys.exit(1)

if __name__ == "__main__":
    main() 