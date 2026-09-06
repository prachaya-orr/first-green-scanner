"""Chart rendering — Plotly candlestick + volume.

แยกการเตรียมข้อมูลกราฟ (load_chart) และการวาด (build_candlestick)
ออกจาก UI เพื่อให้ทดสอบและ reuse ได้
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go

from . import config
from .data import fetch_history

logger = logging.getLogger(__name__)

# สีธีม Navy/Gold
_UP_COLOR = "#27ae60"
_DOWN_COLOR = "#e74c3c"
_GOLD = "#c9a84c"
_GRID = "#1e3a6e"
_BG = "#0a1628"
_PLOT_BG = "#0d1f3c"
_TEXT = "#aac4e8"


def load_chart_data(symbol: str, signal_date: str, lookback_days: int) -> pd.DataFrame:
    """slice ข้อมูลรอบวันสัญญาณจาก cache เดิม (ไม่ยิงเน็ตซ้ำ)."""
    df_full = fetch_history(symbol, lookback_days + config.FETCH_BUFFER_DAYS)
    if df_full.empty:
        return pd.DataFrame()

    sig_dt = pd.Timestamp(signal_date)
    start = sig_dt - timedelta(days=config.CHART_DAYS_BEFORE)
    end = sig_dt + timedelta(days=config.CHART_DAYS_AFTER)
    return df_full.loc[(df_full.index >= start) & (df_full.index <= end)].copy()


def build_candlestick(
    df: pd.DataFrame,
    symbol: str,
    signal_date: str,
    vol_ma_period: int = config.VOLUME_MA_PERIOD,
) -> go.Figure | None:
    """วาดกราฟ Candlestick + Volume + marker วันสัญญาณ."""
    if df.empty:
        return None

    df = df.copy()
    # ตรงกับ logic ตอนสแกน: ไม่รวมวันปัจจุบันในค่าเฉลี่ย
    df["Vol_MA"] = df["Volume"].shift(1).rolling(vol_ma_period).mean()
    sig_dt = pd.Timestamp(signal_date)

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="ราคา",
            increasing_line_color=_UP_COLOR,
            decreasing_line_color=_DOWN_COLOR,
            increasing_fillcolor=_UP_COLOR,
            decreasing_fillcolor=_DOWN_COLOR,
        )
    )

    if sig_dt in df.index:
        sig_row = df.loc[sig_dt]
        fig.add_trace(
            go.Scatter(
                x=[sig_dt],
                y=[float(sig_row["High"]) * 1.03],
                mode="markers+text",
                marker=dict(symbol="triangle-down", size=14, color=_GOLD),
                text=["🟢 สัญญาณ"],
                textposition="top center",
                textfont=dict(color=_GOLD, size=12),
                name="วันสัญญาณ",
            )
        )

    vol_colors = [
        _UP_COLOR if c >= o else _DOWN_COLOR for c, o in zip(df["Close"], df["Open"], strict=False)
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color=vol_colors,
            opacity=0.5,
            yaxis="y2",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Vol_MA"],
            name=f"Vol MA{vol_ma_period}",
            line=dict(color=_GOLD, width=1.5, dash="dot"),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title=dict(text=f"📈 {symbol} — {signal_date}", font=dict(color=_GOLD, size=16)),
        paper_bgcolor=_BG,
        plot_bgcolor=_PLOT_BG,
        font=dict(color=_TEXT, family="Kanit"),
        xaxis=dict(gridcolor=_GRID, showgrid=True, rangeslider_visible=False),
        yaxis=dict(gridcolor=_GRID, showgrid=True),
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            title="Volume",
            title_font=dict(color="#7a9cc4"),
        ),
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(bgcolor=_PLOT_BG, bordercolor=_GRID),
    )

    return fig
