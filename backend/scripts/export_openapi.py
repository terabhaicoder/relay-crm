import json
from pathlib import Path

from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.modules.crm.schemas import SCHEMAS

# Schema generation performs no database or network calls and contains no credentials.
settings = Settings(
    environment="test",
    database_url=SecretStr("postgresql+asyncpg://schema@localhost/schema"),
    redis_url=SecretStr("redis://localhost:6379/0"),
)
output = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)
schema = create_app(settings).openapi()
# Generic collection routes validate these concrete models inside the service.
# Include their actual schemas for consumers without inventing response fields.
components = schema.setdefault("components", {}).setdefault("schemas", {})
for model in SCHEMAS.values():
    model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    components.update(model_schema.pop("$defs", {}))
    components[model.__name__] = model_schema
output.write_text(json.dumps(schema, indent=2) + "\n")
print(f"Exported {output}")
