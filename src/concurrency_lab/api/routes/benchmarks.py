"""Read-only published load evidence and actual bounded business monitoring."""

from fastapi import APIRouter, HTTPException, Request

from concurrency_lab.schemas.benchmarks import BenchmarkSummary, BusinessMetrics, RecordedLoadRun
from concurrency_lab.services import benchmarks
from concurrency_lab.services.load_monitor import collect_business_metrics

router = APIRouter(prefix="/api/v1", tags=["benchmarks"])


@router.get("/benchmarks", response_model=list[BenchmarkSummary])
async def list_benchmarks() -> list[BenchmarkSummary]:
    try:
        summaries = []
        for run_id in benchmarks.benchmark_ids():
            run = benchmarks.load_benchmark(run_id)
            summaries.append(BenchmarkSummary(manifest=run.manifest, summary=run.summary))
        return summaries
    except ValueError as error:
        raise HTTPException(503, "Trusted load evidence invalid") from error


@router.get("/benchmarks/{run_id}", response_model=RecordedLoadRun)
async def get_benchmark(run_id: str) -> RecordedLoadRun:
    if run_id not in benchmarks.benchmark_ids():
        raise HTTPException(404, "Unknown recorded load run")
    try:
        return benchmarks.load_benchmark(run_id)
    except ValueError as error:
        raise HTTPException(503, "Trusted load evidence invalid") from error


@router.get("/observability/business-metrics", response_model=BusinessMetrics)
async def business_metrics(request: Request) -> BusinessMetrics:
    resources = request.app.state.resources
    return await collect_business_metrics(resources.business, resources.settings)
