from fastapi import APIRouter

# Re-export for package clarity; routes live in routes.py
from app.api.routes import router  # noqa: F401

__all__ = ["router"]
