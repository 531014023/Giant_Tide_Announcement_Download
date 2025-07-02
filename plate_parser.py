"""
板块解析模块 - 负责获取板块信息
"""
import requests
import re
from bs4 import BeautifulSoup

class PlateParser:
    """板块解析类"""
    
    def __init__(self, cache_manager=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.cache_manager = cache_manager
    
    def get_plate(self, stock_code, org_id, sjsts_bond):
        """
        获取板块信息
        
        Args:
            stock_code (str): 股票代码
            org_id (str): 机构ID
            sjsts_bond (str): 是否可转债
            
        Returns:
            str: 板块代码 (如 'sse', 'szse', 'bj')
        """
        # 检查缓存
        if self.cache_manager:
            cached_html = self.cache_manager.load_stock_cache(stock_code, org_id, sjsts_bond)
            if cached_html:
                # 从缓存的HTML中解析板块信息
                soup = BeautifulSoup(cached_html, 'html.parser')
                plate = self._extract_plate_from_soup(soup)
                if plate:
                    print(f"使用缓存获取板块信息: {plate}")
                    return plate
        
        try:
            url = f"https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}&orgId={org_id}&sjstsBond={sjsts_bond}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            html_content = response.text
            
            # 保存到缓存
            if self.cache_manager:
                self.cache_manager.save_stock_cache(stock_code, org_id, sjsts_bond, html_content)
            
            # 解析HTML页面
            soup = BeautifulSoup(html_content, 'html.parser')
            plate = self._extract_plate_from_soup(soup)
            
            if plate:
                print(f"成功获取板块信息: {plate}")
                return plate
            else:
                print("未找到板块信息")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求板块信息失败: {e}")
            return None
        except Exception as e:
            print(f"解析板块信息时发生错误: {e}")
            return None
    
    def _extract_plate_from_soup(self, soup):
        """从BeautifulSoup对象中提取板块信息"""
        # 查找包含plate变量的script标签
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string:
                # 使用正则表达式匹配 var plate = "xxx";
                match = re.search(r'var\s+plate\s*=\s*["\']([^"\']+)["\'];', script.string)
                if match:
                    return match.group(1)
        
        return None 