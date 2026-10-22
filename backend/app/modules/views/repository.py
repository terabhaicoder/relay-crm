from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.views.models import SavedView


class ViewRepository:
    """Both tenant and individual owner scope apply to every preference operation."""

    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user

    def query(self) -> Select[tuple[SavedView]]:
        return select(SavedView).where(
            SavedView.org_id == self.user.org_id, SavedView.user_id == self.user.id
        )

    def get(self, record_id: str) -> SavedView:
        row = self.db.scalar(self.query().where(SavedView.id == record_id))
        if row is None:
            raise HTTPException(404, "Saved view not found.")
        return row
