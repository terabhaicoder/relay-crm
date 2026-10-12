-- Immutable SQLite migration: 0003_engagement. Add a new migration for future schema changes.

CREATE TABLE IF NOT EXISTS email_templates (
	name VARCHAR(200) NOT NULL, 
	subject VARCHAR(300) NOT NULL, 
	body TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_email_templates PRIMARY KEY (id), 
	CONSTRAINT fk_email_templates_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE INDEX IF NOT EXISTS ix_email_templates_org_id ON email_templates (org_id);

CREATE TABLE IF NOT EXISTS automation_rules (
	name VARCHAR(200) NOT NULL, 
	"trigger" VARCHAR(80) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	conditions JSON NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	action_text VARCHAR(500) NOT NULL, 
	due_days INTEGER NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_automation_rules PRIMARY KEY (id), 
	CONSTRAINT fk_automation_rules_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), 
	CONSTRAINT fk_automation_rules_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE INDEX IF NOT EXISTS ix_automation_rules_org_id ON automation_rules (org_id);

CREATE TABLE IF NOT EXISTS email_messages (
	owner_id VARCHAR(36) NOT NULL, 
	recipient VARCHAR(254) NOT NULL, 
	subject VARCHAR(300) NOT NULL, 
	body TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	entity_type VARCHAR(40), 
	entity_id VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_email_messages PRIMARY KEY (id), 
	CONSTRAINT fk_email_messages_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), 
	CONSTRAINT fk_email_messages_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE INDEX IF NOT EXISTS ix_email_messages_org_id ON email_messages (org_id);

CREATE TABLE IF NOT EXISTS notifications (
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	entity_type VARCHAR(40), 
	entity_id VARCHAR(36), 
	read BOOLEAN NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_notifications PRIMARY KEY (id), 
	CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_notifications_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE INDEX IF NOT EXISTS ix_notifications_org_id ON notifications (org_id);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);

CREATE TABLE IF NOT EXISTS automation_runs (
	rule_id VARCHAR(36) NOT NULL, 
	event_key VARCHAR(200) NOT NULL, 
	entity_type VARCHAR(40) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	result VARCHAR(500) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_automation_runs PRIMARY KEY (id), 
	CONSTRAINT uq_automation_runs_org_id UNIQUE (org_id, rule_id, event_key), 
	CONSTRAINT fk_automation_runs_rule_id_automation_rules FOREIGN KEY(rule_id) REFERENCES automation_rules (id), 
	CONSTRAINT fk_automation_runs_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE INDEX IF NOT EXISTS ix_automation_runs_org_id ON automation_runs (org_id);

CREATE INDEX IF NOT EXISTS ix_automation_runs_rule_id ON automation_runs (rule_id);
