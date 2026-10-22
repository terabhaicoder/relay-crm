from datetime import date

from fastapi import APIRouter, Query

from app.core.auth import CurrentUser, SessionDep
from app.modules.crm.reporting import ForecastReport, ForecastView, sales_forecast

router = APIRouter(tags=["Sales reporting"])


@router.get("/reports/sales", response_model=ForecastReport)
def report(
    db: SessionDep,
    user: CurrentUser,
    date_from: date,
    date_to: date,
    view: ForecastView = "open",
    pipeline_id: str | None = None,
    owner_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ForecastReport:
    return sales_forecast(db, user, date_from, date_to, view, pipeline_id, owner_id, limit, offset)
