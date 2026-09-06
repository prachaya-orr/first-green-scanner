"""Data access layer: price history + watchlist loading.

แยกการ "ดึงข้อมูล" ออกจากการ "คำนวณ" อย่างชัดเจน
- ทุกฟังก์ชันดึงข้อมูลถูก cache (Streamlit) เพื่อไม่โหลดซ้ำ
- ใช้ logging แทนการกลืน error เงียบ ๆ เพื่อให้ debug ได้ใน production
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from .config import CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

# ── Watchlist template ─────────────────────────────────────────────────────
_TEMPLATE_LINES = (
    "# watchlist template — 1 คอลัมน์ = ชื่อหุ้น 1 ตัว (บรรทัดละ 1 ตัว)",
    "# TH ลงท้าย .BK | HK ลงท้าย .HK | US ใส่ชื่อตรงๆ",
    "# ลบบรรทัด # ออกได้ แล้วแก้เป็นหุ้นที่ต้องการ",
    "PTT.BK",
    "KBANK.BK",
    "CPALL.BK",
    "0700.HK",
    "AAPL",
    "NVDA",
)


def _normalize_symbols(series: pd.Series) -> list[str]:
    """ทำความสะอาดคอลัมน์ชื่อหุ้น: ตัดช่องว่าง เป็นตัวพิมพ์ใหญ่ ทิ้งค่าว่าง."""
    return series.dropna().astype(str).str.strip().str.upper().tolist()


@st.cache_data(show_spinner=False)
def load_stock_list(filename: str) -> list[str]:
    """อ่านรายชื่อหุ้นจากไฟล์ CSV (1 คอลัมน์ ไม่มี header)."""
    try:
        df = pd.read_csv(filename, header=None, comment="#")
        return _normalize_symbols(df.iloc[:, 0])
    except FileNotFoundError:
        logger.warning("watchlist file not found: %s", filename)
        return []
    except Exception:
        logger.exception("failed to load watchlist: %s", filename)
        return []


def parse_uploaded_csv(file) -> list[str]:
    """แปลงไฟล์ CSV ที่ผู้ใช้อัปโหลดเป็นรายชื่อหุ้น (ข้ามบรรทัดคอมเมนต์ #)."""
    df = pd.read_csv(file, header=None, comment="#")
    return _normalize_symbols(df.iloc[:, 0])


def parse_manual_input(raw: str) -> list[str]:
    """แปลงข้อความที่ผู้ใช้พิมพ์ (คั่นด้วย , หรือขึ้นบรรทัดใหม่) เป็นรายชื่อหุ้น."""
    tokens = raw.replace("\n", ",").split(",")
    return [t.strip().upper() for t in tokens if t.strip()]


def build_template_csv() -> bytes:
    """สร้างเนื้อหา CSV แม่แบบสำหรับดาวน์โหลด (encode utf-8-sig ให้ Excel อ่านไทยได้)."""
    return ("\n".join(_TEMPLATE_LINES) + "\n").encode("utf-8-sig")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_history(symbol: str, period_days: int) -> pd.DataFrame:
    """ดึงราคา OHLCV รายวันจาก Yahoo Finance แล้ว cache ตาม TTL.

    Args:
        symbol: ชื่อหุ้นเต็ม (มี suffix ตลาด เช่น PTT.BK)
        period_days: จำนวนวันปฏิทินย้อนหลังที่ต้องการ

    Returns:
        DataFrame คอลัมน์ Open/High/Low/Close/Volume (คืน DataFrame ว่างถ้าดึงไม่ได้)
    """
    end = datetime.today()
    start = end - timedelta(days=period_days)
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
    except Exception:
        logger.exception("yfinance download failed: %s", symbol)
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df
