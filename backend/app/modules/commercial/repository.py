from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.modules.commercial.models import Quotation
from app.modules.crm.models import Contact, Deal, Party
from app.modules.crm.repository import CRMRepository


class QuotationRepository(CRMRepository):
    """Use the shared tenant/owner scope, including current linked-record access."""

    def quotes(self) -> Any:
        return select(Quotation).where(
            *self.scope(Quotation),
            Quotation.deal_id.in_(self.query("deals").with_only_columns(Deal.id)),
            or_(
                Quotation.party_id.is_(None),
                Quotation.party_id.in_(self.query("parties").with_only_columns(Party.id)),
            ),
            or_(
                Quotation.contact_id.is_(None),
                Quotation.contact_id.in_(self.query("contacts").with_only_columns(Contact.id)),
            ),
        )

    def quote(self, record_id: str) -> Quotation:
        row: Quotation | None = self.db.scalar(self.quotes().where(Quotation.id == record_id))
        if row is None:
            raise HTTPException(404, "Quotation not found.")
        return row
