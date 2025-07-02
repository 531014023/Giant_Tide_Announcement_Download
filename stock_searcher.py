"""
股票搜索模块 - 负责查询股票基本信息
"""
import requests
import json

class StockSearcher:
    """股票搜索类"""
    
    def __init__(self, cache_manager=None):
        self.search_url = "https://www.cninfo.com.cn/new/information/topSearch/query"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self.cache_manager = cache_manager
    
    def search_stock(self, stock_code, max_num=10):
        """
        搜索股票基本信息
        
        Args:
            stock_code (str): 股票代码
            max_num (int): 最大返回数量
            
        Returns:
            dict: 股票信息字典，包含code, orgId, sjstsBond, zwjc等字段
        """
        # 检查缓存
        if self.cache_manager:
            cached_data = self.cache_manager.load_top_search_cache(stock_code, max_num)
            if cached_data and len(cached_data) > 0:
                stock_info = cached_data[0]  # 取第一个匹配结果
                print(f"使用缓存获取股票信息: {stock_info.get('zwjc', '')} ({stock_info.get('code', '')})")
                return stock_info
        
        try:
            data = {
                'keyWord': stock_code,
                'maxNum': max_num
            }
            
            response = requests.post(self.search_url, data=data, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            
            # 保存到缓存
            if self.cache_manager and result:
                self.cache_manager.save_top_search_cache(stock_code, max_num, result)
            
            if result and len(result) > 0:
                stock_info = result[0]  # 取第一个匹配结果
                print(f"成功获取股票信息: {stock_info.get('zwjc', '')} ({stock_info.get('code', '')})")
                return stock_info
            else:
                print(f"未找到股票代码 {stock_code} 的信息")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求股票信息失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"解析股票信息响应失败: {e}")
            return None
        except Exception as e:
            print(f"搜索股票时发生错误: {e}")
            return None 