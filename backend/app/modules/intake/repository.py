from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.intake.models import CaptureForm, CaptureSubmission


class IntakeRepository:
    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user

    def forms(self) -> Select[tuple[CaptureForm]]:
        return select(CaptureForm).where(CaptureForm.org_id == self.user.org_id)

    def get(self, record_id: str) -> CaptureForm:
        row = self.db.scalar(self.forms().where(CaptureForm.id == record_id))
        if row is None:
            raise HTTPException(404, "Lead form not found.")
        return row

    def submissions(self, form_id: str) -> Select[tuple[CaptureSubmission]]:
        return select(CaptureSubmission).where(
            CaptureSubmission.org_id == self.user.org_id,
            CaptureSubmission.form_id == form_id,
        )
