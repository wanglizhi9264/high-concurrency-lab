"""Readonly immutable009observations, heavy work stays in explicit CLI processes."""

import asyncio

from fastapi import APIRouter, HTTPException

from concurrency_lab.schemas.scale_experiments import ScaleRun, ScaleSummary
from concurrency_lab.services import scale_results

router = APIRouter(prefix="/api/v1/scale-experiments", tags=["recorded009experiments"])


@router.get("", response_model=list[ScaleSummary])
async def catalogue() -> list[ScaleSummary]:
    try:
        return await asyncio.to_thread(scale_results.summaries)
    except ValueError as error:
        raise HTTPException(503, "Trusted009evidence invalid") from error


@router.get("/{identifier}", response_model=ScaleRun)
async def get_record(identifier: str) -> ScaleRun:
    if identifier not in await asyncio.to_thread(scale_results.run_ids):
        raise HTTPException(404, "Unknown009record")
    try:
        return await asyncio.to_thread(scale_results.load_run, identifier)
    except ValueError as error:
        raise HTTPException(503, "Trusted009evidence invalid") from error
