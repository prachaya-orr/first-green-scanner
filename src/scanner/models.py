"""Typed data models shared across the scanner.

ใช้ dataclass แทน dict ดิบ ๆ เพื่อให้:
- editor ช่วยเตือนพิมพ์ชื่อ field ผิด
- อ่านโค้ดแล้วรู้ทันทีว่าข้อมูลมี field อะไรบ้าง ชนิดอะไร
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarketInfo:
    """ข้อมูลประจำตลาด (ไทย/ฮ่องกง/สหรัฐฯ)."""

    code: str
    suffix: str
    currency: str
    liquidity_threshold: float


@dataclass(frozen=True, slots=True)
class ScanConfig:
    """พารามิเตอร์การสแกนที่ผู้ใช้ปรับได้จาก sidebar.

    เก็บค่าที่ "แปลงหน่วยแล้ว" (เช่น percent -> สัดส่วน) เพื่อให้ logic
    การสแกนใช้ได้ตรง ๆ โดยไม่ต้องแปลงซ้ำ
    """

    change_threshold: float  # สัดส่วน เช่น 0.10 = 10%
    volume_multiplier: float
    volume_ma_period: int
    quiet_period_days: int
    quiet_threshold: float  # สัดส่วน เช่น 0.07 = 7%
    lookback_days: int


@dataclass(frozen=True, slots=True)
class Signal:
    """สัญญาณ "เขียวแท่งแรก" ที่ผ่านทุกเงื่อนไข 1 รายการ."""

    symbol: str  # ชื่อย่อสำหรับแสดงผล (ตัด suffix ตลาดออก)
    full_symbol: str  # ชื่อเต็มที่ใช้ดึงข้อมูล (มี suffix)
    market: str
    date: str  # YYYY-MM-DD
    open: float
    close: float
    change_pct: float  # เปอร์เซ็นต์ เช่น 12.5
    volume: int
    vol_ma: int
    vol_ratio: float
    trading_value: float
    currency: str
    liquidity_threshold: float
    below_liquidity: bool

    def as_row(self) -> dict:
        """แปลงเป็น dict สำหรับสร้าง DataFrame แสดงผล."""
        return {
            "Symbol": self.symbol,
            "Full_Symbol": self.full_symbol,
            "Market": self.market,
            "Date": self.date,
            "Open": self.open,
            "Close": self.close,
            "Change_%": self.change_pct,
            "Volume": self.volume,
            "Vol_MA20": self.vol_ma,
            "Vol_Ratio_x": self.vol_ratio,
            "Trading_Value": self.trading_value,
            "Currency": self.currency,
            "Below_Liq": self.below_liquidity,
        }
