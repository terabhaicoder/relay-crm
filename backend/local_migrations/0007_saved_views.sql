-- Private CRM list preferences; permission to save does not grant record access.
CREATE TABLE saved_views (
 id VARCHAR(36) PRIMARY KEY,
 org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 user_id VARCHAR(36) NOT NULL REFERENCES users(id),
 entity VARCHAR(30) NOT NULL,
 name VARCHAR(80) NOT NULL,
 filters JSON NOT NULL,
 version INTEGER NOT NULL DEFAULT 1,
 created_at TIMESTAMP NOT NULL,
 updated_at TIMESTAMP NOT NULL,
 created_by VARCHAR(36) NOT NULL REFERENCES users(id),
 updated_by VARCHAR(36) NOT NULL REFERENCES users(id),
 UNIQUE(org_id, user_id, entity, name)
);
CREATE INDEX ix_saved_views_org_id ON saved_views(org_id);
CREATE INDEX ix_saved_views_user_id ON saved_views(user_id);
