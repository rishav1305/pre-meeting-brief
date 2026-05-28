"""FastAPI entry point for Vercel Python serverless.

Mounts all routers under /api/*. The whole ASGI app is exported as `app`;
Vercel's Python runtime calls it for every /api/* request.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health

app = FastAPI(title="Pre-Meeting Brief API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
