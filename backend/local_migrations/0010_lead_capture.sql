-- Local public lead capture and durable, idempotent submission receipts.
CREATE TABLE capture_forms (
 id VARCHAR(36) PRIMARY KEY,
 org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 name VARCHAR(100) NOT NULL,
 title VARCHAR(160) NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 source VARCHAR(100) NOT NULL DEFAULT 'Website',
 enabled BOOLEAN NOT NULL DEFAULT 1,
 owner_ids JSON NOT NULL,
 cursor INTEGER NOT NULL DEFAULT 0,
 version INTEGER NOT NULL DEFAULT 1,
 created_by VARCHAR(36) NOT NULL REFERENCES users(id),
 updated_by VARCHAR(36) NOT NULL REFERENCES users(id),
 created_at TIMESTAMP NOT NULL,
 updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_capture_forms_org_id ON capture_forms(org_id);
CREATE TABLE capture_submissions (
 id VARCHAR(36) PRIMARY KEY,
 org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 form_id VARCHAR(36) NOT NULL REFERENCES capture_forms(id),
 lead_id VARCHAR(36) NOT NULL REFERENCES leads(id),
 request_key VARCHAR(200) NOT NULL,
 payload_hash VARCHAR(64) NOT NULL,
 name VARCHAR(255) NOT NULL,
 message TEXT NOT NULL DEFAULT '',
 duplicate BOOLEAN NOT NULL DEFAULT 0,
 created_at TIMESTAMP NOT NULL,
 UNIQUE(org_id, form_id, request_key)
);
CREATE INDEX ix_capture_submissions_org_id ON capture_submissions(org_id);
CREATE INDEX ix_capture_submissions_form_id ON capture_submissions(form_id);
