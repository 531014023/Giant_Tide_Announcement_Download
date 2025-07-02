# 巨潮资讯网公告下载器

这是一个用于从巨潮资讯网下载指定公司公告的Python工具，使用模块化设计，支持批量下载PDF格式的公告文件。默认下载全部公告。

## 功能特点

- 模块化设计，每个模块负责单一职责
- 支持自动获取股票基本信息和板块信息
- 支持分页获取公告列表，使用生成器模式边获取边下载
- 使用pycurl进行高效的文件下载
- 自动验证文件完整性
- 智能文件命名和目录组织
- 下载间隔控制，避免被封IP
- 内存优化，避免大量公告数据占用内存
- 完整的缓存系统，支持断点续传，减少重复请求

## 项目结构

```
Giant_Tide_Announcement_Download/
├── config.py              # 配置管理模块
├── cache_manager.py       # 缓存管理模块
├── stock_searcher.py      # 股票搜索模块
├── plate_parser.py        # 板块解析模块
├── announcement_fetcher.py # 公告获取模块
├── file_downloader.py     # 文件下载模块
├── main.py               # 主程序
├── cache_tools.py        # 缓存管理工具
├── requirements.txt      # 依赖包列表
├── README.md            # 项目说明
├── list-search.json     # 配置文件（需要用户提供）
└── cache/               # 缓存目录
    ├── 601225_陕西煤业/                # 每只股票独立缓存目录
    │   ├── topSearchquery/             # 股票搜索缓存
    │   │   ├── 601225_10_topSearchquery.json
    │   │   └── ...
    │   │
    │   ├── stock/                      # 股票页面缓存
    │   │   ├── 601225_9900023204_false_disclosurestock.html
    │   │   └── ...
    │   │
    │   └── hisAnnouncementquery/       # 公告查询缓存
    │       ├── 年度报告/                # 分类中文名目录
    │       │   ├── 601225_category_ndbg_szsh_1_sse_sse_empty_empty_hisAnnouncementquery.json
    │       │   └── ...
    │       └── ...
    └── ...
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 准备配置文件 `list-search.json`，包含分类信息
2. 运行程序：

```bash
python main.py <股票代码>/<股票名称>
```

示例：
```bash
python main.py 601225
python main.py 陕西煤业
```

### 启动时指定分类下载

你可以通过命令行参数指定只下载某个分类的公告，支持分类中文名（模糊匹配）或分类key（精确匹配）。分类在list-search.json中查找。

示例：

只下载"年报"分类（支持模糊）：
```bash
python main.py 601225 年报
```

只下载key为"category_ndbg_szsh"的分类：
```bash
python main.py 601225 category_ndbg_szsh
```

如果不指定分类参数，则默认下载全部分类。 

### 缓存管理

查看缓存信息：
```bash
python cache_tools.py info
```

清理所有缓存：
```bash
python cache_tools.py clear
```

清理特定类型缓存：
```bash
python cache_tools.py clear top_search    # 清理股票搜索缓存
python cache_tools.py clear stock         # 清理股票页面缓存
python cache_tools.py clear announcement  # 清理公告查询缓存
```

## 配置文件格式

`list-search.json` 文件默认不能动，这是从巨潮下载下来的。

## 下载目录结构

程序会在 `downloads` 目录下创建如下结构：

```
downloads/
└── 陕西煤业/
    ├── 年度报告/
    │   ├── 2014-04-25_601225_陕西煤业_关于公司非经营性资金占用及其他关联资金往来的专项说明.pdf
    │   └── ...
    └── 半年度报告/
        └── ...
```

## 模块说明

### config.py
- 负责加载和管理全局配置
- 处理 `list-search.json` 配置文件
- 管理股票信息和板块信息

### cache_manager.py
- 负责缓存文件的保存、读取和检查
- 支持三种类型的缓存：股票搜索、股票页面、公告查询
- 提供缓存清理和信息查看功能

### stock_searcher.py
- 负责查询股票基本信息
- 通过POST请求获取股票代码、机构ID等信息

### plate_parser.py
- 负责解析板块信息
- 从HTML页面中提取板块代码

### announcement_fetcher.py
- 负责获取公告列表
- 支持分页获取，自动处理翻页逻辑
- 使用生成器模式，边获取边下载，避免内存占用过大

### file_downloader.py
- 负责下载PDF文件
- 使用pycurl进行高效下载
- 验证文件完整性
- 智能文件命名

### main.py
- 主程序入口
- 协调各个模块完成完整的下载流程

### cache_tools.py
- 缓存管理工具
- 提供缓存信息查看和清理功能

## 注意事项

1. 确保网络连接正常
2. 下载间隔设置为1秒，避免被服务器限制
3. 文件大小验证允许10KB的误差
4. 程序会自动创建必要的目录结构
5. 文件名中的特殊字符会被替换为下划线
6. 使用生成器模式处理公告列表，避免大量数据占用内存
7. 缓存文件会保存在cache目录下，支持断点续传
8. 如需强制刷新数据，可以使用缓存清理工具

## 错误处理

程序包含完善的错误处理机制：
- 网络请求异常处理
- 文件下载失败重试
- 配置文件加载异常处理
- 文件大小验证失败处理
- 缓存文件损坏自动重新请求

## 依赖包

- requests: HTTP请求库
- pycurl: 高效的文件下载库
- beautifulsoup4: HTML解析库
- lxml: XML/HTML解析器 

## 缓存目录结构

```
cache/
└── 601225_陕西煤业/                # 每只股票独立缓存目录
    ├── topSearchquery/             # 股票搜索缓存
    │   ├── 601225_10_topSearchquery.json
    │   └── ...
    ├── stock/                      # 股票页面缓存
    │   ├── 601225_9900023204_false_disclosurestock.html
    │   └── ...
    └── hisAnnouncementquery/       # 公告查询缓存
        ├── 年度报告/                # 分类中文名目录
        │   ├── 601225_category_ndbg_szsh_1_sse_sse_empty_empty_hisAnnouncementquery.json
        │   └── ...
        └── ...
```

- 所有缓存（topSearchquery、stock、hisAnnouncementquery）都自动存储在 `cache/{股票代码}_{股票名称}/` 目录下，互不干扰，便于管理和分析。
- 公告缓存路径为：`cache/{股票代码}_{股票名称}/hisAnnouncementquery/{分类中文名}/{股票信息}_{分类key}_{页码}_{column}_{plate}_{searchkey}_{seDate}_hisAnnouncementquery.json`
- 其中`分类中文名`为category.value（如"年度报告"），文件名顺序与代码一致。 

## 缓存目录和下载目录配置

**现在支持通过 `.env` 文件自定义缓存和下载目录。**

1. 在项目根目录新建 `.env` 文件，内容示例：
   ```
   CACHE_DIR=D:/your/path/cache
   DOWNLOADS_DIR=D:/your/path/downloads
   ```
   路径可根据需要自行修改。

2. 程序会自动读取 `.env` 文件中的配置。如果没有设置，将使用默认的 `cache/` 和 `downloads/` 目录。

3. `.env` 文件已加入 `.gitignore`，不会被提交到 git 仓库。

4. 你也可以直接在 `config.py` 里修改默认值。

如需自定义目录，请确保对应目录有写入权限。 