"""API root message."""

from bonsai_api.__version__ import VERSION as version
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def read_root():
    """Return root message."""
    return {
        "message": "Welcome to the Bonsai API",
        "version": version,
    }
