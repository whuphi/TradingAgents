"""Analyze an A-share ticker with free data.

Yahoo is blocked in this sandbox and Alpha Vantage's free tier is 25 req/day,
so we pre-warm the framework's OHLCV cache from akshare (Sina) and let the
yfinance vendor path compute every technical indicator locally.

Usage:
    .venv/bin/python analyze_ashare.py 000892.SZ 2026-11-05
"""
import os
import sys
from copy import deepcopy

import akshare as ak
import pandas as pd
from dotenv import load_dotenv

from tradingagents.dataflows.symbols import normalize_symbol, safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

load_dotenv("/workspace/.env")

symbol = sys.argv[1]
trade_date = sys.argv[2]
ak_symbol = ("sh" if symbol.startswith("6") else "sz") + symbol.split(".")[0]

# --- pre-warm the OHLCV cache in yfinance's column format ---
canonical = normalize_symbol(symbol)
cache_dir = DEFAULT_CONFIG["data_cache_dir"]
os.makedirs(cache_dir, exist_ok=True)
path = os.path.join(cache_dir, f"{safe_ticker_component(canonical)}-YFin-data.csv")
end = pd.Timestamp.today().strftime("%Y%m%d")
start = (pd.Timestamp.today() - pd.DateOffset(years=5)).strftime("%Y%m%d")
raw = ak.stock_zh_a_daily(symbol=ak_symbol, start_date=start, end_date=end, adjust="qfq")
pd.DataFrame({
    "Date": raw["date"], "Open": raw["open"], "High": raw["high"],
    "Low": raw["low"], "Close": raw["close"], "Volume": raw["volume"],
}).to_csv(path, index=False, encoding="utf-8")
print(f"[cache] {path} rows={len(raw)} last={raw['date'].iloc[-1]} close={raw['close'].iloc[-1]}")

# --- run the graph ---
config = deepcopy(DEFAULT_CONFIG)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "news_data": "yfinance",
    "fundamental_data": "yfinance",
}
config["output_language"] = "Chinese"

ta = TradingAgentsGraph(selected_analysts=["market"], debug=True, config=config)
state, decision = ta.propagate(symbol, trade_date)
print("\n===== FINAL DECISION =====\n" + str(decision))
print("\n===== REPORTS SAVED =====")
print(ta.save_reports(state, symbol))
