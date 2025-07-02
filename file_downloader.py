"""
文件下载模块 - 使用pycurl下载PDF文件
"""
import os
import re
import time
import pycurl
from io import BytesIO

class FileDownloader:
    """文件下载类"""
    
    def __init__(self):
        self.base_url = "https://static.cninfo.com.cn/"
        self.download_delay = 1  # 下载间隔1秒
    
    def extract_date_from_url(self, adjunct_url):
        """
        从adjunctUrl中提取日期
        
        Args:
            adjunct_url (str): 文件URL路径
            
        Returns:
            str: 日期字符串 (如 '2014-04-25')
        """
        match = re.search(r'(\d{4}-\d{2}-\d{2})', adjunct_url)
        if match:
            return match.group(1)
        return ""
    
    def generate_filename(self, announcement, date_str):
        """
        生成文件名
        
        Args:
            announcement (dict): 公告信息
            date_str (str): 日期字符串
            
        Returns:
            str: 生成的文件名
        """
        sec_code = announcement.get('secCode', '')
        sec_name = announcement.get('secName', '')
        title = announcement.get('announcementTitle', '')
        
        # 构建文件名
        filename_parts = []
        
        if date_str:
            filename_parts.append(date_str)
        
        if sec_code and sec_code not in title:
            filename_parts.append(sec_code)
        
        if sec_name and sec_name not in title:
            filename_parts.append(sec_name)
        
        # 清理标题中的特殊字符
        clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        filename_parts.append(clean_title)
        
        filename = '_'.join(filename_parts) + '.pdf'
        return filename
    
    def get_file_size(self, file_path):
        """
        获取文件大小 (KB)
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            int: 文件大小 (KB)
        """
        try:
            if os.path.exists(file_path):
                return os.path.getsize(file_path) // 1024
            return 0
        except Exception:
            return 0
    
    def download_file(self, url, file_path, expected_size_kb, max_retries=3):
        """
        使用pycurl下载文件，支持重试
        
        Args:
            url (str): 下载URL
            file_path (str): 保存路径
            expected_size_kb (int): 期望文件大小 (KB)
            max_retries (int): 最大重试次数
        Returns:
            bool: 下载是否成功
        """
        attempt = 0
        while attempt < max_retries:
            if(attempt > 0):
                time.sleep(self.download_delay)
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # 使用pycurl下载
                with open(file_path, 'wb') as f:
                    curl = pycurl.Curl()
                    curl.setopt(pycurl.URL, url)
                    curl.setopt(pycurl.WRITEDATA, f)
                    curl.setopt(pycurl.FOLLOWLOCATION, True)
                    curl.setopt(pycurl.TIMEOUT, 60)
                    curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                    curl.perform()
                    http_code = curl.getinfo(pycurl.HTTP_CODE)
                    curl.close()
                
                if http_code == 200:
                    # 检查文件大小
                    actual_size = self.get_file_size(file_path)
                    if actual_size >= expected_size_kb - 10:
                        print(f"下载成功: {file_path} ({actual_size}KB)")
                        return True
                    else:
                        print(f"文件大小不匹配: 期望{expected_size_kb}KB, 实际{actual_size}KB，重试({attempt+1}/{max_retries})")
                        attempt += 1
                        continue
                else:
                    print(f"下载失败，HTTP状态码: {http_code}，重试({attempt+1}/{max_retries})")
                    attempt += 1
                    continue
                
            except Exception as e:
                print(f"下载文件时发生错误: {e}，重试({attempt+1}/{max_retries})")
                attempt += 1
                continue
        print(f"下载失败，已重试{max_retries}次: {file_path}")
        return False
    
    def download_announcement(self, announcement, save_dir, category_name):
        """
        下载单个公告文件
        
        Args:
            announcement (dict): 公告信息
            save_dir (str): 保存目录
            category_name (str): 分类名称
            
        Returns:
            bool or str: 下载是否成功，若为'skip_category'表示遇到已存在文件
        """
        adjunct_url = announcement.get('adjunctUrl', '')
        if not adjunct_url:
            print("公告没有附件URL")
            return False
        
        # 构建完整URL
        full_url = self.base_url + adjunct_url
        
        # 提取日期
        date_str = self.extract_date_from_url(adjunct_url)
        
        # 生成文件名
        filename = self.generate_filename(announcement, date_str)
        
        # 构建完整保存路径
        file_path = os.path.join(save_dir, category_name, filename)
        
        # 获取期望文件大小
        expected_size = announcement.get('adjunctSize', 0)
        
        # 检查文件是否已存在且完整
        actual_size = self.get_file_size(file_path)
        if os.path.exists(file_path):
            if actual_size >= expected_size - 10:
                print(f"文件已存在且完整，跳过下载: {file_path} ({actual_size}KB)")
                return 'skip_category'
            else:
                print(f"文件已存在但不完整，将重新下载: {file_path} (实际{actual_size}KB, 期望{expected_size}KB)")
        
        print(f"开始下载: {file_path}")
        print(f"URL: {full_url}")
        
        # 下载文件
        success = self.download_file(full_url, file_path, expected_size, max_retries=3)
        
        if success:
            # 下载成功后等待1秒
            time.sleep(self.download_delay)
        
        return success 