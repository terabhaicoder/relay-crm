-- Immutable SQLite migration: 0004_attachments. Add a new migration for future schema changes.

CREATE TABLE IF NOT EXISTS attachments (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	entity_type VARCHAR(40) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	filename VARCHAR(200) NOT NULL, 
	storage_key VARCHAR(64) NOT NULL, 
	content_type VARCHAR(100) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT pk_attachments PRIMARY KEY (id), 
	CONSTRAINT fk_attachments_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_attachments_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), 
	CONSTRAINT uq_attachments_storage_key UNIQUE (storage_key)
);

CREATE INDEX IF NOT EXISTS ix_attachments_org_entity ON attachments (org_id, entity_type, entity_id);

CREATE INDEX IF NOT EXISTS ix_attachments_org_id ON attachments (org_id);
