"""Vercel FastAPI entrypoint.

Exports the FastAPI `app` so Vercel can auto-detect the ASGI application.
"""

from main import app
