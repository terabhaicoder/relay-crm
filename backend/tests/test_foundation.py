import json
import logging
from decimal import Decimal

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.orm import Mapped

from app.core.config import Settings
from app.core.db import Base, Money, Quantity, Rate
from app.core.logging import SafeJSONFormatter


def test_settings_reject_non_postgres_and_wildcard_cors(settings: Settings) -> None:
    values = settings.model_dump()
    with pytest.raises(ValidationError):
        Settings(**{**values, "database_url": SecretStr("mysql:///test.db")})
    with pytest.raises(ValidationError):
        Settings(**{**values, "cors_origins": ["*"]})


def test_settings_repr_masks_connection_secrets(settings: Settings) -> None:
    assert "test:test" not in repr(settings)


def test_logging_omits_arbitrary_messages_and_sensitive_extras() -> None:
    record = logging.LogRecord("test", logging.ERROR, __file__, 1, "PAN SECRET123", (), None)
    record.password = "password-secret"
    record.salary = "100000"
    record.safe_event = "request_failed"
    output = SafeJSONFormatter().format(record)
    assert json.loads(output)["event"] == "request_failed"
    assert "SECRET123" not in output
    assert "password-secret" not in output
    assert "100000" not in output


def test_decimal_column_contract() -> None:
    class SampleBase(Base):
        __abstract__ = True

    class DecimalContract(SampleBase):
        __tablename__ = "test_decimal_contract"
        from sqlalchemy.orm import mapped_column

        id: Mapped[int] = mapped_column(primary_key=True)
        money: Mapped[Money]
        quantity: Mapped[Quantity]
        rate: Mapped[Rate]

    try:
        for name, scale in [("money", 2), ("quantity", 3), ("rate", 4)]:
            column_type = DecimalContract.__table__.c[name].type
            assert column_type.precision == 18
            assert column_type.scale == scale
            assert column_type.asdecimal
            assert column_type.python_type is Decimal
    finally:
        Base.metadata.remove(DecimalContract.__table__)
