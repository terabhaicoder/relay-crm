-- Typed extension fields; archived definitions retain their values and audit.
CREATE TABLE custom_field_definitions (
 id VARCHAR(36) PRIMARY KEY, org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 entity VARCHAR(30) NOT NULL CHECK(entity IN ('leads','contacts','parties','deals','tickets')),
 field_key VARCHAR(40) NOT NULL, label VARCHAR(100) NOT NULL,
 field_type VARCHAR(20) NOT NULL CHECK(field_type IN ('text','number','date','boolean','select')),
 description VARCHAR(300) NOT NULL DEFAULT '', options JSON NOT NULL,
 version INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
 created_by VARCHAR(36) NOT NULL REFERENCES users(id), updated_by VARCHAR(36) NOT NULL REFERENCES users(id),
 deleted_at TIMESTAMP, UNIQUE(org_id, entity, field_key)
);
CREATE INDEX ix_custom_field_definitions_org_id ON custom_field_definitions(org_id);
CREATE TABLE custom_record_fields (
 id VARCHAR(36) PRIMARY KEY, org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 entity VARCHAR(30) NOT NULL, record_id VARCHAR(36) NOT NULL, "values" JSON NOT NULL,
 version INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
 created_by VARCHAR(36) NOT NULL REFERENCES users(id), updated_by VARCHAR(36) NOT NULL REFERENCES users(id),
 UNIQUE(org_id, entity, record_id)
);
CREATE INDEX ix_custom_record_fields_org_id ON custom_record_fields(org_id);
CREATE INDEX ix_custom_record_fields_record_id ON custom_record_fields(record_id);
CREATE TABLE custom_field_audit (
 id VARCHAR(36) PRIMARY KEY, org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 entity VARCHAR(30) NOT NULL, record_id VARCHAR(36),
 field_id VARCHAR(36) REFERENCES custom_field_definitions(id),
 actor_id VARCHAR(36) NOT NULL REFERENCES users(id), action VARCHAR(30) NOT NULL,
 details JSON NOT NULL, created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_custom_field_audit_org_id ON custom_field_audit(org_id);
CREATE INDEX ix_custom_field_audit_record_id ON custom_field_audit(record_id);
