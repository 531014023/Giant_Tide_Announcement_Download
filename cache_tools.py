"""
缓存管理工具 - 提供缓存清理和查看功能
"""
import sys
from cache_manager import CacheManager

def show_cache_info():
    """显示缓存信息"""
    cache_manager = CacheManager()
    info = cache_manager.get_cache_info()
    
    print("=" * 50)
    print("缓存信息")
    print("=" * 50)
    print(f"股票搜索缓存: {info['top_search_count']} 个文件")
    print(f"股票页面缓存: {info['stock_count']} 个文件")
    print(f"公告查询缓存: {info['announcement_count']} 个文件")
    print("=" * 50)

def clear_cache(cache_type=None):
    """清理缓存"""
    cache_manager = CacheManager()
    
    if cache_type is None:
        print("清理所有缓存...")
        cache_manager.clear_cache()
    else:
        print(f"清理 {cache_type} 缓存...")
        cache_manager.clear_cache(cache_type)
    
    print("缓存清理完成")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python cache_tools.py info                    # 查看缓存信息")
        print("  python cache_tools.py clear                   # 清理所有缓存")
        print("  python cache_tools.py clear top_search        # 清理股票搜索缓存")
        print("  python cache_tools.py clear stock             # 清理股票页面缓存")
        print("  python cache_tools.py clear announcement      # 清理公告查询缓存")
        return
    
    command = sys.argv[1]
    
    if command == "info":
        show_cache_info()
    elif command == "clear":
        cache_type = sys.argv[2] if len(sys.argv) > 2 else None
        clear_cache(cache_type)
    else:
        print(f"未知命令: {command}")
        print("可用命令: info, clear")

if __name__ == "__main__":
    main() 