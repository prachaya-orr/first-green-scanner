#!/usr/bin/env bash
#
# run.sh — รัน First Green Scanner ด้วย uv (modern Python package manager)
#
# วิธีใช้:
#   ./run.sh          # ติดตั้ง deps (ถ้าจำเป็น) แล้วรันแอป
#   ./run.sh --setup  # ติดตั้ง deps อย่างเดียว ไม่รันแอป
#
# ต้องมี uv ก่อน: https://docs.astral.sh/uv/getting-started/installation/
#   (macOS)  brew install uv
#
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ ไม่พบ uv — ติดตั้งก่อนด้วย: brew install uv"
    echo "   หรือดู https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# uv sync = เทียบเท่า npm install (สร้าง .venv + ติดตั้งจาก uv.lock)
echo "==> ติดตั้ง/ซิงก์ dependencies ด้วย uv"
uv sync

if [ "${1:-}" == "--setup" ]; then
    echo "==> ติดตั้งเสร็จแล้ว (โหมด --setup ไม่รันแอป)"
    exit 0
fi

echo "==> เริ่มรันแอป (http://localhost:8501)"
exec uv run task dev
