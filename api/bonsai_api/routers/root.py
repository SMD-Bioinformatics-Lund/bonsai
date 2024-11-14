"""API root message."""

from fastapi import APIRouter

from ..__version__ import VERSION as version

router = APIRouter()


@router.get("/")
async def read_root():
    """Return root message."""
    return {
        "message": "Welcome to the Bonsai API",
        "version": version,
    }
