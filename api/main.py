"""
api/main.py
FastAPI application entry point.

Run locally:
    uvicorn api.main:app --reload

Serves:
  GET  /onboarding          — clinic signup form
  POST /clinic/register     — create clinic, return embed code
  POST /api/chat            — widget chat endpoint
  GET  /widget.js           — serve the embeddable JS widget
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.routes.chat import router as chat_router
from api.routes.onboarding import router as onboarding_router
from api.routes.portal import router as portal_router

app = FastAPI(title="Dental Clinic Chatbot Platform", docs_url="/docs")

# ---------------------------------------------------------------------------
# CORS
# We keep CORS open (*) so the widget can be embedded on any domain.
# Per-clinic domain enforcement happens inside /api/chat via the Origin check
# in core/security.py — that's the actual security layer.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handler — ensures CORS headers are present even on 500s
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
        headers={"Access-Control-Allow-Origin": "*"},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(chat_router)
app.include_router(onboarding_router)
app.include_router(portal_router)


# ---------------------------------------------------------------------------
# Widget static file
# ---------------------------------------------------------------------------
_WIDGET_PATH = Path(__file__).parent.parent / "widget" / "widget.js"

@app.get("/widget.js")
async def serve_widget():
    return FileResponse(
        _WIDGET_PATH,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}
