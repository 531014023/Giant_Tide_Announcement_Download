"""港股(HKEXnews)公告抓取器。

输出与 A股 announcement_fetcher 同构的归一化公告字典，
直接喂给 FileDownloader（下载器是源无关的，只看 adjunctUrl/adjunctSize/
announcementTitle/secCode/secName 这几个字段）。

取数流程（已实测确认可行）：
  1. 解析股票代码 -> 港交所内部 stockId
     港交所的股票选择是 JS 自动完成组件，提交的是"内部序列号"而非展示代码。
     展示代码 00700 对应的内部 stockId 是 7609；直接把 00700 当 stockId 传，
     服务端会按"序列号"解读从而返回错误的股票。
     解析接口：GET /search/partial.do?lang=ZH&type=A&name=<代码>&market=SEHK
       -> {"stockInfo":[{"stockId":7609,"code":"00700","name":"騰訊控股"}, ...]}
  2. GET /search/titleSearchServlet.do 拿 JSON
     参数 stockId=内部id、fromDate/toDate 为全历史、t1code=-2(全部分类)、lang=ZH(中文_pdf)
     带上正确的内部 stockId 后，服务端按股票过滤，且支持宽日期范围（无需按月分块）。

说明：
  - 用 requests（与 A股列表抓取同一套 TLS 栈）
  - 用正则解析，不引入 bs4 等新依赖
  - 查全部分类(t1code=-2)再按标题关键词过滤，确保年报/中报/季报/業績公告都覆盖
    （業績公告属"公告及通告"类，不在 Reports 类下，故不能只查 t1code=40000）
"""
import re
import json
from datetime import datetime

import requests
from opencc import OpenCC

# 繁→简转换器：输出(目录名/文件名/关键词过滤)统一用简体。
# 注意：标题分类仍在港交所繁体原文上做（关键词繁简混合，原文匹配最稳），
#       转简只发生在产出 announcementTitle/secName 时。
_CC = OpenCC("t2s")

BASE = "https://www1.hkexnews.hk"
SEARCH_PAGE = f"{BASE}/search/titlesearch.xhtml"
API_ENDPOINT = f"{BASE}/search/titleSearchServlet.do"
STOCK_RESOLVE = f"{BASE}/search/partial.do"

# 分类规则：按顺序匹配标题，命中即归入对应类别（用作下载子目录）。
# 分类名直接采用 A股使用习惯：年报 / 半年报 / 一季报 / 三季报 / 業績公告。
#
# 顺序至关重要（从最明确的期间锚点往前排）：
#   年报 > 半年报 > 三季报 > 一季报 > 業績公告
# 为什么这个顺序？
#   - 港股季报标题形如"截至X月X日止三個月業績公佈"，中报标题是
#     "截至六月三十日止三個月及六個月業績公佈"——两者都含"三個月"，
#     必须让带"六個月/六月三十日"的半年报规则先于"三個月"命中，否则中报会被误判成一季报。
#   - 因此用"财报截止月份"作为锚点：三月三十一日=一季报、六月三十日=半年报、
#     九月三十日=三季报、十二月三十一日=年报；季度词(第一季/第三季)作补充。
#   - 全年業績/年度業績归年报，中期業績归半年报（避免落入業績公告桶）。
CATEGORY_RULES = [
    # 年报（年度）：含 年報 / 十二月三十一日 / 全年業績 / 年度業績
    ("年报", ["年報", "年度報告", "annual report", "十二月三十一日",
              "全年業績", "年度業績", "全年业绩", "年度业绩"]),
    # 半年报（中报）：含 中期報告/中期業績 / 六月三十日 / 六個月 / 半年
    ("半年报", ["中期報告", "中期报告", "中期業績", "中期业绩", "中期公佈", "中期公布",
                "interim report", "六月三十日", "及六個月", "止六個月", "及六个月", "止六个月",
                "半年", "半年度"]),
    # 三季报：只认"定期报告"精确写法（截止月份锚点 + 季度報告）。
    # 刻意不用裸词"第三季/第三季度"——港股大量"第三季度最新業務狀況"是
    # 自愿性业务更新公告(非定期报告)，会被误判成季报。
    ("三季报", ["九月三十日", "及九個月", "止九個月", "及九个月", "止九个月",
                "第三季度報告", "第三季度报告"]),
    # 一季报：同理，只认定期报告精确写法，避开"第一季度最新業務狀況"类业务更新。
    ("一季报", ["三月三十一日", "第一季度報告", "第一季度报告",
                "及三個月", "止三個月", "及三个月", "止三个月"]),
    # 业务更新：自愿性经营数据披露（非定期报告），形如"X季度最新業務狀況"/
    # "自願公告 業務資料更新"。含季度经营数据，对跟踪有价值，但必须单列，
    # 不能与正式一季报/三季报混淆（故上文季报规则刻意不用裸"第一季/第三季"）。
    ("业务更新", ["最新業務狀況", "最新业务状况", "業務狀況", "业务状况",
                "業務資料更新", "業務資料", "業務更新", "业务更新"]),
    # 业绩公告（兜底）：其他无法归入上述定期报告期间的業績类公告
    ("业绩公告", ["業績", "业绩", "results", "preliminary results"]),
]

# 排除词：即便命中上面类别也不下载（不属于"定期报告/业绩公告"）
#  - ESG 报告
#  - 证券变动月报（港交所强制的月度例行披露，标题含"月報表"，会撞月份锚点被误判为一/三季报）
#  - 股息公告（末期股息/中期股息等分红公告，不是报告本身）
EXCLUDE_TITLES = ["環境、社會及管治", "環境社會及管治", "esg報告", "esg report",
                  "月報表", "股息"]


class HKAnnouncementFetcher:
    """港股公告抓取器（归一化输出）"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    # ------------------------------------------------------------------ #
    # 步骤 1：展示代码 -> 港交所内部 stockId
    # ------------------------------------------------------------------ #
    def _resolve_stock_id(self, code):
        """把 5 位展示代码解析为港交所内部 stockId（整数）。

        优先查主板(type=A)；若未命中（如 GEM 等）再查 type=I。
        返回 None 表示无法解析（代码不存在或网络异常）。
        """
        for stock_type in ("A", "I"):
            try:
                resp = self.session.get(
                    STOCK_RESOLVE,
                    params={
                        "lang": "ZH",
                        "type": stock_type,
                        "name": code,
                        "market": "SEHK",
                        "callback": "cb",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
            except requests.RequestException:
                continue
            m = re.search(r"callback\((.*)\)", resp.text, re.S)
            if not m:
                continue
            try:
                data = json.loads(m.group(1))
            except (ValueError, json.JSONDecodeError):
                continue
            for it in data.get("stockInfo", []):
                if str(it.get("code", "")).zfill(5) == code:
                    return int(it["stockId"])
        return None

    # ------------------------------------------------------------------ #
    # 步骤 2：GET JSON API（分页 rowRange + hasNextRow）
    # ------------------------------------------------------------------ #
    def _fetch_json(self, stock_id, from_date, to_date):
        records = []
        fetched = 0
        while True:
            row_range = fetched + 5000
            resp = self.session.get(
                API_ENDPOINT,
                params={
                    "sortDir": "0",
                    "sortByOptions": "DateTime",
                    "category": "0",
                    "market": "SEHK",
                    "stockId": str(stock_id),
                    "documentType": "-1",
                    "fromDate": from_date,
                    "toDate": to_date,
                    "title": "",
                    "searchType": "0",
                    "t1code": "-2",       # 全部分类（业绩公告不在 Reports 类下）
                    "t2Gcode": "-2",
                    "t2code": "-2",
                    "rowRange": str(row_range),
                    "lang": "ZH",          # 中文 → 链接带 _c.pdf
                },
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Referer": SEARCH_PAGE,
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result")
            if not result or result == "null":
                break
            chunk = json.loads(result)
            records.extend(chunk[fetched:])
            fetched = len(chunk)
            if not data.get("hasNextRow"):
                break
            if chunk and fetched >= int(chunk[0].get("TOTAL_COUNT", "0")):
                break
        return records

    # ------------------------------------------------------------------ #
    # 标题分类 / 字段解析
    # ------------------------------------------------------------------ #
    @staticmethod
    def _classify(title):
        t = title.lower()
        for cat, kws in CATEGORY_RULES:
            for kw in kws:
                if kw.lower() in t:
                    return cat
        return None

    @staticmethod
    def _is_excluded(title):
        t = title.lower()
        return any(ex.lower() in t for ex in EXCLUDE_TITLES)

    @staticmethod
    def _parse_size(file_info):
        """'152KB' / '1.3MB' -> KB(int)；解析失败返回 0（下载器以 Content-Length 为准）"""
        m = re.match(r"([\d.]+)\s*(KB|MB)", (file_info or "").strip(), re.I)
        if not m:
            return 0
        val = float(m.group(1))
        return int(val * 1024 if m.group(2).upper() == "MB" else val)

    @staticmethod
    def _parse_date(date_time):
        """'19/03/2026 16:30' (DD/MM/YYYY) -> '2026-03-19'"""
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", date_time or "")
        if not m:
            return ""
        dd, mm, yyyy = m.groups()
        return f"{yyyy}-{mm}-{dd}"

    @staticmethod
    def _clean(field):
        return (field or "").split("<br/>")[0].strip()

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #
    def fetch(self, stock_code, from_date="20000101", to_date=None, sec_name_hint=None):
        """
        抓取某港股代码的定期报告 + 业绩公告（中文），返回归一化公告列表。

        Args:
            stock_code (str): 港股代码，支持 '700' / '00700' / '00700.HK' 等写法
            from_date (str): 起始日期 YYYYMMDD，默认 20000101（全历史）
            to_date (str): 结束日期 YYYYMMDD，默认今天
            sec_name_hint (str): 公司简体简称（A股搜索接口返回的 zwjc），
                优先用作目录名/文件名；未提供时用港交所繁体 STOCK_NAME 转简。

        Returns:
            list[dict]: 每个元素字段与 A股公告同构
        """
        # 规范化代码为 5 位
        code = re.sub(r"[^0-9]", "", str(stock_code)).zfill(5)
        if not to_date:
            to_date = datetime.now().strftime("%Y%m%d")

        # 1) 解析内部 stockId（核心修复：不能把展示代码当 stockId 传）
        stock_id = self._resolve_stock_id(code)
        if stock_id is None:
            return []

        # 2) 拉 JSON（带上正确的内部 stockId，服务端按股票过滤）
        raw = self._fetch_json(stock_id, from_date, to_date)

        out = []
        seen = set()
        for rec in raw:
            title = (rec.get("TITLE", "")
                     .replace("&#x3b;", ";").replace("&amp;", "&").strip())
            # 去控制字符(港股 TITLE 可能含字面 \r\n，会导致文件名非法)
            title = re.sub(r"[\x00-\x1f]", "", title).strip()
            cat = self._classify(title)
            if not cat or self._is_excluded(title):
                continue
            link = rec.get("FILE_LINK", "")
            if not link:
                continue
            if not link.lower().endswith(".pdf"):
                continue  # 只下 PDF（报告/业绩公告均为 PDF）
            if link.startswith("/"):
                link = BASE + link
            date_str = self._parse_date(rec.get("DATE_TIME", ""))
            size = self._parse_size(rec.get("FILE_INFO", ""))
            sec = self._clean(rec.get("STOCK_CODE", ""))
            # 公司名：优先 A股搜索返回的简体简称(sec_name_hint)，否则港交所繁体转简
            if sec_name_hint:
                name = sec_name_hint
            else:
                name = _CC.convert(self._clean(rec.get("STOCK_NAME", "")))
            key = (link, title)  # 去重（中文/英文版不会同时出现，因 lang=ZH）
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "adjunctUrl": link,
                "adjunctSize": size,
                # 标题转简体（文件名/关键词过滤用简体；分类已用繁体原文判定）
                "announcementTitle": _CC.convert(title),
                "secCode": code,
                "secName": name or f"HK{code}",
                "announcementDate": date_str,
                "category": cat,
            })
        return out
