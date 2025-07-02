"""
配置文件 - 存储全局配置参数
"""
import json
import os

class Config:
    """全局配置类"""
    
    CACHE_DIR = "cache"
    DOWNLOADS_DIR = "downloads"
    
    def __init__(self):
        self.list_search = None
        self.stock_info = None
        self.plate = None
        self.download_base_dir = self.DOWNLOADS_DIR
        
    def load_list_search(self, file_path="list-search.json"):
        """加载list-search.json文件"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.list_search = json.load(f)
                print(f"成功加载配置文件: {file_path}")
            else:
                print(f"配置文件不存在: {file_path}")
                self.list_search = {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.list_search = {}
    
    def set_stock_info(self, stock_info):
        """设置股票信息"""
        self.stock_info = stock_info
    
    def set_plate(self, plate):
        """设置板块信息"""
        self.plate = plate
    
    def get_category_list(self):
        """获取分类列表"""
        if self.plate and self.list_search and self.plate in self.list_search:
            return self.list_search[self.plate].get('category', [])
        return [] 