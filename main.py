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

class AnnouncementDownloader:
    """公告下载器主类"""
    
    def __init__(self):
        self.config = Config()
        self.cache_manager = CacheManager(cache_dir=Config.CACHE_DIR)
        self.stock_searcher = StockSearcher(self.cache_manager)
        self.plate_parser = PlateParser(self.cache_manager)
        self.announcement_fetcher = AnnouncementFetcher(self.cache_manager)
        self.file_downloader = FileDownloader()
    
    def run(self, stock_code, category_filter=None):
        """
        运行下载流程
        
        Args:
            stock_code (str): 股票代码
            category_filter (str|None): 分类过滤（中文名或key）
        """
        print(f"开始处理股票: {stock_code}")
        print("=" * 50)
        
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
        
        # 4. 获取分类列表
        print("\n步骤4: 获取分类列表")
        category_list = self.config.get_category_list()
        if not category_list:
            print("错误: 无法获取分类列表")
            return False
        
        print(f"找到 {len(category_list)} 个分类")
        
        # 如果指定了分类过滤，只保留匹配的分类
        if category_filter:
            filtered = []
            for item in category_list:
                # key精确匹配，value支持模糊匹配
                if category_filter == item.get('key') or (item.get('value') and category_filter in item.get('value')):
                    filtered.append(item)
            if not filtered:
                print(f"未找到指定分类: {category_filter}")
                return False
            category_list = filtered
            print(f"仅下载指定分类(支持中文模糊): {category_filter}")
        
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
            
            # 使用生成器逐条获取和下载公告
            category_downloaded = 0
            announcement_count = 0
            
            for announcement in self.announcement_fetcher.fetch_announcements_generator(
                stock_info['code'],
                stock_info['orgId'],
                plate,
                category_key,
                category_value=category_name
            ):
                announcement_count += 1
                
                # 立即下载当前公告
                success = self.file_downloader.download_announcement(
                    announcement,
                    download_dir,
                    category_name
                )
                if success:
                    category_downloaded += 1
                
                # 每下载10个文件显示一次进度
                if announcement_count % 10 == 0:
                    print(f"分类 {category_name} 进度: {announcement_count} 个公告，成功下载 {category_downloaded} 个")
            
            print(f"分类 {category_name} 下载完成: {category_downloaded}/{announcement_count}")
            total_downloaded += category_downloaded
        
        print("\n" + "=" * 50)
        print(f"下载完成! 总共下载 {total_downloaded} 个文件")
        print(f"文件保存在: {download_dir}")
        
        # 显示缓存信息
        cache_info = self.cache_manager.get_cache_info()
        print(f"缓存信息: 股票搜索{cache_info['top_search_count']}个, 股票页面{cache_info['stock_count']}个, 公告查询{cache_info['announcement_count']}个")
        
        return True

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python main.py <股票代码> [分类名或key]")
        print("示例: python main.py 601225 年度报告")
        return
    
    stock_code = sys.argv[1]
    category_filter = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 创建下载器实例并运行
    downloader = AnnouncementDownloader()
    success = downloader.run(stock_code, category_filter)
    
    if success:
        print("\n程序执行成功!")
    else:
        print("\n程序执行失败!")
        sys.exit(1)

if __name__ == "__main__":
    main() 