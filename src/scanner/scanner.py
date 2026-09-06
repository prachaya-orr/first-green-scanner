"""Core scanning logic — pure domain functions.

โมดูลนี้ "ไม่พึ่ง Streamlit" เลย รับ DataFrame + ScanConfig เข้ามา
แล้วคืน list[Signal] ออกไป ทำให้เขียน unit test ได้ง่ายและ reuse ได้
"""

from __future__ import annotations

import logging

import pandas as pd

from . import config
from .data import fetch_history
from .models import ScanConfig, Signal

logger = logging.getLogger(__name__)


def get_market(symbol: str) -> str:
    """ตรวจตลาดจาก suffix ของชื่อหุ้น."""
    for market in config.MARKETS.values():
        if market.suffix and symbol.endswith(market.suffix):
            return market.code
    return config.DEFAULT_MARKET


def strip_suffix(symbol: str) -> str:
    """ตัด suffix ตลาดออก เพื่อใช้เป็นชื่อย่อแสดงผล."""
    for market in config.MARKETS.values():
        if market.suffix and symbol.endswith(market.suffix):
            return symbol[: -len(market.suffix)]
    return symbol


def format_trading_value(value: float, currency: str) -> str:
    """จัดรูปแบบมูลค่าเทรดเป็น M/B พร้อมสกุลเงิน."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}B {currency}"
    return f"{value / 1_000_000:,.1f}M {currency}"


def is_quiet_before(
    df: pd.DataFrame, current_iloc: int, quiet_days: int, quiet_threshold: float
) -> bool:
    """ตรวจว่าช่วงก่อนวันสัญญาณราคานิ่งจริงไหม.

    "นิ่ง" = ในช่วง quiet_days ก่อนหน้า ไม่มีแท่งเขียวไหนบวกเกิน quiet_threshold
    """
    start_i = max(0, current_iloc - quiet_days)
    prior = df.iloc[start_i:current_iloc]
    if len(prior) < config.MIN_QUIET_ROWS:
        return False
    green_pct = (prior["Close"] - prior["Open"]) / prior["Open"]
    return float(green_pct.max()) < quiet_threshold


def _build_signal(symbol: str, dt: pd.Timestamp, row: pd.Series) -> Signal:
    """ประกอบ Signal จากแถวข้อมูลที่ผ่านเงื่อนไขแล้ว."""
    market = get_market(symbol)
    market_info = config.MARKETS[market]
    trading_value = float(row["Close"]) * float(row["Volume"])
    vol_ma = row["Vol_MA"]

    return Signal(
        symbol=strip_suffix(symbol),
        full_symbol=symbol,
        market=market,
        date=dt.strftime("%Y-%m-%d"),
        open=round(float(row["Open"]), 2),
        close=round(float(row["Close"]), 2),
        change_pct=round(float(row["Chg_OC"]) * 100, 2),
        volume=int(row["Volume"]),
        vol_ma=int(vol_ma) if not pd.isna(vol_ma) else 0,
        vol_ratio=round(float(row["Vol_Ratio"]), 1),
        trading_value=trading_value,
        currency=market_info.currency,
        liquidity_threshold=market_info.liquidity_threshold,
        below_liquidity=trading_value < market_info.liquidity_threshold,
    )


def _add_indicators(df: pd.DataFrame, vol_ma_period: int) -> pd.DataFrame:
    """เพิ่มคอลัมน์ตัวชี้วัด: Vol_MA, Chg_OC, Vol_Ratio.

    ใช้ shift(1) ก่อน rolling เพื่อให้ Vol_MA คิดจากวันก่อนหน้าเท่านั้น
    ไม่รวม volume ของวันที่เกิดสัญญาณ (กัน spike ดันค่าเฉลี่ยตัวเอง
    เหมือนหลักการ volume[1] ใน Pine Script)
    """
    df = df.copy()
    df["Vol_MA"] = df["Volume"].shift(1).rolling(vol_ma_period).mean()
    df["Chg_OC"] = (df["Close"] - df["Open"]) / df["Open"]
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA"]
    return df


def _passes_conditions(row: pd.Series, cfg: ScanConfig) -> bool:
    """ตรวจเงื่อนไขระดับแท่งเทียน (ยังไม่รวมเงื่อนไข quiet period)."""
    if not (row["Close"] > row["Open"]):
        return False
    if float(row["Chg_OC"]) < cfg.change_threshold:
        return False
    if pd.isna(row["Vol_Ratio"]):
        return False
    if float(row["Vol_Ratio"]) < cfg.volume_multiplier:
        return False
    return True


def scan_one_stock(symbol: str, cfg: ScanConfig) -> list[Signal]:
    """สแกนหุ้น 1 ตัว คืน list ของสัญญาณที่ผ่านทุกเงื่อนไข."""
    fetch_days = cfg.lookback_days + config.FETCH_BUFFER_DAYS
    df = fetch_history(symbol, fetch_days)

    if df.empty or len(df) < config.MIN_ROWS_REQUIRED:
        return []

    df = _add_indicators(df, cfg.volume_ma_period)

    # นับ "แท่งเทรดจริง" ล่าสุด ไม่ใช่วันปฏิทิน (กันปัญหาวันหยุด)
    df_scan = df.tail(cfg.lookback_days)

    signals: list[Signal] = []
    for dt, row in df_scan.iterrows():
        if not _passes_conditions(row, cfg):
            continue
        global_i = df.index.get_loc(dt)
        if not is_quiet_before(df, global_i, cfg.quiet_period_days, cfg.quiet_threshold):
            continue
        signals.append(_build_signal(symbol, dt, row))

    return signals
