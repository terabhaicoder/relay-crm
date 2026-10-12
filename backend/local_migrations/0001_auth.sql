-- Immutable SQLite migration: 0001_auth. Add a new migration for future schema changes.

CREATE TABLE IF NOT EXISTS orgs (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_orgs PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS users (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(300) NOT NULL, 
	role VARCHAR(30) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT fk_users_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE INDEX IF NOT EXISTS ix_users_org_id ON users (org_id);

CREATE TABLE IF NOT EXISTS invites (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	role VARCHAR(30) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	invited_by VARCHAR(36) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	accepted_at DATETIME, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_invites PRIMARY KEY (id), 
	CONSTRAINT fk_invites_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_invites_invited_by_users FOREIGN KEY(invited_by) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_invites_email ON invites (email);

CREATE INDEX IF NOT EXISTS ix_invites_org_id ON invites (org_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_invites_token_hash ON invites (token_hash);

CREATE TABLE IF NOT EXISTS login_sessions (
	id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_login_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_login_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_login_sessions_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id)
);

CREATE INDEX IF NOT EXISTS ix_login_sessions_org_id ON login_sessions (org_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_login_sessions_token_hash ON login_sessions (token_hash);

CREATE INDEX IF NOT EXISTS ix_login_sessions_user_id ON login_sessions (user_id);

CREATE TABLE IF NOT EXISTS security_audit_logs (
	id VARCHAR(36) NOT NULL, 
	org_id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	action VARCHAR(60) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	created_at DATETIME NOT NULL, 
	CONSTRAINT pk_security_audit_logs PRIMARY KEY (id), 
	CONSTRAINT fk_security_audit_logs_org_id_orgs FOREIGN KEY(org_id) REFERENCES orgs (id), 
	CONSTRAINT fk_security_audit_logs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS ix_security_audit_logs_org_id ON security_audit_logs (org_id);
