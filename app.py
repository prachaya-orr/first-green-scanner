"""
╔══════════════════════════════════════════════════════════════╗
║     🟢 VITALi — First Green Candle + Volume Scanner          ║
║     VITALi © 2026                                            ║
╚══════════════════════════════════════════════════════════════╝

UI layer เท่านั้น — logic ทั้งหมดอยู่ใน package `scanner`
(config / models / data / scanner / charts)
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ให้ import package `scanner` จากโฟลเดอร์ src ได้เมื่อรันด้วย `streamlit run app.py`
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scanner import ScanConfig, Signal, charts, data, scanner  # noqa: E402  # noqa: E402
from scanner import config as cfg  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG + STYLE
# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title="VITALi — First Green Scanner", page_icon="🟢", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Kanit', sans-serif; }
.main { background-color: #0a1628; color: #f0f0f0; }
.title-box {
    background: linear-gradient(135deg, #0d1f3c, #1a3a6b);
    border: 1px solid #c9a84c; border-radius: 12px;
    padding: 20px 28px; margin-bottom: 24px;
}
.title-box h1 { color: #c9a84c; font-size: 26px; margin: 0; }
.title-box p  { color: #aac4e8; font-size: 14px; margin: 4px 0 0; }
.metric-card {
    background: #0d1f3c; border: 1px solid #1e3a6e;
    border-radius: 10px; padding: 16px; text-align: center;
}
.metric-card .label { color: #7a9cc4; font-size: 13px; }
.metric-card .value { color: #c9a84c; font-size: 28px; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="title-box">
    <h1>🟢 VITALi — First Green Candle Scanner</h1>
    <p>สแกนหา "เขียวแท่งแรก" พร้อม Volume พิเศษ | VITALi © 2026</p>
</div>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════
# SIDEBAR — เลือก watchlist + ตั้งค่า
# ══════════════════════════════════════════════════════════════
def render_sidebar() -> tuple[list[str], ScanConfig, bool]:
    """วาด sidebar แล้วคืน (รายชื่อหุ้น, การตั้งค่า, กดปุ่มสแกนหรือยัง)."""
    with st.sidebar:
        st.markdown("### ⚙️ ตั้งค่าการสแกน")
        lookback = st.slider("ดูย้อนหลัง (แท่งเทรดล่าสุด)", 1, 30, 5)
        change_th = st.slider("บวก >= (%)", 5, 20, 10)
        vol_mult = st.slider("Volume >= (x เท่า)", 1.0, 10.0, 3.0, step=0.5)
        quiet_days = st.slider("Quiet period (วัน)", 10, 60, 30)
        quiet_th = st.slider("Quiet threshold (%)", 3, 15, 7)

        st.markdown("---")
        st.markdown("### 📋 รายชื่อหุ้น")
        source = st.radio(
            "เลือกรายชื่อหุ้น",
            [*cfg.PRESET_FILES.keys(), "พิมพ์เอง", "อัปโหลด CSV"],
        )

        stock_list = _resolve_stock_list(source)
        st.markdown("---")
        run_btn = st.button("🚀 เริ่มสแกน", use_container_width=True, type="primary")

    scan_config = ScanConfig(
        change_threshold=change_th / 100,
        volume_multiplier=vol_mult,
        volume_ma_period=cfg.VOLUME_MA_PERIOD,
        quiet_period_days=quiet_days,
        quiet_threshold=quiet_th / 100,
        lookback_days=lookback,
    )
    return stock_list, scan_config, run_btn


def _resolve_stock_list(source: str) -> list[str]:
    """คืนรายชื่อหุ้นตามแหล่งที่ผู้ใช้เลือก."""
    if source in cfg.PRESET_FILES:
        stocks = data.load_stock_list(cfg.PRESET_FILES[source])
        st.caption(f"✅ {len(stocks)} ตัว")
        return stocks

    if source == "พิมพ์เอง":
        raw = st.text_area(
            "พิมพ์ชื่อหุ้น (คั่นด้วย , หรือขึ้นบรรทัดใหม่)",
            placeholder="เช่น\nXO.BK\nKGEN.BK\nPTT.BK",
        )
        stocks = data.parse_manual_input(raw) if raw.strip() else []
        if stocks:
            st.caption(f"✅ {len(stocks)} ตัว")
        return stocks

    if source == "อัปโหลด CSV":
        st.download_button(
            "⬇️ โหลด template ตัวอย่าง",
            data=data.build_template_csv(),
            file_name="watchlist_template.csv",
            mime="text/csv",
            use_container_width=True,
            help="ไฟล์ตัวอย่าง 1 คอลัมน์ = ชื่อหุ้น (TH .BK / HK .HK / US ตรงๆ)",
        )
        uploaded = st.file_uploader("CSV (1 คอลัมน์ = ชื่อหุ้น)", type="csv")
        if uploaded:
            stocks = data.parse_uploaded_csv(uploaded)
            st.caption(f"✅ {len(stocks)} ตัว")
            return stocks

    return []


# ══════════════════════════════════════════════════════════════
# SCAN ORCHESTRATION
# ══════════════════════════════════════════════════════════════
def run_scan(stock_list: list[str], scan_config: ScanConfig) -> list[Signal]:
    """ดึง + สแกนหลายหุ้นพร้อมกัน (I/O-bound → ThreadPool)."""
    all_signals: list[Signal] = []
    total = len(stock_list)
    progress = st.progress(0.0, text="กำลังสแกน...")

    workers = min(cfg.MAX_WORKERS, total)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scanner.scan_one_stock, sym, scan_config): sym for sym in stock_list
        }
        for done, future in enumerate(as_completed(futures), start=1):
            try:
                all_signals.extend(future.result())
            except Exception:
                logging.exception("scan failed for %s", futures[future])
            progress.progress(done / total, text=f"กำลังสแกน... ({done}/{total})")

    progress.empty()
    return all_signals


# ══════════════════════════════════════════════════════════════
# RESULTS RENDERING
# ══════════════════════════════════════════════════════════════
def _metric_card(label: str, value: str) -> str:
    return f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div></div>'


def render_results(signals: list[Signal]) -> None:
    """แสดง metric cards + ตาราง + กราฟ."""
    unique_sym = len({s.symbol for s in signals}) if signals else 0
    avg_vol = round(np.mean([s.vol_ratio for s in signals]), 1) if signals else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(_metric_card("พบสัญญาณ", str(len(signals))), unsafe_allow_html=True)
    c2.markdown(_metric_card("จำนวนหุ้น", str(unique_sym)), unsafe_allow_html=True)
    c3.markdown(_metric_card("Vol Ratio เฉลี่ย", f"{avg_vol}x"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not signals:
        st.info("ℹ️ ไม่พบสัญญาณในช่วงที่กำหนด ลองเพิ่ม lookback หรือลด threshold ดูครับ")
        return

    _render_table(signals)
    _render_chart_picker(signals)


def _render_table(signals: list[Signal]) -> None:
    df = pd.DataFrame([s.as_row() for s in signals])
    df = df.sort_values("Trading_Value", ascending=False).reset_index(drop=True)
    df.index = df.index + 1

    st.markdown("### 📋 ผลการสแกน")
    st.caption(
        "🔴 แถวพื้นสีแดงอ่อน = Trading Value ต่ำกว่าเกณฑ์สภาพคล่องแนะนำของตลาดนั้นๆ "
        "(TH < 50M บาท · HK < 20M HKD · US < 5M USD) — ไม่ได้ตัดออก แค่เตือนความเสี่ยงถูกปั่นราคา"
    )

    display = df[["Symbol", "Market", "Date", "Open", "Close", "Change_%", "Vol_Ratio_x"]].copy()
    display["Trading Value"] = [
        scanner.format_trading_value(v, c)
        for v, c in zip(df["Trading_Value"], df["Currency"], strict=False)
    ]
    display.columns = [
        "หุ้น",
        "ตลาด",
        "วันที่",
        "Open",
        "Close",
        "บวก (%)",
        "Vol Ratio",
        "Trading Value",
    ]
    display["บวก (%)"] = display["บวก (%)"].apply(lambda x: f"+{x:.1f}%")
    display["Vol Ratio"] = display["Vol Ratio"].apply(lambda x: f"{x:.1f}x")

    below_liq = df["Below_Liq"].values

    def highlight(row):
        i = display.index.get_loc(row.name)
        if below_liq[i]:
            return ["background-color: #4a1414; color: #ff9999"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display.style.apply(highlight, axis=1),
        use_container_width=True,
        height=min(400, 60 + len(display) * 38),
    )


def _render_chart_picker(signals: list[Signal]) -> None:
    st.markdown("### 📈 ดูกราฟ")
    options = [f"{s.symbol} — {s.date}" for s in signals]
    selected = st.selectbox("เลือกหุ้นที่ต้องการดู", options)
    if not selected:
        return

    sig = signals[options.index(selected)]
    with st.spinner(f"กำลังโหลดกราฟ {sig.symbol}..."):
        df_chart = charts.load_chart_data(sig.full_symbol, sig.date, cfg.FETCH_BUFFER_DAYS)
        fig = charts.build_candlestick(df_chart, sig.symbol, sig.date)

    if fig is None:
        st.error("โหลดข้อมูลกราฟไม่ได้ครับ")
        return

    st.plotly_chart(fig, use_container_width=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Open", f"{sig.open:.2f}")
    m2.metric("Close", f"{sig.close:.2f}")
    m3.metric("บวก", f"+{sig.change_pct:.1f}%")
    m4.metric("Vol Ratio", f"{sig.vol_ratio:.1f}x")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main() -> None:
    stock_list, scan_config, run_btn = render_sidebar()

    if run_btn:
        if not stock_list:
            st.warning("⚠️ กรุณาเลือกหรือใส่รายชื่อหุ้นก่อนครับ")
            st.stop()
        st.session_state["signals"] = run_scan(stock_list, scan_config)

    if "signals" in st.session_state:
        render_results(st.session_state["signals"])
    else:
        st.markdown(
            """
        <div style="text-align:center; padding: 60px; color: #4a6a9a;">
            <div style="font-size: 48px;">🟢</div>
            <div style="font-size: 18px; margin-top: 12px;">
                ตั้งค่าและกด <b style="color:#c9a84c">เริ่มสแกน</b> ได้เลยครับ
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


main()
