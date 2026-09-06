"""first-green-scanner core package.

โครงสร้าง:
    config.py   — ค่าคงที่และการตั้งค่า
    models.py   — dataclass (ScanConfig, Signal, MarketInfo)
    data.py     — ดึงข้อมูล + โหลด watchlist
    scanner.py  — logic การคำนวณสัญญาณ
    charts.py   — วาดกราฟ Plotly
"""

from __future__ import annotations

from .models import MarketInfo, ScanConfig, Signal

__all__ = ["MarketInfo", "ScanConfig", "Signal"]
