# 🟢 First Green Scanner

สแกนหา **"เขียวแท่งแรก" (First Green Candle)** ที่บวกแรงพร้อม **Volume ผิดปกติ** หลังจากช่วงราคานิ่งมาก่อน — เครื่องมือช่วยหาหุ้นที่อาจกำลังเริ่มเคลื่อนไหว รองรับตลาดไทย (SET), ฮ่องกง (HK) และสหรัฐฯ (US)

> เว็บแอปบน Streamlit ดึงราคาหุ้นรายวันจาก Yahoo Finance มาคำนวณสัญญาณ แล้วแสดงผลเป็นตาราง + กราฟ Candlestick โครงสร้างโค้ดแยกเป็น package ตามหน้าที่ จัดการ dependency ด้วย [uv](https://docs.astral.sh/uv/)

---

## 📌 แอปนี้ทำอะไร

สแกนรายชื่อหุ้นเพื่อหาแท่งเทียนที่ผ่านเงื่อนไขทั้งหมดต่อไปนี้พร้อมกัน:

| เงื่อนไข | ความหมาย | ค่าเริ่มต้น |
|----------|----------|-------------|
| แท่งเขียว | `Close > Open` | — |
| บวกแรง | `(Close − Open) / Open ≥ threshold` | ≥ 10% |
| Volume พุ่ง | `Volume / Vol_MA20 ≥ ตัวคูณ` | ≥ 3 เท่า |
| ผ่านช่วงเงียบ | ก่อนหน้านี้ราคานิ่ง (แท่งเขียวแรงสุดไม่เกิน threshold) | 30 วัน / ≤ 7% |

จากนั้นแสดงผลเป็นตารางเรียงตาม **Trading Value** (มูลค่าเทรด) จากมากไปน้อย พร้อมทำเครื่องหมายเตือนหุ้นสภาพคล่องต่ำ และให้เลือกดูกราฟ Candlestick + Volume รายตัวได้

### ฟีเจอร์หลัก
- 📋 เลือกรายชื่อหุ้นสำเร็จรูป (SET / SET100 / S&P500 / US Stock) หรือพิมพ์เอง / อัปโหลด CSV
- ⬇️ ดาวน์โหลด CSV template แล้วแก้/อัปโหลดกลับได้
- ⚙️ ปรับ threshold ทุกตัวได้จาก sidebar (บวก %, Volume, ช่วงเงียบ, จำนวนแท่งย้อนหลัง)
- 🚦 ทำเครื่องหมายเตือนหุ้นที่ Trading Value ต่ำกว่าเกณฑ์สภาพคล่องของแต่ละตลาด (ไม่ตัดออก แค่เตือน)
- 📈 กราฟ Candlestick + Volume + marker วันสัญญาณ
- ⚡ ดึงข้อมูลแบบขนาน (parallel) + cache เพื่อความเร็วและรองรับการสแกนหุ้นจำนวนมาก

---

## 🏗️ Software Architecture

โค้ดแยกเป็น **package `scanner`** ตามหน้าที่ชัดเจน โดย `app.py` ทำหน้าที่เป็น **UI layer บาง ๆ** เท่านั้น — logic การดึงข้อมูล คำนวณสัญญาณ และวาดกราฟ แยกออกเป็นโมดูลที่ทดสอบและ reuse ได้ (ไม่ผูกกับ Streamlit)

Streamlit จะ re-run สคริปต์ทั้งไฟล์ทุกครั้งที่ผู้ใช้มี interaction โดยมี `st.cache_data` และ `st.session_state` ช่วยไม่ให้ทำงานหนักซ้ำ

### ภาพรวม data flow

```
┌─────────────────────────────────────────────────────────────┐
│                    app.py — Streamlit UI layer               │
│  render_sidebar → run_scan → render_results                  │
└───────────────┬─────────────────────────────────────────────┘
                │ กดปุ่ม "เริ่มสแกน"
                ▼
┌─────────────────────────────────────────────────────────────┐
│  ThreadPoolExecutor (I/O-bound, config.MAX_WORKERS)          │
│  ดึง + สแกนหลายหุ้นพร้อมกัน                                    │
└───────────────┬─────────────────────────────────────────────┘
                │ ต่อหุ้น 1 ตัว
                ▼
┌──────────────────────────┐     ┌──────────────────────────────┐
│  data.fetch_history()    │────▶│  Yahoo Finance (yfinance)     │
│  @st.cache_data ttl=1hr  │◀────│  ราคา OHLCV รายวัน             │
└───────────┬──────────────┘     └──────────────────────────────┘
            │ DataFrame (cached)
            ▼
┌──────────────────────────┐
│  scanner.scan_one_stock()│  _add_indicators → _passes_conditions
│  + is_quiet_before()     │  → คืน list[Signal] (dataclass)
└───────────┬──────────────┘
            │ list[Signal]
            ▼
┌──────────────────────────┐
│  st.session_state         │  เก็บผลลัพธ์ข้ามการ re-run
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐     ┌──────────────────────────────┐
│  ตาราง + Metric cards     │     │  charts.build_candlestick()   │
│  (pandas Styler)          │     │  + charts.load_chart_data()   │
│                          │     │  ใช้ข้อมูล cache เดิม ไม่ยิงซ้ำ   │
└──────────────────────────┘     └──────────────────────────────┘
```

### โครงสร้าง package

```
first-green-scanner/
├── app.py                  # UI layer (Streamlit เท่านั้น)
├── src/scanner/
│   ├── __init__.py         # public API ของ package
│   ├── config.py           # ค่าคงที่ + settings (typed, ไม่มี magic number)
│   ├── models.py           # dataclass: ScanConfig / Signal / MarketInfo
│   ├── data.py             # ดึงข้อมูล + โหลด watchlist (มี logging)
│   ├── scanner.py          # logic การคำนวณสัญญาณ (pure functions)
│   └── charts.py           # วาดกราฟ Plotly
├── pyproject.toml          # metadata + deps + script runner (แบบ modern)
├── uv.lock                 # ล็อกเวอร์ชัน dependency เป๊ะ ๆ
├── requirements.txt        # generate จาก uv.lock (เผื่อ deploy)
├── run.sh                  # script รันด้วย uv
├── SET.csv / SET100.csv / SP500.csv / US_Stock.csv   # รายชื่อหุ้น preset
└── README.md
```

| โมดูล | หน้าที่ |
|-------|---------|
| `config.py` | ค่าคงที่ทั้งหมด — `MAX_WORKERS`, `CACHE_TTL_SECONDS`, `VOLUME_MA_PERIOD`, `MARKETS`, `PRESET_FILES` |
| `models.py` | `ScanConfig` (พารามิเตอร์สแกน), `Signal` (ผลลัพธ์), `MarketInfo` (ข้อมูลตลาด) — เป็น `frozen` dataclass |
| `data.py` | `fetch_history` (cached), `load_stock_list`, `parse_uploaded_csv`, `parse_manual_input`, `build_template_csv` |
| `scanner.py` | `scan_one_stock`, `is_quiet_before`, `get_market`, `strip_suffix`, `format_trading_value` |
| `charts.py` | `load_chart_data`, `build_candlestick` |

### หลักการออกแบบสำคัญ

**1. แยก UI / data / logic ออกจากกัน**
`scanner.py` และ `models.py` ไม่ import Streamlit เลย รับ DataFrame + `ScanConfig` แล้วคืน `list[Signal]` ทำให้เขียน unit test และ reuse นอก Streamlit ได้ ส่วน `app.py` เหลือแค่เรื่อง UI

**2. แยกการ "ดึงข้อมูล" ออกจากการ "คำนวณสัญญาณ"**
`data.fetch_history()` ดึงข้อมูลอย่างเดียวและถูก cache 1 ชั่วโมง (`@st.cache_data(ttl=3600)`) ส่วน `scan_one_stock()` รับ DataFrame มาคำนวณ ผลคือปรับ threshold แล้วสแกนใหม่ได้ทันทีโดยไม่ต้องโหลดข้อมูลซ้ำ และกราฟใช้ข้อมูลชุดเดียวกันได้เลย

**3. ดึงข้อมูลแบบขนาน (parallel I/O)**
งานสแกนเป็น I/O-bound (เวลาหมดไปกับการรอ network) จึงใช้ `ThreadPoolExecutor` ให้การรอของแต่ละหุ้นทับซ้อนกัน error ของหุ้นแต่ละตัวถูก isolate และ log ไว้ ไม่ให้ล้มทั้งการสแกน

**4. คำนวณ Vol_MA แบบไม่รวมวันปัจจุบัน**
ใช้ `Volume.shift(1).rolling(vm).mean()` เพื่อให้ค่าเฉลี่ย volume คิดจากวันก่อนหน้าเท่านั้น กันไม่ให้ volume spike ของวันที่เกิดสัญญาณไปดันค่าเฉลี่ยตัวเองให้สูงเทียม (หลักการเดียวกับ `volume[1]` ใน Pine Script)

**5. นับ "แท่งเทรดจริง" ไม่ใช่วันปฏิทิน**
ใช้ `df.tail(lookback_days)` เพื่อนับแท่งเทรดจริงล่าสุด กันปัญหาวันหยุด/เสาร์-อาทิตย์ทำให้ได้แท่งน้อยกว่าที่ตั้งไว้

**6. ตรวจตลาดจาก suffix ของ symbol**
`.BK` → ไทย, `.HK` → ฮ่องกง, ไม่มี suffix → สหรัฐฯ (นิยามใน `config.MARKETS`) แต่ละตลาดมีเกณฑ์สภาพคล่องและสกุลเงินต่างกัน ใช้ทำเครื่องหมายเตือนเท่านั้น ไม่ตัดหุ้นออก เพราะสกุลเงินคนละหน่วยเทียบตรง ๆ ไม่ได้

---

## 🧰 Technology Stack

| ส่วน | เทคโนโลยี | ใช้ทำอะไร |
|------|-----------|-----------|
| ภาษา | **Python** (≥ 3.10) | ภาษาหลักทั้งโปรเจกต์ |
| Package / env manager | **uv** | จัดการ dependency, venv, lockfile, script runner |
| UI / Web framework | **Streamlit** | เว็บแอป, sidebar, ตาราง, ปุ่ม, การ cache |
| แหล่งข้อมูลราคา | **yfinance** (Yahoo Finance) | ดึงราคา OHLCV รายวัน |
| ประมวลผลข้อมูล | **pandas** / **numpy** | คำนวณ rolling mean, ratio, จัดตาราง |
| กราฟ | **Plotly** (`graph_objects`) | Candlestick + Volume แบบ interactive |
| การทำงานขนาน | **concurrent.futures** (`ThreadPoolExecutor`) | ดึงข้อมูลหลายหุ้นพร้อมกัน |
| Lint + format | **ruff** | ตรวจและจัดรูปแบบโค้ดในเครื่องมือเดียว |
| Script runner | **taskipy** | คำสั่งสั้น ๆ เช่น `uv run task dev` |

---

## 🚀 การติดตั้งและรัน

โปรเจกต์นี้ใช้ [**uv**](https://docs.astral.sh/uv/) จัดการทุกอย่าง ติดตั้ง uv ก่อน (ครั้งเดียว):

```bash
# macOS
brew install uv
# หรือดู https://docs.astral.sh/uv/getting-started/installation/
```

### วิธีเร็วสุด (แนะนำ)

```bash
./run.sh
```

สคริปต์จะ `uv sync` (สร้าง `.venv` + ติดตั้ง deps จาก `uv.lock`) แล้วรันแอปให้อัตโนมัติ เปิดที่ **http://localhost:8501**

โหมดติดตั้งอย่างเดียว (ไม่รันแอป): `./run.sh --setup`

### รันเองด้วย uv

```bash
uv sync              # ติดตั้ง dependencies (เทียบเท่า npm install)
uv run task dev      # รันแอป (เทียบเท่า npm run dev)
```

### คำสั่งที่ใช้บ่อย (script runner)

| คำสั่ง | เทียบ npm | ทำอะไร |
|--------|-----------|--------|
| `uv sync` | `npm install` | ติดตั้ง/ซิงก์ dependencies จาก lockfile |
| `uv run task dev` | `npm run dev` | รันแอป |
| `uv run task start` | `npm start` | รันแบบ headless |
| `uv run task lint` | `npm run lint` | ตรวจโค้ดด้วย ruff |
| `uv run task format` | `npm run format` | จัดรูปแบบโค้ด |
| `uv run task fix` | — | แก้ปัญหา lint อัตโนมัติ |
| `uv add <pkg>` | `npm install <pkg>` | เพิ่ม dependency |

> **หมายเหตุเรื่องเวอร์ชัน Python:** uv จัดการเวอร์ชัน Python ให้เอง ถ้าต้องการล็อกเวอร์ชันเฉพาะ ใช้ `uv python pin 3.12` แล้ว `uv sync` ใหม่

---

## 📖 วิธีใช้งาน

1. เปิดแอปที่ http://localhost:8501
2. ที่ sidebar ด้านซ้าย เลือกรายชื่อหุ้น (preset / พิมพ์เอง / อัปโหลด CSV)
3. ปรับ threshold ตามต้องการ — บวก %, Volume, ช่วงเงียบ, จำนวนแท่งย้อนหลัง
4. กด **🚀 เริ่มสแกน**
5. ดูผลในตาราง (เรียงตามมูลค่าเทรด) แล้วเลือกหุ้นเพื่อดูกราฟรายตัว

### รูปแบบไฟล์ CSV (สำหรับอัปโหลดเอง)

- 1 คอลัมน์ = 1 ชื่อหุ้นต่อบรรทัด ไม่ต้องมี header
- หุ้นไทยลงท้ายด้วย `.BK` เช่น `PTT.BK`
- หุ้นฮ่องกงลงท้ายด้วย `.HK` เช่น `0700.HK`
- หุ้นสหรัฐฯ ใส่ชื่อตรง ๆ เช่น `AAPL`
- บรรทัดที่ขึ้นต้นด้วย `#` เป็นคอมเมนต์ ระบบจะข้ามให้

กดปุ่ม **⬇️ โหลด template ตัวอย่าง** ในโหมด "อัปโหลด CSV" เพื่อดาวน์โหลดไฟล์ตัวอย่างไปแก้ได้

---

## ⚠️ ข้อจำกัดและข้อควรทราบ

- ข้อมูลราคามาจาก Yahoo Finance อาจมี delay หรือขาดหายในบางหุ้น/บางตลาด
- เกณฑ์สภาพคล่อง (Trading Value) ใช้ **เตือน** เท่านั้น ไม่ได้ตัดหุ้นออกจากผล
- เครื่องมือนี้ช่วย **คัดกรองเบื้องต้น** ไม่ใช่คำแนะนำการลงทุน ควรวิเคราะห์เพิ่มก่อนตัดสินใจ
- ถ้าสแกนหุ้นจำนวนมากแล้วเจอ rate-limit จาก Yahoo (เช่น error `401 Invalid Crumb`) ลองลดค่า `MAX_WORKERS` ใน `src/scanner/config.py` (เช่นจาก 12 เหลือ 6–8)

---

## 🔭 แนวทางขยายในอนาคต (Scaling)

สำหรับระดับหลายผู้ใช้ / หุ้นจำนวนมหาศาล แนะนำแยก layer:

- แยก **nightly job** ดึงข้อมูลราคาเก็บลงฐานข้อมูล (เช่น DuckDB + Parquet หรือ Postgres) แทนดึงสดทุกครั้ง
- ให้แอปอ่านจาก DB → query เร็วขึ้นมากและลดภาระ network
- ย้าย compute หนัก ๆ ออกจาก Streamlit process (ซึ่ง re-run ทั้งสคริปต์ทุก interaction)
- เพิ่ม unit test ให้ `scanner.py` (แยกจาก UI แล้ว เขียน test ได้ตรง ๆ)
