"""FastAPI entry point for Vercel Python serverless.

Mounts all routers under /api/*. Same routes are also registered under
/pre-meeting-brief/api/* because Vercel rewrites do not transform the
path the function receives — the function sees the original request URL.
This lets the API answer both:
  - direct calls to pre-meeting-brief.vercel.app/api/*
  - calls via the basePath at rishavchatterjee.com/pre-meeting-brief/api/*

The whole ASGI app is exported as `app`; Vercel's Python runtime calls it
for every /api/* request (per the catch-all rewrite in vercel.json).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agenda, briefs, health

app = FastAPI(title="Pre-Meeting Brief API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Register all routers under both prefixes so both direct and basePath
# access work. Add new routers here in Phase 2+.
for _prefix in ("/api", "/pre-meeting-brief/api"):
    app.include_router(health.router, prefix=_prefix)
    app.include_router(agenda.router, prefix=_prefix)
    app.include_router(briefs.router, prefix=_prefix)
