-- ==============================================================================
-- Codenter AI SDR Platform — Supabase PostgreSQL Schema
-- Generated strictly according to Section 12 Specification & ORM Models
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: users
CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	status user_status NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

-- Table: workspaces
CREATE TABLE workspaces (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	domain VARCHAR(255), 
	settings JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


-- Table: audit_logs
CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36), 
	actor_email VARCHAR(255), 
	action VARCHAR(100) NOT NULL, 
	resource_type VARCHAR(100) NOT NULL, 
	resource_id VARCHAR(255), 
	payload JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_audit_logs_workspace_id ON audit_logs (workspace_id);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

-- Table: business_profiles
CREATE TABLE business_profiles (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	company_name VARCHAR(255) NOT NULL, 
	legal_name VARCHAR(255), 
	description TEXT, 
	offerings JSON NOT NULL, 
	value_propositions JSON NOT NULL, 
	industries JSON NOT NULL, 
	icp_hints JSON NOT NULL, 
	pricing JSON, 
	features JSON NOT NULL, 
	faqs JSON NOT NULL, 
	proof JSON NOT NULL, 
	brand_voice JSON NOT NULL, 
	claims_policy JSON NOT NULL, 
	ctas JSON NOT NULL, 
	version INTEGER NOT NULL, 
	confidence_score FLOAT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_business_profiles_workspace_id ON business_profiles (workspace_id);

-- Table: calendar_connections
CREATE TABLE calendar_connections (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	provider calendar_provider_type NOT NULL, 
	account_email VARCHAR(255) NOT NULL, 
	encrypted_access_token VARCHAR(1000) NOT NULL, 
	encrypted_refresh_token VARCHAR(1000) NOT NULL, 
	token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	sync_status VARCHAR(50) NOT NULL, 
	working_hours_json JSON NOT NULL, 
	buffer_minutes INTEGER NOT NULL, 
	timezone VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_calendar_connections_workspace_id ON calendar_connections (workspace_id);

-- Table: campaigns
CREATE TABLE campaigns (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	status campaign_state NOT NULL, 
	objective VARCHAR(255) NOT NULL, 
	config_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_campaigns_workspace_id ON campaigns (workspace_id);
CREATE INDEX ix_campaigns_status ON campaigns (status);

-- Table: crm_connections
CREATE TABLE crm_connections (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	provider crm_provider_type NOT NULL, 
	account_id VARCHAR(100), 
	account_name VARCHAR(255), 
	encrypted_access_token TEXT NOT NULL, 
	encrypted_refresh_token TEXT NOT NULL, 
	token_expires_at TIMESTAMP WITH TIME ZONE, 
	field_mappings_json JSON NOT NULL, 
	sync_status crm_sync_status NOT NULL, 
	last_sync_at TIMESTAMP WITH TIME ZONE, 
	sync_cursor VARCHAR(255), 
	sync_error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_crm_connections_workspace_id ON crm_connections (workspace_id);

-- Table: email_accounts
CREATE TABLE email_accounts (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	provider email_provider_type NOT NULL, 
	email_address VARCHAR(255) NOT NULL, 
	encrypted_credentials TEXT NOT NULL, 
	daily_send_limit INTEGER NOT NULL, 
	current_day_sends INTEGER NOT NULL, 
	last_send_at TIMESTAMP WITH TIME ZONE, 
	health_status mailbox_health_status NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_email_accounts_email_address ON email_accounts (email_address);
CREATE INDEX ix_email_accounts_workspace_id ON email_accounts (workspace_id);

-- Table: knowledge_documents
CREATE TABLE knowledge_documents (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	url TEXT NOT NULL, 
	title VARCHAR(500), 
	content_hash VARCHAR(64) NOT NULL, 
	source_type VARCHAR(50) NOT NULL, 
	raw_text TEXT NOT NULL, 
	screenshot_url TEXT, 
	fetched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_knowledge_documents_workspace_id ON knowledge_documents (workspace_id);
CREATE INDEX ix_knowledge_documents_content_hash ON knowledge_documents (content_hash);

-- Table: suppression_list
CREATE TABLE suppression_list (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	email VARCHAR(255), 
	domain VARCHAR(255), 
	reason suppression_reason NOT NULL, 
	source VARCHAR(100), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_suppression_workspace_email UNIQUE (workspace_id, email), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_suppression_list_domain ON suppression_list (domain);
CREATE INDEX ix_suppression_list_workspace_id ON suppression_list (workspace_id);
CREATE INDEX ix_suppression_list_email ON suppression_list (email);

-- Table: usage_events
CREATE TABLE usage_events (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	event_type usage_event_type NOT NULL, 
	units INTEGER NOT NULL, 
	cost_estimate_usd NUMERIC(10, 6) NOT NULL, 
	metadata_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_usage_events_event_type ON usage_events (event_type);
CREATE INDEX ix_usage_events_workspace_id ON usage_events (workspace_id);
CREATE INDEX ix_usage_events_created_at ON usage_events (created_at);

-- Table: website_scans
CREATE TABLE website_scans (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	url TEXT NOT NULL, 
	status scan_status NOT NULL, 
	pages_discovered INTEGER NOT NULL, 
	pages_crawled INTEGER NOT NULL, 
	pages_failed INTEGER NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);

CREATE INDEX ix_website_scans_workspace_id ON website_scans (workspace_id);

-- Table: workspace_members
CREATE TABLE workspace_members (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	role workspace_role NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_workspace_members_workspace_id ON workspace_members (workspace_id);
CREATE INDEX ix_workspace_members_user_id ON workspace_members (user_id);

-- Table: campaign_steps
CREATE TABLE campaign_steps (
	id VARCHAR(36) NOT NULL, 
	campaign_id VARCHAR(36) NOT NULL, 
	step_number INTEGER NOT NULL, 
	delay_days INTEGER NOT NULL, 
	delay_hours INTEGER NOT NULL, 
	prompt_instructions TEXT, 
	template_config_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_campaign_step_number UNIQUE (campaign_id, step_number), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
);

CREATE INDEX ix_campaign_steps_campaign_id ON campaign_steps (campaign_id);

-- Table: crm_leads
CREATE TABLE crm_leads (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	crm_connection_id VARCHAR(36), 
	crm_record_id VARCHAR(100), 
	first_name VARCHAR(255), 
	last_name VARCHAR(255), 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(100), 
	job_title VARCHAR(255), 
	company_name VARCHAR(255), 
	domain VARCHAR(255), 
	industry VARCHAR(255), 
	employee_count INTEGER, 
	location VARCHAR(255), 
	revenue_band VARCHAR(100), 
	lifecycle_stage VARCHAR(100), 
	owner_id VARCHAR(100), 
	lead_notes TEXT, 
	custom_fields JSON NOT NULL, 
	opt_out BOOLEAN NOT NULL, 
	do_not_contact BOOLEAN NOT NULL, 
	bounce_status VARCHAR(50) NOT NULL, 
	icp_score FLOAT NOT NULL, 
	intent_score FLOAT NOT NULL, 
	total_score FLOAT NOT NULL, 
	score_reasons_json JSON NOT NULL, 
	qualification_status VARCHAR(50) NOT NULL, 
	qualification_details JSON NOT NULL, 
	is_qualified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_crm_leads_workspace_email UNIQUE (workspace_id, email), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(crm_connection_id) REFERENCES crm_connections (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_leads_email ON crm_leads (email);
CREATE INDEX ix_crm_leads_is_qualified ON crm_leads (is_qualified);
CREATE INDEX ix_crm_leads_total_score ON crm_leads (total_score);
CREATE INDEX ix_crm_leads_domain ON crm_leads (domain);
CREATE INDEX ix_crm_leads_opt_out ON crm_leads (opt_out);
CREATE INDEX ix_crm_leads_workspace_id ON crm_leads (workspace_id);
CREATE INDEX ix_crm_leads_crm_record_id ON crm_leads (crm_record_id);
CREATE INDEX ix_crm_leads_do_not_contact ON crm_leads (do_not_contact);
CREATE INDEX ix_crm_leads_qualification_status ON crm_leads (qualification_status);
CREATE INDEX ix_crm_leads_crm_connection_id ON crm_leads (crm_connection_id);

-- Table: knowledge_chunks
CREATE TABLE knowledge_chunks (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	document_id VARCHAR(36) NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	token_count INTEGER NOT NULL, 
	embedding VECTOR(1536), 
	metadata_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(document_id) REFERENCES knowledge_documents (id) ON DELETE CASCADE
);

CREATE INDEX ix_knowledge_chunks_workspace_id ON knowledge_chunks (workspace_id);
CREATE INDEX ix_knowledge_chunks_document_id ON knowledge_chunks (document_id);

-- Table: appointments
CREATE TABLE appointments (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	calendar_connection_id VARCHAR(36), 
	lead_id VARCHAR(36), 
	campaign_id VARCHAR(36), 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	start_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	attendee_email VARCHAR(255) NOT NULL, 
	host_email VARCHAR(255) NOT NULL, 
	status appointment_status NOT NULL, 
	provider_event_id VARCHAR(255), 
	meeting_link VARCHAR(500), 
	idempotency_key VARCHAR(255), 
	metadata_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(calendar_connection_id) REFERENCES calendar_connections (id) ON DELETE SET NULL, 
	FOREIGN KEY(lead_id) REFERENCES crm_leads (id) ON DELETE SET NULL
);

CREATE INDEX ix_appointments_start_time ON appointments (start_time);
CREATE INDEX ix_appointments_lead_id ON appointments (lead_id);
CREATE INDEX ix_appointments_provider_event_id ON appointments (provider_event_id);
CREATE INDEX ix_appointments_attendee_email ON appointments (attendee_email);
CREATE INDEX ix_appointments_campaign_id ON appointments (campaign_id);
CREATE INDEX ix_appointments_calendar_connection_id ON appointments (calendar_connection_id);
CREATE INDEX ix_appointments_host_email ON appointments (host_email);
CREATE INDEX ix_appointments_workspace_id ON appointments (workspace_id);
CREATE INDEX ix_appointments_idempotency_key ON appointments (idempotency_key);
CREATE INDEX ix_appointments_status ON appointments (status);

-- Table: campaign_leads
CREATE TABLE campaign_leads (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	campaign_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	current_step_number INTEGER NOT NULL, 
	state lead_sequence_state NOT NULL, 
	next_action_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_campaign_lead_enrollment UNIQUE (campaign_id, lead_id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES crm_leads (id) ON DELETE CASCADE
);

CREATE INDEX ix_campaign_leads_next_action_at ON campaign_leads (next_action_at);
CREATE INDEX ix_campaign_leads_state ON campaign_leads (state);
CREATE INDEX ix_campaign_leads_lead_id ON campaign_leads (lead_id);
CREATE INDEX ix_campaign_leads_workspace_id ON campaign_leads (workspace_id);
CREATE INDEX ix_campaign_leads_campaign_id ON campaign_leads (campaign_id);

-- Table: email_threads
CREATE TABLE email_threads (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36), 
	campaign_id VARCHAR(36), 
	subject VARCHAR(500) NOT NULL, 
	status thread_status NOT NULL, 
	summary TEXT, 
	last_message_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES crm_leads (id) ON DELETE SET NULL
);

CREATE INDEX ix_email_threads_campaign_id ON email_threads (campaign_id);
CREATE INDEX ix_email_threads_workspace_id ON email_threads (workspace_id);
CREATE INDEX ix_email_threads_lead_id ON email_threads (lead_id);

-- Table: lead_enrichments
CREATE TABLE lead_enrichments (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	company_summary TEXT, 
	role_summary TEXT, 
	detected_technologies JSON NOT NULL, 
	signals_json JSON NOT NULL, 
	source_urls JSON NOT NULL, 
	enriched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	UNIQUE (lead_id), 
	FOREIGN KEY(lead_id) REFERENCES crm_leads (id) ON DELETE CASCADE
);

CREATE INDEX ix_lead_enrichments_workspace_id ON lead_enrichments (workspace_id);

-- Table: conversation_events
CREATE TABLE conversation_events (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	thread_id VARCHAR(36), 
	lead_id VARCHAR(36), 
	campaign_id VARCHAR(36), 
	event_type VARCHAR(100) NOT NULL, 
	rule_name VARCHAR(255), 
	model_version VARCHAR(100), 
	prompt_version VARCHAR(100), 
	knowledge_chunk_ids JSON NOT NULL, 
	previous_state VARCHAR(100), 
	new_state VARCHAR(100), 
	data_payload JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(thread_id) REFERENCES email_threads (id) ON DELETE SET NULL, 
	FOREIGN KEY(lead_id) REFERENCES crm_leads (id) ON DELETE SET NULL, 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE SET NULL
);

CREATE INDEX ix_conversation_events_lead_id ON conversation_events (lead_id);
CREATE INDEX ix_conversation_events_event_type ON conversation_events (event_type);
CREATE INDEX ix_conversation_events_thread_id ON conversation_events (thread_id);
CREATE INDEX ix_conversation_events_created_at ON conversation_events (created_at);
CREATE INDEX ix_conversation_events_workspace_id ON conversation_events (workspace_id);
CREATE INDEX ix_conversation_events_campaign_id ON conversation_events (campaign_id);

-- Table: email_messages
CREATE TABLE email_messages (
	id VARCHAR(36) NOT NULL, 
	workspace_id VARCHAR(36) NOT NULL, 
	thread_id VARCHAR(36) NOT NULL, 
	provider_message_id VARCHAR(255), 
	direction message_direction NOT NULL, 
	from_address VARCHAR(255) NOT NULL, 
	to_address VARCHAR(255) NOT NULL, 
	subject VARCHAR(500) NOT NULL, 
	body_text TEXT NOT NULL, 
	body_html TEXT, 
	headers_json JSON NOT NULL, 
	delivery_status delivery_status NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(thread_id) REFERENCES email_threads (id) ON DELETE CASCADE
);

CREATE INDEX ix_email_messages_thread_id ON email_messages (thread_id);
CREATE INDEX ix_email_messages_workspace_id ON email_messages (workspace_id);
CREATE INDEX ix_email_messages_provider_message_id ON email_messages (provider_message_id);
