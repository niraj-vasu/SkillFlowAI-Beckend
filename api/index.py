"""Vercel serverless entrypoint.

Vercel's @vercel/python runtime serves the ASGI `app` exposed here. All routes
(/health, /api/*, /docs, /verify) are handled by FastAPI itself — see vercel.json,
which rewrites every path to this function.
"""
import os
import sys

# Make the project root importable so `app` package resolves on Vercel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401
