from fastapi import HTTPException
from sqlalchemy import Select, select

from app.modules.crm.repository import CRMRepository
from app.modules.customization.models import FieldDefinition, RecordFields


class CustomizationRepository(CRMRepository):
    def definitions(
        self, entity: str, include_archived: bool = False
    ) -> Select[tuple[FieldDefinition]]:
        return select(FieldDefinition).where(
            *self.scope(FieldDefinition, include_deleted=include_archived),
            FieldDefinition.entity == entity,
        )

    def definition(self, field_id: str) -> FieldDefinition:
        row = self.db.scalar(
            select(FieldDefinition).where(
                *self.scope(FieldDefinition, include_deleted=True), FieldDefinition.id == field_id
            )
        )
        if row is None:
            raise HTTPException(404, "Custom field not found.")
        return row

    def record_values(self, entity: str, record_id: str) -> RecordFields | None:
        self.get(entity, record_id)
        return self.db.scalar(
            select(RecordFields).where(
                *self.scope(RecordFields),
                RecordFields.entity == entity,
                RecordFields.record_id == record_id,
            )
        )
