"""
main.py
-------
FastAPI: vừa cung cấp API phân tích, vừa serve dashboard frontend.
Chạy:  uvicorn main:app --reload   (rồi mở http://localhost:8000)

Endpoints:
  GET  /               - serve frontend SPA
  GET  /api/health     - kiểm tra nguồn dữ liệu
  GET  /api/symbols    - gợi ý mã phổ biến
  POST /api/analyze    - phân tích đồng bộ (backward compat)
  GET  /api/analyze-stream - phân tích realtime qua SSE
  GET  /api/model-info     - thông tin giáo dục về các mô hình
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from providers import get_provider
from service import AnalysisService
from financial_regression import MODEL_INFO

app = FastAPI(title="VN Stock ML Lab", version="2.0")
service = AnalysisService()

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

SUGGESTED = ["HPG", "FPT", "VNM", "VCB", "MWG", "HSG", "SSI", "VHM", "MSN", "ACB"]


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["HPG"])
    start: str = "2020-01-01"
    end: str = "2026-05-31"
    horizon: int = Field(5, ge=1, le=20)
    mode: str = Field("return", pattern="^(return|volatility)$")


@app.get("/api/health")
def health():
    prov = get_provider(prefer_real=True).name
    return {"status": "ok", "data_source": prov,
            "note": "synthetic = chưa cài vnstock hoặc không có mạng tới sàn"}


@app.get("/api/symbols")
def symbols():
    return {"suggested": SUGGESTED}


@app.get("/api/model-info")
def model_info():
    """Trả thông tin giáo dục về các mô hình ML — dùng cho accordion UI."""
    return MODEL_INFO


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """Phân tích đồng bộ (giữ lại để backward-compat)."""
    if not req.symbol.strip():
        raise HTTPException(400, "Thiếu mã chứng khoán.")
    try:
        return service.analyze(req.symbol.strip(), req.start, req.end, req.horizon, req.mode)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Lỗi phân tích: {e}")


@app.get("/api/analyze-stream")
async def analyze_stream(
    symbol: str = Query(..., description="Mã chứng khoán"),
    start: str = Query("2020-01-01"),
    end: str = Query("2026-05-31"),
    horizon: int = Query(5, ge=1, le=20),
    mode: str = Query("return", pattern="^(return|volatility)$"),
):
    """Phân tích realtime — trả SSE stream với events theo từng giai đoạn ML."""
    if not symbol.strip():
        raise HTTPException(400, "Thiếu mã chứng khoán.")

    async def event_generator():
        loop = asyncio.get_event_loop()
        sync_gen = service.analyze_stream(symbol.strip(), start, end, horizon, mode)
        # Dùng sentinel thay vì try/except StopIteration:
        # Python 3.7+ (PEP 479) biến StopIteration trong coroutine thành RuntimeError,
        # nên không thể catch được sau run_in_executor. next(gen, default) an toàn hơn.
        _DONE = object()

        while True:
            event = await loop.run_in_executor(None, lambda: next(sync_gen, _DONE))
            if event is _DONE:
                break
            yield json.dumps(event, ensure_ascii=False)

    return EventSourceResponse(event_generator())


@app.get("/")
def index():
    return FileResponse(str(FRONTEND))
