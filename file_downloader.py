"""
文件下载模块 - 使用pycurl下载PDF文件
"""
import os
import re
import time
import pycurl
from io import BytesIO

# Windows 上 pycurl 默认使用 Schannel(系统证书栈)做 TLS。
# 若机器无法访问 CA 的 CRL/OCSP 服务(内网/代理/防火墙)，握手会以
# CRYPT_E_REVOCATION_OFFLINE (0x80092013) 失败，表现为 pycurl error 35。
# CURLSSLOPT_REVOKE_BEST_EFFORT = 1<<3 = 8 : 吊销服务器可达时照常校验，
#   不可达时忽略"无法完成吊销检查"这一项，安全性损失最小。
# CURLSSLOPT_NO_REVOKE        = 1<<1 = 2 : 完全关闭吊销检查(兜底)。
CURLSSLOPT_REVOKE_BEST_EFFORT = getattr(pycurl, 'SSLOPT_REVOKE_BEST_EFFORT', 8)
CURLSSLOPT_NO_REVOKE = getattr(pycurl, 'SSLOPT_NO_REVOKE', 2)


class FileDownloader:
    """文件下载类"""
    
    def __init__(self):
        self.base_url = "https://static.cninfo.com.cn/"
        self.download_delay = 1  # 下载间隔1秒
        # 当前使用的 SSL 选项，遇到吊销检查失败时会自动降级
        self.ssl_options = CURLSSLOPT_REVOKE_BEST_EFFORT
    
    @staticmethod
    def is_valid_pdf(file_path):
        """
        校验文件是否为有效 PDF(非空且以 %PDF 开头)

        Args:
            file_path (str): 文件路径

        Returns:
            bool: 是否为有效 PDF
        """
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False
            with open(file_path, 'rb') as f:
                return f.read(5) == b'%PDF-'
        except Exception:
            return False
    
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

        注意: 这里按 1000 字节 = 1KB 换算，而非 1024。
        巨潮接口返回的 adjunctSize 就是 1000 进制(实测 1,349,189 字节 -> 1349)，
        若用 1024 换算会系统性偏小约 2.4%，文件越大绝对偏差越大，
        导致大文件被误判为"大小不匹配"。

        Args:
            file_path (str): 文件路径

        Returns:
            int: 文件大小 (KB, 1000进制)
        """
        try:
            if os.path.exists(file_path):
                return os.path.getsize(file_path) // 1000
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
        # 先写入临时文件，确认完整后再改名，避免失败时留下 0 字节的假文件
        temp_path = file_path + '.part'
        while attempt < max_retries:
            if(attempt > 0):
                time.sleep(self.download_delay)
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # 使用pycurl下载
                curl = pycurl.Curl()
                try:
                    with open(temp_path, 'wb') as f:
                        curl.setopt(pycurl.URL, url)
                        curl.setopt(pycurl.WRITEDATA, f)
                        curl.setopt(pycurl.FOLLOWLOCATION, True)
                        curl.setopt(pycurl.TIMEOUT, 60)
                        curl.setopt(pycurl.CONNECTTIMEOUT, 15)
                        curl.setopt(pycurl.SSL_OPTIONS, self.ssl_options)
                        curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                        curl.perform()
                        http_code = curl.getinfo(pycurl.HTTP_CODE)
                        downloaded = int(curl.getinfo(pycurl.SIZE_DOWNLOAD))
                        content_length = int(curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
                finally:
                    curl.close()
                
                if http_code == 200:
                    actual_size = self.get_file_size(temp_path)
                    if not self.is_valid_pdf(temp_path):
                        print(f"下载内容不是有效PDF(实际{actual_size}KB)，重试({attempt+1}/{max_retries})")
                        self._cleanup(temp_path)
                        attempt += 1
                        continue

                    # 完整性判定优先级:
                    # 1) 服务器给了 Content-Length -> 以"实收字节 == 声明字节"为准(最权威，能真正识别截断)
                    # 2) 没有 Content-Length(分块传输) -> 退回用 adjunctSize 做宽松校验
                    # adjunctSize 仅作参考: 实测部分早年公告的元数据与服务器实际文件不符
                    # (如 2003 年报元数据 893KB, 服务器实际仅 674KB 且文件完好)，
                    # 因此它只用于提示，不作为失败依据。
                    if content_length > 0:
                        complete = (downloaded == content_length)
                        if not complete:
                            print(f"传输不完整: 已收{downloaded}字节/共{content_length}字节，"
                                  f"重试({attempt+1}/{max_retries})")
                    else:
                        complete = actual_size >= expected_size_kb * 0.9
                        if not complete:
                            print(f"文件大小不匹配: 期望约{expected_size_kb}KB, 实际{actual_size}KB，"
                                  f"重试({attempt+1}/{max_retries})")

                    if complete:
                        if expected_size_kb and actual_size < expected_size_kb * 0.9:
                            print(f"提示: 服务器文件({actual_size}KB)小于公告元数据标称"
                                  f"({expected_size_kb}KB)，但传输完整，按成功处理")
                        os.replace(temp_path, file_path)
                        print(f"下载成功: {file_path} ({actual_size}KB)")
                        return True
                    else:
                        self._cleanup(temp_path)
                        attempt += 1
                        continue
                else:
                    print(f"下载失败，HTTP状态码: {http_code}，重试({attempt+1}/{max_retries})")
                    self._cleanup(temp_path)
                    attempt += 1
                    continue
                
            except pycurl.error as e:
                errno = e.args[0] if e.args else 0
                msg = str(e.args[1]) if len(e.args) > 1 else str(e)
                self._cleanup(temp_path)
                # SSL 握手失败且是证书吊销检查问题时，自动降级为完全跳过吊销检查再试
                if (errno == pycurl.E_SSL_CONNECT_ERROR
                        and 'REVOCATION' in msg.upper()
                        and self.ssl_options != CURLSSLOPT_NO_REVOKE):
                    self.ssl_options = CURLSSLOPT_NO_REVOKE
                    print("检测到证书吊销检查无法完成(CRYPT_E_REVOCATION_OFFLINE)，"
                          "已切换为跳过吊销检查后重试")
                    continue  # 不消耗重试次数，立即用新策略重试
                print(f"下载文件时发生错误: [{errno}] {msg}，重试({attempt+1}/{max_retries})")
                attempt += 1
                continue
            except Exception as e:
                self._cleanup(temp_path)
                print(f"下载文件时发生错误: {e}，重试({attempt+1}/{max_retries})")
                attempt += 1
                continue
        self._cleanup(temp_path)
        print(f"下载失败，已重试{max_retries}次: {file_path}")
        return False

    def get_remote_size(self, url):
        """
        只发 HEAD 请求获取服务器上文件的真实字节数

        用于本地文件大小与公告元数据 adjunctSize 不一致时的仲裁，
        避免因元数据不准而无限重复下载同一个文件。

        Args:
            url (str): 文件URL

        Returns:
            int: 服务器文件字节数，获取失败返回 -1
        """
        curl = pycurl.Curl()
        try:
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.NOBODY, True)
            curl.setopt(pycurl.FOLLOWLOCATION, True)
            curl.setopt(pycurl.TIMEOUT, 20)
            curl.setopt(pycurl.CONNECTTIMEOUT, 10)
            curl.setopt(pycurl.SSL_OPTIONS, self.ssl_options)
            curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            curl.perform()
            if curl.getinfo(pycurl.HTTP_CODE) != 200:
                return -1
            return int(curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
        except Exception:
            return -1
        finally:
            curl.close()

    @staticmethod
    def _cleanup(path):
        """删除临时/残缺文件，避免留下 0 字节垃圾"""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    
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
            # 必须是有效PDF(非空、含%PDF头)，否则视为历史失败残留，强制重下
            if not self.is_valid_pdf(file_path):
                print(f"文件已存在但为空或非有效PDF，将重新下载: {file_path} ({actual_size}KB)")
            elif actual_size >= expected_size - 10:
                print(f"文件已存在且完整，跳过下载: {file_path} ({actual_size}KB)")
                return 'skip_category'
            else:
                # 本地比标称小，未必是没下全 —— 部分早年公告的 adjunctSize 本身就不准。
                # 向服务器确认真实大小再决定，避免每次运行都重复下载同一文件。
                remote_bytes = self.get_remote_size(full_url)
                if remote_bytes > 0 and os.path.getsize(file_path) == remote_bytes:
                    print(f"文件已存在且与服务器一致，跳过下载: {file_path} "
                          f"({actual_size}KB, 公告元数据标称{expected_size}KB 不准)")
                    return 'skip_category'
                print(f"文件已存在但不完整，将重新下载: {file_path} (实际{actual_size}KB, 期望{expected_size}KB)")
        
        print(f"开始下载: {file_path}")
        print(f"URL: {full_url}")
        
        # 下载文件
        success = self.download_file(full_url, file_path, expected_size, max_retries=3)
        
        if success:
            # 下载成功后等待1秒
            time.sleep(self.download_delay)
        
        return success 