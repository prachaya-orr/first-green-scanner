# syntax=docker/dockerfile:1

# ── Stage 1: builder — ติดตั้ง dependencies ด้วย uv จาก lockfile ──────────────
FROM python:3.12-slim AS builder

# ดึง uv binary จาก official image (เวอร์ชัน pin เพื่อ reproducible build)
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# ติดตั้ง dependencies ก่อน (layer นี้ถูก cache ตราบใดที่ lockfile ไม่เปลี่ยน)
# --no-install-project = ยังไม่ติดตั้งตัวโปรเจกต์เอง เอาแค่ deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# คัดลอกซอร์สโค้ดแล้วติดตั้งตัวโปรเจกต์ (editable package)
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ── Stage 2: runtime — image เล็ก ไม่มี uv/build tools ───────────────────────
FROM python:3.12-slim AS runtime

# รันด้วย non-root user เพื่อความปลอดภัย
RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

# คัดลอก virtualenv + ซอร์สจาก builder
COPY --from=builder --chown=app:app /app /app

# ใช้ venv ที่ uv สร้างไว้เป็น default PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

USER app

EXPOSE 8501

# health check ผ่าน endpoint ในตัวของ Streamlit
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').status==200 else 1)"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
