-- Durable local CRM workflow steps. Existing legacy rules keep synchronous behavior.
ALTER TABLE automation_rules ADD COLUMN steps JSON NOT NULL DEFAULT '[]';
ALTER TABLE automation_runs ADD COLUMN rule_name VARCHAR(200) NOT NULL DEFAULT '';
ALTER TABLE automation_runs ADD COLUMN entity_name VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE automation_runs ADD COLUMN completed_at TIMESTAMP;
UPDATE automation_runs SET rule_name=(SELECT name FROM automation_rules WHERE automation_rules.id=automation_runs.rule_id);
CREATE TABLE automation_jobs (
 id VARCHAR(36) PRIMARY KEY,
 org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 created_at TIMESTAMP NOT NULL,
 run_id VARCHAR(36) NOT NULL REFERENCES automation_runs(id),
 rule_id VARCHAR(36) NOT NULL REFERENCES automation_rules(id),
 actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
 rule_name VARCHAR(200) NOT NULL,
 entity_type VARCHAR(40) NOT NULL,
 entity_id VARCHAR(36) NOT NULL,
 entity_name VARCHAR(255) NOT NULL,
 step_index INTEGER NOT NULL,
 action VARCHAR(40) NOT NULL,
 snapshot JSON NOT NULL,
 status VARCHAR(30) NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','completed','failed','cancelled','skipped')),
 scheduled_at TIMESTAMP,
 started_at TIMESTAMP,
 completed_at TIMESTAMP,
 attempts INTEGER NOT NULL DEFAULT 0,
 result VARCHAR(500) NOT NULL DEFAULT '',
 result_entity_type VARCHAR(40),
 result_entity_id VARCHAR(36),
 error_detail TEXT NOT NULL DEFAULT '',
 UNIQUE(org_id,run_id,step_index)
);
CREATE INDEX ix_automation_jobs_org_id ON automation_jobs(org_id);
CREATE INDEX ix_automation_jobs_run_id ON automation_jobs(run_id);
CREATE INDEX ix_automation_jobs_rule_id ON automation_jobs(rule_id);
CREATE INDEX ix_automation_jobs_status ON automation_jobs(status);
CREATE INDEX ix_automation_jobs_scheduled_at ON automation_jobs(scheduled_at);
