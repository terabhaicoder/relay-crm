-- CRM commercial estimates only; no invoice, tax posting or payment claims.
CREATE TABLE quotations (
 id VARCHAR(36) PRIMARY KEY, org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 deal_id VARCHAR(36) NOT NULL REFERENCES deals(id), party_id VARCHAR(36) REFERENCES parties(id),
 contact_id VARCHAR(36) REFERENCES contacts(id), name VARCHAR(200) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','issued','accepted','declined')),
 currency VARCHAR(3) NOT NULL DEFAULT 'INR' CHECK(currency = 'INR'),
 customer_name VARCHAR(255) NOT NULL, contact_name VARCHAR(255) NOT NULL DEFAULT '',
 deal_name VARCHAR(200) NOT NULL, valid_until VARCHAR(10), terms TEXT NOT NULL DEFAULT '',
 subtotal NUMERIC(18,2) NOT NULL CHECK(subtotal >= 0), discount NUMERIC(18,2) NOT NULL DEFAULT 0,
 total NUMERIC(18,2) NOT NULL CHECK(total >= 0), version INTEGER NOT NULL DEFAULT 1,
 created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL,
 created_by VARCHAR(36) NOT NULL REFERENCES users(id), updated_by VARCHAR(36) NOT NULL REFERENCES users(id),
 issued_at TIMESTAMP, decided_at TIMESTAMP, decision_note TEXT NOT NULL DEFAULT '',
 CHECK(discount >= 0 AND discount <= subtotal)
);
CREATE INDEX ix_quotations_org_id ON quotations(org_id);
CREATE INDEX ix_quotations_deal_id ON quotations(deal_id);
CREATE INDEX ix_quotations_status ON quotations(status);
CREATE TABLE quotation_lines (
 id VARCHAR(36) PRIMARY KEY, org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 quotation_id VARCHAR(36) NOT NULL REFERENCES quotations(id), position INTEGER NOT NULL,
 description VARCHAR(500) NOT NULL, quantity NUMERIC(18,3) NOT NULL CHECK(quantity > 0),
 unit_price NUMERIC(18,4) NOT NULL CHECK(unit_price >= 0), amount NUMERIC(18,2) NOT NULL CHECK(amount >= 0),
 UNIQUE(quotation_id, position)
);
CREATE INDEX ix_quotation_lines_org_id ON quotation_lines(org_id);
CREATE INDEX ix_quotation_lines_quotation_id ON quotation_lines(quotation_id);
CREATE TABLE quotation_events (
 id VARCHAR(36) PRIMARY KEY, org_id VARCHAR(36) NOT NULL REFERENCES orgs(id),
 quotation_id VARCHAR(36) NOT NULL REFERENCES quotations(id), actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
 action VARCHAR(30) NOT NULL, changes JSON NOT NULL, created_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_quotation_events_org_id ON quotation_events(org_id);
CREATE INDEX ix_quotation_events_quotation_id ON quotation_events(quotation_id);
