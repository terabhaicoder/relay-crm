CREATE TABLE campaign_members (
 id VARCHAR(36) PRIMARY KEY,
 org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id),
 entity_type VARCHAR(30) NOT NULL CHECK (entity_type IN ('leads','contacts')),
 entity_id VARCHAR(36) NOT NULL,
 created_by VARCHAR(36) NOT NULL REFERENCES users(id),
 created_at TIMESTAMP NOT NULL,
 UNIQUE (org_id, campaign_id, entity_type, entity_id)
);
CREATE INDEX ix_campaign_members_org_id ON campaign_members(org_id);
CREATE INDEX ix_campaign_members_campaign_id ON campaign_members(campaign_id);
