"""把简报 JSON 和行情 JSON 嵌入固定模板，生成独立的 HTML 页面。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "template.html"
DATA_PLACEHOLDER = "__REPORT_DATA__"

TENDENCIES = {"偏多", "偏空", "无倾向"}
CREDIBILITIES = {"官方确认", "媒体报道", "传闻"}
PRICED_IN = {"已计价", "部分", "未计价"}
GRADES = {"高", "中", "低"}
LEVELS = {"公司", "板块", "宏观"}
DIRECTIONS = {"利多", "利空"}
MARKET_DIRECTIONS = {*DIRECTIONS, "中性"}
PATTERN_STATUSES = {"明确", "疑似"}
LEANS = {"偏多", "偏空", "中性"}
REPORT_TIMINGS = {"盘前", "盘后"}
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
NEWS_CATEGORIES = {
    "运营事件与日程",
    "合同与合作",
    "官方披露",
    "管理层言论",
    "分析师动作",
    "资金面",
    "监管与法律",
    "竞争对手与上下游",
}
MAX_TOP_ITEMS = 3
MAX_INDUSTRIES = 5

SECTOR_ITEMS = (
    "板块走势",
    "同业财报",
    "行业事件",
    "行业周期位置",
    "个股相对板块",
    "利率敏感度",
)
POST_EARNINGS_ITEMS = (
    "预期差",
    "指引",
    "盈利质量",
    "关键指标",
    "电话会",
    "已计价程度",
    "仓位与情绪",
    "实际股价反应",
)
FOLLOW_UP_ITEM = "财报后至今"
PRE_EARNINGS_ITEMS = (
    "预期有多高",
    "财报前涨幅与估值",
    "历史财报日规律",
    "这次要过的坎",
)
EARNINGS_ITEMS_BY_MODE = {
    "财报刚出": POST_EARNINGS_ITEMS,
    "财报已过": (*POST_EARNINGS_ITEMS, FOLLOW_UP_ITEM),
    "财报前": PRE_EARNINGS_ITEMS,
}

Item = dict[str, Any]


def find_missing_items(
    section: str, items: list[Item], required: tuple[str, ...]
) -> list[str]:
    present = {item.get("item") for item in items}
    return [f"{section}: 缺少「{name}」" for name in required if name not in present]


def find_invalid_values(
    section: str, items: list[Item], key: str, allowed: set[str]
) -> list[str]:
    return [
        f"{section} 第 {index} 条: {key} 必须是 {sorted(allowed)} 之一，现在是 {item.get(key)!r}"
        for index, item in enumerate(items, start=1)
        if item.get(key) not in allowed
    ]


def find_macro_problems(macro: dict[str, Any]) -> list[str]:
    news = macro.get("news") or []
    problems = find_invalid_values("macro.news", news, "market_impact", MARKET_DIRECTIONS)
    for index, item in enumerate(news, start=1):
        industries = item.get("industries") or []
        section = f"macro.news 第 {index} 条的 industries"
        if len(industries) > MAX_INDUSTRIES:
            problems.append(f"{section} 最多 {MAX_INDUSTRIES} 个")
        problems += find_invalid_values(section, industries, "impact", DIRECTIONS)

    calendar = macro.get("calendar") or []
    problems += find_invalid_values("macro.calendar", calendar, "importance", GRADES)
    problems += find_invalid_values(
        "macro.calendar", calendar, "market_impact", MARKET_DIRECTIONS
    )
    for index, event in enumerate(calendar, start=1):
        industries = event.get("industries") or []
        section = f"macro.calendar 第 {index} 条的 industries"
        if len(industries) > MAX_INDUSTRIES:
            problems.append(f"{section} 最多 {MAX_INDUSTRIES} 个")
        problems += find_invalid_values(section, industries, "impact", MARKET_DIRECTIONS)
    return problems


def find_case_problems(ticker: str, side: str, case: dict[str, Any]) -> list[str]:
    prefix = f"{ticker}.{side}"
    top = case.get("top") or []
    problems: list[str] = []
    if len(top) > MAX_TOP_ITEMS:
        problems.append(f"{prefix}.top 最多 {MAX_TOP_ITEMS} 条")
    problems += find_invalid_values(f"{prefix}.top", top, "level", LEVELS)

    points = case.get("points") or []
    problems += find_invalid_values(f"{prefix}.points", points, "level", LEVELS)
    problems += find_invalid_values(f"{prefix}.points", points, "impact", GRADES)
    problems += find_invalid_values(f"{prefix}.points", points, "priced_in", PRICED_IN)
    return problems


def find_earnings_problems(ticker: str, earnings: dict[str, Any]) -> list[str]:
    prefix = f"{ticker}.earnings"
    problems: list[str] = []
    if not DATE_PATTERN.fullmatch(str(earnings.get("report_date", ""))):
        problems.append(f"{prefix}.report_date 必须是 YYYY-MM-DD")
    if earnings.get("report_timing") not in REPORT_TIMINGS:
        problems.append(f"{prefix}.report_timing 必须是 {sorted(REPORT_TIMINGS)} 之一")
    if not earnings.get("scorecard"):
        problems.append(f"{prefix}.scorecard 为空；至少要有营收和 EPS")

    items = earnings.get("items") or []
    problems += find_invalid_values(f"{prefix}.items", items, "lean", LEANS)
    for index, item in enumerate(items, start=1):
        for side in ("bull", "bear"):
            if not item.get(side):
                problems.append(f"{prefix}.items 第 {index} 条: 缺少 {side}；查不到就写「未找到」")
    return problems


def find_stock_problems(stock: dict[str, Any], market_symbols: dict[str, Any]) -> list[str]:
    ticker = stock.get("ticker", "?")
    problems: list[str] = []
    if ticker not in market_symbols:
        problems.append(f"{ticker}: 行情文件里没有这只股票")
    if stock.get("tendency") not in TENDENCIES:
        problems.append(f"{ticker}: tendency 必须是 {sorted(TENDENCIES)} 之一")

    problems += find_invalid_values(
        f"{ticker}.price_action", stock.get("price_action") or [], "driver", LEVELS
    )
    problems += find_invalid_values(
        f"{ticker}.technical.patterns",
        (stock.get("technical") or {}).get("patterns") or [],
        "status",
        PATTERN_STATUSES,
    )

    for side in ("bull", "bear"):
        problems += find_case_problems(ticker, side, stock.get(side) or {})

    earnings = stock.get("earnings")
    if isinstance(earnings, dict):
        problems += find_earnings_problems(ticker, earnings)
    else:
        problems.append(f"{ticker}.earnings 必须是对象，结构见 SKILL.md 第 4 步")
        earnings = {}
    mode = stock.get("earnings_mode")
    if mode in EARNINGS_ITEMS_BY_MODE:
        problems += find_missing_items(
            f"{ticker}.earnings.items", earnings.get("items") or [], EARNINGS_ITEMS_BY_MODE[mode]
        )
    else:
        problems.append(
            f"{ticker}: earnings_mode 必须是 {sorted(EARNINGS_ITEMS_BY_MODE)} 之一，现在是 {mode!r}"
        )
    problems += find_missing_items(
        f"{ticker}.sector.items",
        (stock.get("sector") or {}).get("items") or [],
        SECTOR_ITEMS,
    )

    news = stock.get("news") or []
    overnight = (stock.get("overnight") or {}).get("items") or []
    problems += find_invalid_values(f"{ticker}.news", news, "category", NEWS_CATEGORIES)
    for section, items in ((f"{ticker}.news", news), (f"{ticker}.overnight.items", overnight)):
        problems += find_invalid_values(section, items, "credibility", CREDIBILITIES)
        problems += find_invalid_values(section, items, "priced_in", PRICED_IN)
    problems += find_invalid_values(
        f"{ticker}.calendar", stock.get("calendar") or [], "credibility", CREDIBILITIES
    )
    return problems


def find_report_problems(report: dict[str, Any], market: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not report.get("date"):
        problems.append("缺少 date")
    problems += find_macro_problems(report.get("macro") or {})

    stocks = report.get("stocks") or []
    if not stocks:
        problems.append("stocks 为空")
    tickers = [stock.get("ticker") for stock in stocks]
    duplicates = sorted({ticker for ticker in tickers if tickers.count(ticker) > 1})
    if duplicates:
        problems.append(f"stocks 里有重复的 ticker：{duplicates}")

    market_symbols = market.get("symbols", {})
    for stock in stocks:
        problems += find_stock_problems(stock, market_symbols)
    return problems


def sort_by_canonical_order(items: list[Item], canonical: tuple[str, ...]) -> list[Item]:
    rank = {name: index for index, name in enumerate(canonical)}
    return sorted(items, key=lambda item: rank.get(item.get("item"), len(rank)))


def sort_fixed_items(report: dict[str, Any]) -> None:
    for stock in report["stocks"]:
        sector = stock.setdefault("sector", {})
        sector["items"] = sort_by_canonical_order(sector.get("items") or [], SECTOR_ITEMS)
        earnings = stock["earnings"]
        earnings["items"] = sort_by_canonical_order(
            earnings.get("items") or [], EARNINGS_ITEMS_BY_MODE[stock["earnings_mode"]]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="简报 JSON")
    parser.add_argument(
        "--market", type=Path, required=True, help="market_data.py 生成的行情 JSON"
    )
    parser.add_argument("--out", type=Path, help="输出 HTML，默认与简报 JSON 同名")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    market = json.loads(args.market.read_text(encoding="utf-8"))
    problems = find_report_problems(report, market)
    if problems:
        sys.stderr.write(
            "简报 JSON 不符合约定：\n"
            + "\n".join(f"- {problem}" for problem in problems)
            + "\n"
        )
        return 1
    sort_fixed_items(report)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(DATA_PLACEHOLDER) != 1:
        sys.stderr.write(
            f"模板里的 {DATA_PLACEHOLDER} 占位符必须恰好出现一次：{TEMPLATE_PATH}\n"
        )
        return 1

    # 数据放在 <script> 里，"</" 会提前结束标签
    payload = json.dumps(
        {"report": report, "market": market}, ensure_ascii=False
    ).replace("</", "<\\/")
    out_path = args.out or args.report.with_suffix(".html")
    out_path.write_text(template.replace(DATA_PLACEHOLDER, payload), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
