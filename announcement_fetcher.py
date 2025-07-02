"""
公告获取模块 - 负责获取公告列表
"""
import requests
import json

class AnnouncementFetcher:
    """公告获取类"""
    
    def __init__(self, cache_manager=None):
        self.query_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self.cache_manager = cache_manager
    
    def get_plate_param(self, plate):
        """
        根据板块代码获取plate参数
        
        Args:
            plate (str): 板块代码
            
        Returns:
            str: plate参数值
        """
        if plate == 'szse':
            return 'sz'
        elif plate == 'sse':
            return 'sh'
        elif plate == 'bj':
            return 'bj;third'
        else:
            return plate
    
    def fetch_announcements_generator(self, stock_code, org_id, plate, category, page_size=30, category_value=None):
        """
        获取公告列表的生成器，逐页返回公告
        
        Args:
            stock_code (str): 股票代码
            org_id (str): 机构ID
            plate (str): 板块代码
            category (str): 公告分类
            page_size (int): 每页数量
            category_value (str): 分类中文名
        Yields:
            dict: 单个公告信息
        """
        page_num = 1
        plate_param = self.get_plate_param(plate)
        total_count = 0
        
        while True:
            try:
                data = {
                    'stock': f"{stock_code},{org_id}",
                    'tabName': 'fulltext',
                    'pageSize': page_size,
                    'pageNum': page_num,
                    'column': plate,
                    'category': category,
                    'plate': plate_param,
                    'seDate': '',
                    'searchkey': '',
                    'secid': '',
                    'sortName': '',
                    'sortType': '',
                    'isHLtitle': 'true'
                }
                
                # 检查缓存
                if self.cache_manager:
                    cached_result = self.cache_manager.load_announcement_cache(
                        data['stock'], page_num, category, plate, plate_param, 
                        data['searchkey'], data['seDate'], category_value
                    )
                    if cached_result:
                        result = cached_result
                    else:
                        # 发送请求
                        response = requests.post(self.query_url, data=data, headers=self.headers)
                        response.raise_for_status()
                        result = response.json()
                        
                        # 保存到缓存
                        self.cache_manager.save_announcement_cache(
                            data['stock'], page_num, category, plate, plate_param,
                            data['searchkey'], data['seDate'], result, category_value
                        )
                else:
                    # 没有缓存管理器，直接发送请求
                    response = requests.post(self.query_url, data=data, headers=self.headers)
                    response.raise_for_status()
                    result = response.json()
                
                if 'announcements' in result:
                    announcements = result['announcements']
                    if not announcements:
                        announcements = []
                    
                    print(f"第{page_num}页获取到 {len(announcements)} 条公告")
                    
                    # 逐条返回公告
                    for announcement in announcements:
                        total_count += 1
                        yield announcement
                    
                    # 检查是否还有更多页
                    if not result.get('hasMore', False):
                        break
                    
                    page_num += 1
                else:
                    print(f"第{page_num}页响应格式异常")
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"请求公告列表失败 (第{page_num}页): {e}")
                break
            except json.JSONDecodeError as e:
                print(f"解析公告列表响应失败 (第{page_num}页): {e}")
                break
            except Exception as e:
                print(f"获取公告列表时发生错误 (第{page_num}页): {e}")
                break
        
        print(f"总共获取到 {total_count} 条公告")
    
    def fetch_announcements(self, stock_code, org_id, plate, category, page_size=30):
        """
        获取公告列表（保持向后兼容）
        
        Args:
            stock_code (str): 股票代码
            org_id (str): 机构ID
            plate (str): 板块代码
            category (str): 公告分类
            page_size (int): 每页数量
            
        Returns:
            list: 公告列表
        """
        return list(self.fetch_announcements_generator(stock_code, org_id, plate, category, page_size)) 