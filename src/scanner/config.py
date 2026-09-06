"""Central configuration and constants for the scanner.

รวมค่าคงที่และการตั้งค่าทั้งหมดไว้ที่เดียว เพื่อให้ปรับจูนง่าย
และไม่มี "magic number" กระจายอยู่ทั่วโค้ด
"""

from __future__ import annotations

from typing import Final

from .models import MarketInfo

# ── Concurrency ────────────────────────────────────────────────────────────
# จำนวน worker สูงสุดสำหรับดึงข้อมูลพร้อมกัน งานนี้เป็น I/O-bound (รอเน็ต)
# ตั้งไว้ระดับกลางเพื่อความเร็ว แต่ไม่สูงจนเสี่ยงโดน rate-limit จาก Yahoo
MAX_WORKERS: Final[int] = 12

# ── Data fetching ──────────────────────────────────────────────────────────
# cache ข้อมูลราคาไว้ 1 ชั่วโมง (วินาที)
CACHE_TTL_SECONDS: Final[int] = 3600

# ดึงข้อมูลเผื่อ (วันปฏิทิน) นอกเหนือจากช่วง lookback ที่ผู้ใช้เลือก
# เผื่อให้พอสำหรับคำนวณ Vol_MA + quiet period + ช่วงวาดกราฟ 90 วัน
FETCH_BUFFER_DAYS: Final[int] = 200

# ── Signal calculation ─────────────────────────────────────────────────────
# จำนวนวันสำหรับค่าเฉลี่ย volume (Vol_MA)
VOLUME_MA_PERIOD: Final[int] = 20

# ต้องมีข้อมูลอย่างน้อยเท่านี้ถึงจะสแกนได้ (Vol_MA period + เผื่อ)
MIN_ROWS_REQUIRED: Final[int] = VOLUME_MA_PERIOD + 10

# จำนวนแท่งขั้นต่ำในช่วง quiet ที่ยอมรับได้ว่ามีข้อมูลพอประเมิน
MIN_QUIET_ROWS: Final[int] = 5

# ── Chart rendering ────────────────────────────────────────────────────────
# ช่วงข้อมูลรอบวันสัญญาณที่นำมาวาดกราฟ (วันปฏิทิน)
CHART_DAYS_BEFORE: Final[int] = 80
CHART_DAYS_AFTER: Final[int] = 10

# ── Market definitions ─────────────────────────────────────────────────────
# เกณฑ์สภาพคล่องต่อวันแยกตามตลาด ใช้ "เตือน" เท่านั้น ไม่ตัดหุ้นออก
# เพราะสกุลเงินคนละหน่วย เทียบตรง ๆ ไม่ได้
MARKETS: Final[dict[str, MarketInfo]] = {
    "TH": MarketInfo(code="TH", suffix=".BK", currency="THB", liquidity_threshold=50_000_000),
    "HK": MarketInfo(code="HK", suffix=".HK", currency="HKD", liquidity_threshold=20_000_000),
    "US": MarketInfo(code="US", suffix="", currency="USD", liquidity_threshold=5_000_000),
}

DEFAULT_MARKET: Final[str] = "US"

# ── Watchlist preset files ─────────────────────────────────────────────────
PRESET_FILES: Final[dict[str, str]] = {
    "SET": "SET.csv",
    "SET100": "SET100.csv",
    "S&P500": "SP500.csv",
    "US Stock": "US_Stock.csv",
}
