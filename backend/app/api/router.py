"""Primary API router setup."""

from fastapi import APIRouter

from .v1 import pipeline as pipeline_router

api_router = APIRouter()
api_router.include_router(
    pipeline_router.router,
    prefix="/v1/pipeline",
    tags=["pipeline"],
)
