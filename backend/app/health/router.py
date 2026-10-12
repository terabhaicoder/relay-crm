from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.errors import ErrorResponse, error_response
from app.health.service import DependencyProbe

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def get_probe(request: Request) -> DependencyProbe:
    return cast(DependencyProbe, request.app.state.probe)


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
async def ready(
    probe: Annotated[DependencyProbe, Depends(get_probe)],
) -> HealthResponse | JSONResponse:
    checks = await probe.check()
    if not checks or not all(checks.values()):
        return error_response(
            503, "DEPENDENCY_UNAVAILABLE", "Service is not ready. Please try again."
        )
    return HealthResponse()
