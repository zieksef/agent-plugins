"""拉取 Yahoo 日线行情并计算技术指标，供 premarket 简报使用。

完整数据写入 --out 文件；标准输出只打印摘要（最近 14 个交易日 + 指标）。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"
# Yahoo 对默认的 urllib User-Agent 返回 429
USER_AGENT = "Mozilla/5.0"
REQUEST_TIMEOUT_SECONDS = 20
FETCH_ATTEMPTS = 2

NEW_YORK = ZoneInfo("America/New_York")
CHART_WINDOW = 126
RECENT_WINDOW = 14
RSI_PERIOD = 14
VOLUME_BASELINE_DAYS = 20
SWING_SPAN = 3
LEVEL_TOLERANCE = 0.02
MAX_LEVELS_PER_SIDE = 2
# 小于这个幅度的缺口多是报价噪音
MIN_GAP_PCT = 0.5

logger = logging.getLogger("market_data")

Candle = dict[str, Any]


def fetch_chart(
    symbol: str, chart_range: str, interval: str, include_extended: bool
) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "range": chart_range,
            "interval": interval,
            "includePrePost": str(include_extended).lower(),
        }
    )
    url = CHART_URL.format(symbol=urllib.parse.quote(symbol), query=query)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    last_error: Exception | None = None
    for _ in range(FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                chart = json.load(response)["chart"]
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
        ) as exc:
            last_error = exc
            continue
        if chart.get("error"):
            raise ValueError(
                f"fetch chart (symbol={symbol}, range={chart_range}): {chart['error']}"
            )
        return chart["result"][0]
    raise ValueError(
        f"fetch chart (symbol={symbol}, range={chart_range}): {last_error}"
    )


def parse_candles(result: dict[str, Any]) -> list[Candle]:
    quote = result["indicators"]["quote"][0]
    candles: list[Candle] = []
    for index, timestamp in enumerate(result.get("timestamp", [])):
        values = [quote[key][index] for key in ("open", "high", "low", "close")]
        # 停牌日和尚未结算的当日，Yahoo 返回 null
        if any(value is None for value in values):
            continue
        candles.append(
            {
                "date": datetime.fromtimestamp(timestamp, NEW_YORK).date().isoformat(),
                "open": round(values[0], 4),
                "high": round(values[1], 4),
                "low": round(values[2], 4),
                "close": round(values[3], 4),
                "volume": quote["volume"][index] or 0,
            }
        )
    return candles


def simple_moving_average(values: list[float], period: int) -> list[float | None]:
    averages: list[float | None] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= period:
            running -= values[index - period]
        averages.append(round(running / period, 4) if index >= period - 1 else None)
    return averages


def relative_strength_index(closes: list[float], period: int) -> float | None:
    """Wilder 平滑的 RSI。"""
    if len(closes) <= period:
        return None
    changes = [
        current - previous
        for previous, current in zip(closes, closes[1:], strict=False)
    ]
    average_gain = sum(max(change, 0.0) for change in changes[:period]) / period
    average_loss = sum(max(-change, 0.0) for change in changes[:period]) / period
    for change in changes[period:]:
        average_gain = (average_gain * (period - 1) + max(change, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0.0)) / period
    if average_loss == 0:
        return 100.0
    return round(100 - 100 / (1 + average_gain / average_loss), 1)


def find_swing_points(candles: list[Candle], span: int) -> list[dict[str, Any]]:
    """局部高低点：前后各 span 根 K 线内唯一的最高价或最低价。"""
    swings: list[dict[str, Any]] = []
    for index in range(span, len(candles) - span):
        window = candles[index - span : index + span + 1]
        highs = [candle["high"] for candle in window]
        lows = [candle["low"] for candle in window]
        candle = candles[index]
        if candle["high"] == max(highs) and highs.count(candle["high"]) == 1:
            swings.append(
                {"date": candle["date"], "kind": "high", "price": candle["high"]}
            )
        if candle["low"] == min(lows) and lows.count(candle["low"]) == 1:
            swings.append(
                {"date": candle["date"], "kind": "low", "price": candle["low"]}
            )
    return swings


def find_price_levels(
    swings: list[dict[str, Any]], last_close: float
) -> dict[str, list[dict[str, Any]]]:
    """把价格相近的高低点聚成价位；至少被触及两次才算支撑或压力。"""
    clusters: list[list[dict[str, Any]]] = []
    for swing in sorted(swings, key=lambda item: item["price"]):
        if clusters:
            center = sum(item["price"] for item in clusters[-1]) / len(clusters[-1])
            if abs(swing["price"] - center) / center <= LEVEL_TOLERANCE:
                clusters[-1].append(swing)
                continue
        clusters.append([swing])

    levels = [
        {
            "price": round(sum(item["price"] for item in cluster) / len(cluster), 2),
            "touches": len(cluster),
            "last_touch": max(item["date"] for item in cluster),
        }
        for cluster in clusters
        if len(cluster) >= 2
    ]
    support = sorted(
        (level for level in levels if level["price"] < last_close),
        key=lambda level: -level["price"],
    )
    resistance = sorted(
        (level for level in levels if level["price"] > last_close),
        key=lambda level: level["price"],
    )
    return {
        "support": support[:MAX_LEVELS_PER_SIDE],
        "resistance": resistance[:MAX_LEVELS_PER_SIDE],
    }


def find_gaps(candles: list[Candle]) -> list[dict[str, Any]]:
    """跳空缺口：当日整根 K 线与前一日完全不重叠。"""
    gaps: list[dict[str, Any]] = []
    for index in range(1, len(candles)):
        previous, current = candles[index - 1], candles[index]
        later = candles[index + 1 :]
        if abs(current["open"] / previous["close"] - 1) * 100 < MIN_GAP_PCT:
            continue
        if current["low"] > previous["high"]:
            gaps.append(
                {
                    "date": current["date"],
                    "direction": "up",
                    "from": previous["high"],
                    "to": current["low"],
                    "filled": any(
                        candle["low"] <= previous["high"] for candle in later
                    ),
                }
            )
        elif current["high"] < previous["low"]:
            gaps.append(
                {
                    "date": current["date"],
                    "direction": "down",
                    "from": previous["low"],
                    "to": current["high"],
                    "filled": any(
                        candle["high"] >= previous["low"] for candle in later
                    ),
                }
            )
    return gaps


def find_recent_extremes(candles: list[Candle]) -> dict[str, dict[str, Any]]:
    highest = max(candles, key=lambda candle: candle["high"])
    lowest = min(candles, key=lambda candle: candle["low"])
    return {
        "recent_high": {"price": highest["high"], "date": highest["date"]},
        "recent_low": {"price": lowest["low"], "date": lowest["date"]},
    }


def percent_change(current: float, base: float) -> float | None:
    if not base:
        return None
    return round((current / base - 1) * 100, 2)


def fetch_extended_quote(symbol: str, last_close: float) -> dict[str, Any] | None:
    """最新一笔盘前或盘后价格；当前处于正常交易时段或没有延长时段数据时返回 None。"""
    result = fetch_chart(symbol, "1d", "5m", include_extended=True)
    closes = result["indicators"]["quote"][0]["close"]
    bars = [
        (timestamp, close)
        for timestamp, close in zip(result.get("timestamp", []), closes, strict=False)
        if close
    ]
    if not bars:
        return None
    timestamp, price = bars[-1]
    periods = result["meta"]["currentTradingPeriod"]
    if periods["regular"]["start"] <= timestamp < periods["regular"]["end"]:
        return None
    session = (
        "pre"
        if periods["pre"]["start"] <= timestamp < periods["pre"]["end"]
        else "post"
    )
    return {
        "session": session,
        "price": round(price, 4),
        "time_et": datetime.fromtimestamp(timestamp, NEW_YORK).strftime(
            "%Y-%m-%d %H:%M"
        ),
        "change_pct": percent_change(price, last_close),
    }


def build_symbol_data(symbol: str) -> dict[str, Any]:
    result = fetch_chart(symbol, "1y", "1d", include_extended=False)
    meta = result["meta"]
    candles = parse_candles(result)
    if len(candles) < 2:
        raise ValueError(
            f"build symbol data (symbol={symbol}): only {len(candles)} daily candles"
        )

    closes = [candle["close"] for candle in candles]
    averages = {
        period: simple_moving_average(closes, period) for period in (20, 50, 200)
    }
    for index, candle in enumerate(candles):
        candle["change_pct"] = (
            percent_change(candle["close"], closes[index - 1]) if index else None
        )
        for period, series in averages.items():
            candle[f"sma{period}"] = series[index]

    chart_candles = candles[-CHART_WINDOW:]
    last = candles[-1]
    baseline_volumes = [
        candle["volume"] for candle in candles[-VOLUME_BASELINE_DAYS - 1 : -1]
    ]
    baseline_volume = sum(baseline_volumes) / len(baseline_volumes)
    window_base = (
        candles[-RECENT_WINDOW - 1]["close"]
        if len(candles) > RECENT_WINDOW
        else candles[0]["close"]
    )
    swings = find_swing_points(chart_candles, SWING_SPAN)
    week52_high = meta.get("fiftyTwoWeekHigh")

    extended = None
    if meta.get("hasPrePostMarketData"):
        try:
            extended = fetch_extended_quote(symbol, last["close"])
        except (ValueError, KeyError) as exc:
            logger.warning(
                "extended quote unavailable, symbol: %s, error: %s", symbol, exc
            )

    return {
        "symbol": symbol,
        "name": meta.get("longName") or meta.get("shortName") or symbol,
        "instrument_type": meta.get("instrumentType"),
        "currency": meta.get("currency"),
        "last_date": last["date"],
        "last_close": last["close"],
        "last_change_pct": last["change_pct"],
        "extended": extended,
        "indicators": {
            "sma20": last["sma20"],
            "sma50": last["sma50"],
            "sma200": last["sma200"],
            "rsi14": relative_strength_index(closes, RSI_PERIOD),
            "volume_ratio": round(last["volume"] / baseline_volume, 2)
            if baseline_volume
            else None,
            "change_14d_pct": percent_change(last["close"], window_base),
            "week52_high": week52_high,
            "week52_low": meta.get("fiftyTwoWeekLow"),
            "pct_from_week52_high": percent_change(last["close"], week52_high)
            if week52_high
            else None,
            **find_price_levels(swings, last["close"]),
            **find_recent_extremes(candles[-RECENT_WINDOW:]),
            "gaps": find_gaps(candles[-RECENT_WINDOW - 1 :]),
        },
        "swings": swings,
        "candles": chart_candles,
    }


def summarize(symbol_data: dict[str, Any]) -> dict[str, Any]:
    if "error" in symbol_data:
        return symbol_data
    summary = dict(symbol_data)
    recent = symbol_data["candles"][-RECENT_WINDOW:]
    if symbol_data["instrument_type"] != "EQUITY":
        # ETF 和指数只用来判断个股是否跟随板块或大盘，逐日涨跌幅就够了
        del summary["candles"], summary["swings"]
        summary["daily_change_pct"] = {
            candle["date"]: candle["change_pct"] for candle in recent
        }
        return summary
    summary["candles"] = [
        {
            key: candle[key]
            for key in ("date", "open", "high", "low", "close", "volume", "change_pct")
        }
        for candle in recent
    ]
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "symbols", nargs="+", help="股票、ETF 或指数代码，例如 RKLB ITA ^GSPC ^IXIC"
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="完整行情数据的输出文件（JSON）"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s"
    )

    symbols: dict[str, Any] = {}
    for symbol in dict.fromkeys(symbol.upper() for symbol in args.symbols):
        try:
            symbols[symbol] = build_symbol_data(symbol)
        except (ValueError, KeyError, IndexError) as exc:
            logger.error(
                "failed to load market data, symbol: %s, error: %s", symbol, exc
            )
            symbols[symbol] = {"symbol": symbol, "error": str(exc)}

    market = {
        "generated_at_et": datetime.now(NEW_YORK).strftime("%Y-%m-%d %H:%M"),
        "source": "Yahoo Finance chart API（约 15 分钟延迟）",
        "symbols": symbols,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(market, ensure_ascii=False), encoding="utf-8")

    summary = {
        **market,
        "symbols": {symbol: summarize(data) for symbol, data in symbols.items()},
    }
    json.dump(summary, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 1 if all("error" in data for data in symbols.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
