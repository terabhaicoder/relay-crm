"""Permission-scoped sales forecast, based on expected and actual closing dates."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.models import Deal, Stage
from app.modules.crm.repository import CRMRepository

ForecastView = Literal["open", "won", "lost", "overdue", "undated"]


class ForecastTotals(BaseModel):
    open_count: int = 0
    open_value: str = "0.00"
    weighted_value: str = "0.00"
    won_count: int = 0
    won_value: str = "0.00"
    lost_count: int = 0
    lost_value: str = "0.00"
    win_rate: str = "0.00"
    overdue_count: int = 0
    undated_count: int = 0


class ForecastMonth(BaseModel):
    month: str
    open_value: str
    weighted_value: str
    won_value: str
    lost_value: str


class ForecastDeal(BaseModel):
    id: str
    name: str
    amount: str
    probability: int
    weighted_value: str
    status: str
    stage: str
    close_date: str | None
    lost_reason: str


class ForecastReport(BaseModel):
    date_from: date
    date_to: date
    today: date
    summary: ForecastTotals
    months: list[ForecastMonth]
    items: list[ForecastDeal]
    total: int
    limit: int
    offset: int


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def sales_forecast(
    db: Session,
    user: User,
    date_from: date,
    date_to: date,
    view: ForecastView,
    pipeline_id: str | None,
    owner_id: str | None,
    limit: int,
    offset: int,
) -> ForecastReport:
    if date_to < date_from or (date_to - date_from).days > 366:
        raise HTTPException(422, "Choose an ordered date range of at most one year.")
    repo = CRMRepository(db, user)
    if pipeline_id:
        repo.get("pipelines", pipeline_id)
    scope = repo.scope(Deal)
    if pipeline_id:
        scope.append(Deal.pipeline_id == pipeline_id)
    if owner_id:
        scope.append(Deal.owner_id == owner_id)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    # Date-only expected closes retain their business date; actual closes are UTC.
    expected = func.substr(Deal.expected_close_date, 1, 10)
    actual = func.date(Deal.closed_at, "+330 minutes")
    period_open = and_(Deal.status == "open", expected.between(str(date_from), str(date_to)))
    period_closed = and_(
        Deal.status.in_(["won", "lost"]), actual.between(str(date_from), str(date_to))
    )
    overdue = and_(Deal.status == "open", expected < str(today))
    undated = and_(Deal.status == "open", Deal.expected_close_date.is_(None))
    totals = {key: Decimal("0") for key in ("open", "weighted", "won", "lost")}
    counts = {key: 0 for key in ("open", "won", "lost")}
    months: dict[str, dict[str, Decimal]] = {}
    cursor = date_from.replace(day=1)
    while cursor <= date_to:
        months[cursor.isoformat()[:7]] = dict.fromkeys(totals, Decimal("0"))
        if (cursor.year, cursor.month) == (date_to.year, date_to.month):
            break
        cursor = date(cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1)
    close_day = case((Deal.status == "open", expected), else_=actual)
    rows = db.execute(
        select(Deal.status, Deal.amount, Deal.probability, close_day)
        .where(*scope, or_(period_open, period_closed))
        .execution_options(yield_per=500)
    )
    for status, value, probability, day in rows:
        counts[status] += 1
        totals[status] += value
        bucket = months[day[:7]]
        bucket[status] += value
        if status == "open":
            weighted = value * Decimal(probability) / Decimal(100)
            totals["weighted"] += weighted
            bucket["weighted"] += weighted
    summary = ForecastTotals(
        open_count=counts["open"],
        open_value=money(totals["open"]),
        weighted_value=money(totals["weighted"]),
        won_count=counts["won"],
        won_value=money(totals["won"]),
        lost_count=counts["lost"],
        lost_value=money(totals["lost"]),
        win_rate=money(Decimal(counts["won"] * 100) / Decimal(counts["won"] + counts["lost"]))
        if counts["won"] + counts["lost"]
        else "0.00",
        overdue_count=db.scalar(select(func.count()).select_from(Deal).where(*scope, overdue)) or 0,
        undated_count=db.scalar(select(func.count()).select_from(Deal).where(*scope, undated)) or 0,
    )
    filters: dict[str, Any] = {
        "open": period_open,
        "won": and_(period_closed, Deal.status == "won"),
        "lost": and_(period_closed, Deal.status == "lost"),
        "overdue": overdue,
        "undated": undated,
    }
    query = select(Deal).where(*scope, filters[view])
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page_rows = db.execute(
        select(Deal, Stage.name, close_day)
        .join(Stage, and_(Stage.id == Deal.stage_id, Stage.org_id == user.org_id))
        .where(*scope, filters[view])
        .order_by(close_day.asc().nulls_last(), Deal.id)
        .offset(offset)
        .limit(limit)
    )
    return ForecastReport(
        date_from=date_from,
        date_to=date_to,
        today=today,
        summary=summary,
        months=[
            ForecastMonth(
                month=month,
                open_value=money(values["open"]),
                weighted_value=money(values["weighted"]),
                won_value=money(values["won"]),
                lost_value=money(values["lost"]),
            )
            for month, values in months.items()
        ],
        items=[
            ForecastDeal(
                id=deal.id,
                name=deal.name,
                amount=money(deal.amount),
                probability=deal.probability,
                weighted_value=money(deal.amount * Decimal(deal.probability) / Decimal(100)),
                status=deal.status,
                stage=stage_name,
                close_date=day,
                lost_reason=deal.lost_reason,
            )
            for deal, stage_name, day in page_rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
