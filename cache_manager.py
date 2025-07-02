"""
缓存管理模块 - 负责缓存文件的保存、读取和检查
"""
import os
import json
import hashlib
from pathlib import Path

class CacheManager:
    """缓存管理类"""
    
    def __init__(self, cache_dir="cache", stock_code=None, stock_name=None):
        self.base_dir = cache_dir
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.cache_dir = self.base_dir
        if stock_code and stock_name:
            self.cache_dir = os.path.join(self.base_dir, f"{stock_code}_{stock_name}")
        self.top_search_dir = os.path.join(self.cache_dir, "topSearchquery")
        self.stock_dir = os.path.join(self.cache_dir, "stock")
        self.announcement_dir = os.path.join(self.cache_dir, "hisAnnouncementquery")
        
        # 创建缓存目录
        self._create_cache_dirs()
    
    def _create_cache_dirs(self):
        """创建缓存目录结构"""
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.top_search_dir, exist_ok=True)
        os.makedirs(self.stock_dir, exist_ok=True)
        os.makedirs(self.announcement_dir, exist_ok=True)
    
    def _get_cache_path(self, directory, filename):
        """获取缓存文件路径"""
        return os.path.join(directory, filename)
    
    def save_top_search_cache(self, key_word, max_num, data):
        """
        保存股票搜索缓存
        
        Args:
            key_word (str): 股票代码
            max_num (int): 最大返回数量
            data (dict): 响应数据
        """
        filename = f"{key_word}_{max_num}_topSearchquery.json"
        cache_path = self._get_cache_path(self.top_search_dir, filename)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"股票搜索缓存已保存: {filename}")
        except Exception as e:
            print(f"保存股票搜索缓存失败: {e}")
    
    def load_top_search_cache(self, key_word, max_num):
        """
        加载股票搜索缓存
        
        Args:
            key_word (str): 股票代码
            max_num (int): 最大返回数量
            
        Returns:
            dict: 缓存数据，如果不存在返回None
        """
        filename = f"{key_word}_{max_num}_topSearchquery.json"
        cache_path = self._get_cache_path(self.top_search_dir, filename)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"使用股票搜索缓存: {filename}")
                return data
            except Exception as e:
                print(f"加载股票搜索缓存失败: {e}")
        
        return None
    
    def save_stock_cache(self, stock_code, org_id, sjsts_bond, html_content):
        """
        保存股票页面缓存
        
        Args:
            stock_code (str): 股票代码
            org_id (str): 机构ID
            sjsts_bond (str): 是否可转债
            html_content (str): HTML内容
        """
        filename = f"{stock_code}_{org_id}_{sjsts_bond}_disclosurestock.html"
        cache_path = self._get_cache_path(self.stock_dir, filename)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"股票页面缓存已保存: {filename}")
        except Exception as e:
            print(f"保存股票页面缓存失败: {e}")
    
    def load_stock_cache(self, stock_code, org_id, sjsts_bond):
        """
        加载股票页面缓存
        
        Args:
            stock_code (str): 股票代码
            org_id (str): 机构ID
            sjsts_bond (str): 是否可转债
            
        Returns:
            str: HTML内容，如果不存在返回None
        """
        filename = f"{stock_code}_{org_id}_{sjsts_bond}_disclosurestock.html"
        cache_path = self._get_cache_path(self.stock_dir, filename)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"使用股票页面缓存: {filename}")
                return content
            except Exception as e:
                print(f"加载股票页面缓存失败: {e}")
        
        return None
    
    def save_announcement_cache(self, stock, page_num, category, column, plate, searchkey, se_date, data, category_value=None):
        """
        保存公告查询缓存
        
        Args:
            stock (str): 股票信息
            page_num (int): 页码
            category (str): 分类
            column (str): 列
            plate (str): 板块
            searchkey (str): 搜索关键词
            se_date (str): 日期
            data (dict): 响应数据
            category_value (str): 分类中文名
        """
        # 清理参数中的特殊字符
        safe_stock = stock.replace(',', '_')
        safe_category = category.replace(';', '_')
        safe_plate = plate.replace(';', '_')
        safe_searchkey = searchkey.replace(' ', '_') if searchkey else 'empty'
        safe_se_date = se_date.replace('-', '') if se_date else 'empty'
        safe_category_value = category_value or 'unknown'
        safe_category_value = safe_category_value.replace('/', '_').replace('\\', '_')
        
        dir_path = os.path.join(self.announcement_dir, safe_category_value)
        os.makedirs(dir_path, exist_ok=True)
        filename = f"{safe_stock}_{page_num}_{safe_category}_{column}_{safe_plate}_{safe_searchkey}_{safe_se_date}_hisAnnouncementquery.json"
        cache_path = self._get_cache_path(dir_path, filename)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"公告查询缓存已保存: {os.path.join(safe_category_value, filename)}")
        except Exception as e:
            print(f"保存公告查询缓存失败: {e}")
    
    def load_announcement_cache(self, stock, page_num, category, column, plate, searchkey, se_date, category_value=None):
        """
        加载公告查询缓存
        
        Args:
            stock (str): 股票信息
            page_num (int): 页码
            category (str): 分类
            column (str): 列
            plate (str): 板块
            searchkey (str): 搜索关键词
            se_date (str): 日期
            category_value (str): 分类中文名
        Returns:
            dict: 缓存数据，如果不存在返回None
        """
        # 清理参数中的特殊字符
        safe_stock = stock.replace(',', '_')
        safe_category = category.replace(';', '_')
        safe_plate = plate.replace(';', '_')
        safe_searchkey = searchkey.replace(' ', '_') if searchkey else 'empty'
        safe_se_date = se_date.replace('-', '') if se_date else 'empty'
        safe_category_value = category_value or 'unknown'
        safe_category_value = safe_category_value.replace('/', '_').replace('\\', '_')
        
        dir_path = os.path.join(self.announcement_dir, safe_category_value)
        filename = f"{safe_stock}_{safe_category}_{page_num}_{column}_{safe_plate}_{safe_searchkey}_{safe_se_date}_hisAnnouncementquery.json"
        cache_path = self._get_cache_path(dir_path, filename)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"使用公告查询缓存: {os.path.join(safe_category_value, filename)}")
                return data
            except Exception as e:
                print(f"加载公告查询缓存失败: {e}")
        
        return None
    
    def clear_cache(self, cache_type=None):
        """
        清理缓存
        
        Args:
            cache_type (str): 缓存类型 ('top_search', 'stock', 'announcement', None表示清理所有)
        """
        if cache_type is None or cache_type == 'top_search':
            self._clear_directory(self.top_search_dir)
        if cache_type is None or cache_type == 'stock':
            self._clear_directory(self.stock_dir)
        if cache_type is None or cache_type == 'announcement':
            self._clear_directory(self.announcement_dir)
        
        print("缓存清理完成")
    
    def _clear_directory(self, directory):
        """清理指定目录下的所有文件"""
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
    
    def get_cache_info(self):
        """获取缓存信息"""
        info = {
            'top_search_count': len(os.listdir(self.top_search_dir)) if os.path.exists(self.top_search_dir) else 0,
            'stock_count': len(os.listdir(self.stock_dir)) if os.path.exists(self.stock_dir) else 0,
            'announcement_count': len(os.listdir(self.announcement_dir)) if os.path.exists(self.announcement_dir) else 0
        }
        return info

    def set_stock(self, stock_code, stock_name):
        """设置股票代码和名称，重置缓存目录"""
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.cache_dir = os.path.join(self.base_dir, f"{stock_code}_{stock_name}")
        self.top_search_dir = os.path.join(self.cache_dir, "topSearchquery")
        self.stock_dir = os.path.join(self.cache_dir, "stock")
        self.announcement_dir = os.path.join(self.cache_dir, "hisAnnouncementquery")
        self._create_cache_dirs() 