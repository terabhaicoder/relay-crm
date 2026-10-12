-- Immutable SQLite migration: 0002_crm. Add a new migration for future schema changes.

CREATE TABLE IF NOT EXISTS audit_events (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	entity_type VARCHAR(30) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	changes JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_audit_events PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_audit_events_entity_id ON audit_events (entity_id);

CREATE INDEX IF NOT EXISTS ix_audit_events_org_id ON audit_events (org_id);

CREATE TABLE IF NOT EXISTS crm_idempotency_keys (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	"key" VARCHAR(255) NOT NULL, 
	route VARCHAR(255) NOT NULL, 
	payload_hash VARCHAR(64) NOT NULL, 
	response JSON NOT NULL, 
	CONSTRAINT pk_crm_idempotency_keys PRIMARY KEY (id), 
	CONSTRAINT uq_crm_idempotency_keys_org_id UNIQUE (org_id, route, "key")
);

CREATE INDEX IF NOT EXISTS ix_crm_idempotency_keys_org_id ON crm_idempotency_keys (org_id);

CREATE TABLE IF NOT EXISTS activities (
	type VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	due_date VARCHAR(40), 
	entity_type VARCHAR(30), 
	entity_id VARCHAR(36), 
	notes TEXT NOT NULL, 
	completed_at DATETIME, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_activities PRIMARY KEY (id), 
	CONSTRAINT fk_activities_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_activities_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_activities_due_date ON activities (due_date);

CREATE INDEX IF NOT EXISTS ix_activities_org_id ON activities (org_id);

CREATE INDEX IF NOT EXISTS ix_activities_owner_id ON activities (owner_id);

CREATE INDEX IF NOT EXISTS ix_activities_status ON activities (status);

CREATE INDEX IF NOT EXISTS ix_activities_updated_at ON activities (updated_at);

CREATE TABLE IF NOT EXISTS campaigns (
	type VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	budget NUMERIC(18, 2) NOT NULL, 
	spent NUMERIC(18, 2) NOT NULL, 
	start_date VARCHAR(40), 
	end_date VARCHAR(40), 
	notes TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_campaigns PRIMARY KEY (id), 
	CONSTRAINT fk_campaigns_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_campaigns_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_campaigns_org_id ON campaigns (org_id);

CREATE INDEX IF NOT EXISTS ix_campaigns_owner_id ON campaigns (owner_id);

CREATE INDEX IF NOT EXISTS ix_campaigns_updated_at ON campaigns (updated_at);

CREATE TABLE IF NOT EXISTS leads (
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(40) NOT NULL, 
	company VARCHAR(255) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	source VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	value NUMERIC(18, 2) NOT NULL, 
	score INTEGER NOT NULL, 
	next_follow_up VARCHAR(40), 
	notes TEXT NOT NULL, 
	converted_contact_id VARCHAR(36), 
	converted_party_id VARCHAR(36), 
	converted_deal_id VARCHAR(36), 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_leads PRIMARY KEY (id), 
	CONSTRAINT fk_leads_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_leads_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_leads_email ON leads (email);

CREATE INDEX IF NOT EXISTS ix_leads_org_id ON leads (org_id);

CREATE INDEX IF NOT EXISTS ix_leads_org_owner_status ON leads (org_id, owner_id, status);

CREATE INDEX IF NOT EXISTS ix_leads_owner_id ON leads (owner_id);

CREATE INDEX IF NOT EXISTS ix_leads_phone ON leads (phone);

CREATE INDEX IF NOT EXISTS ix_leads_status ON leads (status);

CREATE INDEX IF NOT EXISTS ix_leads_updated_at ON leads (updated_at);

CREATE TABLE IF NOT EXISTS parties (
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(40) NOT NULL, 
	website VARCHAR(512) NOT NULL, 
	industry VARCHAR(120) NOT NULL, 
	city VARCHAR(120) NOT NULL, 
	notes TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_parties PRIMARY KEY (id), 
	CONSTRAINT fk_parties_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_parties_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_parties_org_id ON parties (org_id);

CREATE INDEX IF NOT EXISTS ix_parties_owner_id ON parties (owner_id);

CREATE INDEX IF NOT EXISTS ix_parties_updated_at ON parties (updated_at);

CREATE TABLE IF NOT EXISTS pipelines (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_pipelines PRIMARY KEY (id), 
	CONSTRAINT fk_pipelines_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_pipelines_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_pipelines_org_id ON pipelines (org_id);

CREATE INDEX IF NOT EXISTS ix_pipelines_owner_id ON pipelines (owner_id);

CREATE INDEX IF NOT EXISTS ix_pipelines_updated_at ON pipelines (updated_at);

CREATE TABLE IF NOT EXISTS contacts (
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(40) NOT NULL, 
	company VARCHAR(255) NOT NULL, 
	party_id VARCHAR(36), 
	title VARCHAR(255) NOT NULL, 
	notes TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_contacts PRIMARY KEY (id), 
	CONSTRAINT fk_contacts_party_id_parties FOREIGN KEY(party_id) REFERENCES parties (id), 
	CONSTRAINT fk_contacts_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_contacts_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_contacts_email ON contacts (email);

CREATE INDEX IF NOT EXISTS ix_contacts_org_id ON contacts (org_id);

CREATE INDEX IF NOT EXISTS ix_contacts_owner_id ON contacts (owner_id);

CREATE INDEX IF NOT EXISTS ix_contacts_phone ON contacts (phone);

CREATE INDEX IF NOT EXISTS ix_contacts_updated_at ON contacts (updated_at);

CREATE TABLE IF NOT EXISTS stages (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	pipeline_id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	probability INTEGER NOT NULL, 
	position INTEGER NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	color VARCHAR(20) NOT NULL, 
	CONSTRAINT pk_stages PRIMARY KEY (id), 
	CONSTRAINT fk_stages_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_stages_pipeline_id_pipelines FOREIGN KEY(pipeline_id) REFERENCES pipelines (id)
);

CREATE INDEX IF NOT EXISTS ix_stages_org_id ON stages (org_id);

CREATE INDEX IF NOT EXISTS ix_stages_pipeline_id ON stages (pipeline_id);

CREATE TABLE IF NOT EXISTS deals (
	party_id VARCHAR(36), 
	contact_id VARCHAR(36), 
	pipeline_id VARCHAR(36) NOT NULL, 
	stage_id VARCHAR(36) NOT NULL, 
	amount NUMERIC(18, 2) NOT NULL, 
	probability INTEGER NOT NULL, 
	expected_close_date VARCHAR(40), 
	status VARCHAR(20) NOT NULL, 
	lost_reason TEXT NOT NULL, 
	notes TEXT NOT NULL, 
	stage_entered_at DATETIME NOT NULL, 
	closed_at DATETIME, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_deals PRIMARY KEY (id), 
	CONSTRAINT fk_deals_party_id_parties FOREIGN KEY(party_id) REFERENCES parties (id), 
	CONSTRAINT fk_deals_contact_id_contacts FOREIGN KEY(contact_id) REFERENCES contacts (id), 
	CONSTRAINT fk_deals_pipeline_id_pipelines FOREIGN KEY(pipeline_id) REFERENCES pipelines (id), 
	CONSTRAINT fk_deals_stage_id_stages FOREIGN KEY(stage_id) REFERENCES stages (id), 
	CONSTRAINT fk_deals_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_deals_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_deals_org_id ON deals (org_id);

CREATE INDEX IF NOT EXISTS ix_deals_org_status_stage ON deals (org_id, status, stage_id);

CREATE INDEX IF NOT EXISTS ix_deals_owner_id ON deals (owner_id);

CREATE INDEX IF NOT EXISTS ix_deals_stage_id ON deals (stage_id);

CREATE INDEX IF NOT EXISTS ix_deals_status ON deals (status);

CREATE INDEX IF NOT EXISTS ix_deals_updated_at ON deals (updated_at);

CREATE TABLE IF NOT EXISTS deal_stage_history (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	deal_id VARCHAR(36) NOT NULL, 
	from_stage_id VARCHAR(36), 
	to_stage_id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	reason TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_deal_stage_history PRIMARY KEY (id), 
	CONSTRAINT fk_deal_stage_history_deal_id_deals FOREIGN KEY(deal_id) REFERENCES deals (id)
);

CREATE INDEX IF NOT EXISTS ix_deal_stage_history_deal_id ON deal_stage_history (deal_id);

CREATE INDEX IF NOT EXISTS ix_deal_stage_history_org_id ON deal_stage_history (org_id);

CREATE TABLE IF NOT EXISTS tickets (
	deal_id VARCHAR(36), 
	priority VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	category VARCHAR(100) NOT NULL, 
	party_id VARCHAR(36), 
	contact_id VARCHAR(36), 
	description TEXT NOT NULL, 
	resolved_at DATETIME, 
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	owner_id VARCHAR(36), 
	tags JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	deleted_at DATETIME, 
	version INTEGER NOT NULL, 
	CONSTRAINT pk_tickets PRIMARY KEY (id), 
	CONSTRAINT fk_tickets_deal_id_deals FOREIGN KEY(deal_id) REFERENCES deals (id), 
	CONSTRAINT fk_tickets_party_id_parties FOREIGN KEY(party_id) REFERENCES parties (id), 
	CONSTRAINT fk_tickets_contact_id_contacts FOREIGN KEY(contact_id) REFERENCES contacts (id), 
	CONSTRAINT fk_tickets_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_tickets_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_tickets_org_id ON tickets (org_id);

CREATE INDEX IF NOT EXISTS ix_tickets_owner_id ON tickets (owner_id);

CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets (status);

CREATE INDEX IF NOT EXISTS ix_tickets_updated_at ON tickets (updated_at);

CREATE TABLE IF NOT EXISTS ticket_messages (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	ticket_id VARCHAR(36) NOT NULL, 
	author_id VARCHAR(36) NOT NULL, 
	body TEXT NOT NULL, 
	internal BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_ticket_messages PRIMARY KEY (id), 
	CONSTRAINT fk_ticket_messages_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_ticket_messages_ticket_id_tickets FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	CONSTRAINT fk_ticket_messages_author_id_users FOREIGN KEY(author_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_ticket_messages_org_id ON ticket_messages (org_id);

CREATE INDEX IF NOT EXISTS ix_ticket_messages_ticket_id ON ticket_messages (ticket_id);
