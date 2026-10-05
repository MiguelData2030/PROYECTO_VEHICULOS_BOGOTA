"""Vercel serverless entry point for the FastAPI backend."""
import os
import sys

# Make the project root importable (backend/ lives next to api/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app  # noqa: E402,F401
