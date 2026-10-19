"""Jyotish Studio — optional FastAPI server. All logic lives in app/api.py, which the
static (in-browser) build also runs, so both modes compute identical results."""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import api

STATIC = os.path.join(os.path.dirname(__file__), "static")
app = FastAPI(title="Jyotish Studio", version="2.0")


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def endpoint(path: str, request: Request):
    body = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)
    status, payload = await run_in_threadpool(api.handle, f"/api/{path}", dict(request.query_params), body)
    return JSONResponse(payload, status_code=status)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))
