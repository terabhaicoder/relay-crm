// Generated from frontend/openapi.json. Do not edit.

export type AutomationInput = { "name": string; "trigger": "leads.created" | "leads.updated" | "leads.converted" | "deals.created" | "deals.won" | "deals.lost" | "deals.stage_changed" | "tickets.created" | "tickets.updated" | "activities.created" | "activities.completed"; "enabled"?: boolean; "conditions"?: Array<Condition>; "action"?: "create_task" | "notify"; "action_text"?: string; "due_days"?: number; "steps"?: Array<AutomationStep>; };

export type AutomationJobList = { "items": Array<AutomationJobResponse>; "total": number; "page": number; "page_size": number; };

export type AutomationJobResponse = { "id": string; "created_at": string; "run_id": string; "rule_id": string; "actor_id": string; "rule_name": string; "entity_type": string; "entity_id": string; "entity_name": string; "step_index": number; "action": "create_task" | "notify" | "assign_owner"; "trigger": string; "delay_minutes": number; "status": "queued" | "completed" | "failed" | "cancelled" | "skipped"; "scheduled_at": (string | null); "started_at": (string | null); "completed_at": (string | null); "attempts": number; "result": string; "result_entity_type": (string | null); "result_entity_id": (string | null); "error_detail": string; };

export type AutomationRunList = { "items": Array<AutomationRunResponse>; "total": number; "page": number; "page_size": number; };

export type AutomationRunResponse = { "id": string; "created_at": string; "rule_id": string; "event_key": string; "entity_type": string; "entity_id": string; "entity_name": string; "rule_name": string; "status": "queued" | "completed" | "failed" | "cancelled" | "skipped"; "result": string; "completed_at": (string | null); };

export type AutomationStep = { "action": "create_task" | "notify" | "assign_owner"; "delay_minutes"?: number; "action_text"?: string; "due_days"?: number; "owner_id"?: (string | null); };

export type AutomationToggle = { "enabled": boolean; };

export type CSVImport = { "csv": string; "mode"?: "skip" | "update" | "create"; };

export type CampaignMemberInput = { "entity_type": "leads" | "contacts"; "entity_id": string; };

export type Condition = { "field": "status" | "source" | "priority" | "score" | "amount" | "value" | "company"; "operator"?: "equals" | "contains" | "gte"; "value": string; };

export type ConvertLead = { "create_deal"?: boolean; "deal_name"?: (string | null); "amount"?: (number | string | null); "contact_id"?: (string | null); "party_id"?: (string | null); };

export type CustomDefinitionCreate = { "entity": "leads" | "contacts" | "parties" | "deals" | "tickets"; "field_key": string; "label": string; "field_type": "text" | "number" | "date" | "boolean" | "select"; "description"?: string; "options"?: Array<string>; };

export type CustomDefinitionList = { "items": Array<CustomDefinitionResponse>; "total": number; };

export type CustomDefinitionResponse = { "id": string; "entity": "leads" | "contacts" | "parties" | "deals" | "tickets"; "field_key": string; "label": string; "field_type": "text" | "number" | "date" | "boolean" | "select"; "description": string; "options": Array<string>; "archived": boolean; "version": number; };

export type CustomDefinitionUpdate = { "version": number; "label"?: (string | null); "description"?: (string | null); "options"?: (Array<string> | null); "archived"?: (boolean | null); };

export type CustomFieldChange = { "field_id": string; "label": string; "before": (string | boolean | null); "after": (string | boolean | null); };

export type CustomFieldEvent = { "action": string; "actor_id": string; "created_at": string; "changes": Array<CustomFieldChange>; };

export type CustomRecordResponse = { "entity": "leads" | "contacts" | "parties" | "deals" | "tickets"; "record_id": string; "version": number; "fields": Array<CustomDefinitionResponse>; "values": Record<string, (string | boolean | null)>; "history": Array<CustomFieldEvent>; };

export type CustomValuesUpdate = { "version": number; "values": Record<string, (string | boolean | null)>; };

export type DraftInput = { "recipient": string; "subject": string; "body": string; "entity_type"?: (string | null); "entity_id"?: (string | null); };

export type ErrorBody = { "code": string; "message": string; "details"?: Record<string, unknown>; };

export type ErrorResponse = { "error": ErrorBody; };

export type EventResponse = { "action": string; "actor_id": string; "created_at": string; "changes": Record<string, (string | boolean)>; };

export type ForecastDeal = { "id": string; "name": string; "amount": string; "probability": number; "weighted_value": string; "status": string; "stage": string; "close_date": (string | null); "lost_reason": string; };

export type ForecastMonth = { "month": string; "open_value": string; "weighted_value": string; "won_value": string; "lost_value": string; };

export type ForecastReport = { "date_from": string; "date_to": string; "today": string; "summary": ForecastTotals; "months": Array<ForecastMonth>; "items": Array<ForecastDeal>; "total": number; "limit": number; "offset": number; };

export type ForecastTotals = { "open_count"?: number; "open_value"?: string; "weighted_value"?: string; "won_count"?: number; "won_value"?: string; "lost_count"?: number; "lost_value"?: string; "win_rate"?: string; "overdue_count"?: number; "undated_count"?: number; };

export type FormInput = { "name": string; "title": string; "description"?: string; "source"?: string; "enabled"?: boolean; "owner_ids"?: Array<string>; "version"?: (number | null); };

export type FormList = { "items": Array<FormResponse>; "total": number; };

export type FormResponse = { "name": string; "title": string; "description"?: string; "source"?: string; "enabled"?: boolean; "owner_ids"?: Array<string>; "version": number; "id": string; "submissions": number; "new_leads": number; "duplicates": number; "created_at": string; };

export type HTTPValidationError = { "detail"?: Array<ValidationError>; };

export type HealthResponse = { "status"?: "ok"; };

export type InviteAccept = { "token": string; "name": string; "password": string; };

export type InviteCreate = { "email": string; "role"?: "Admin" | "Sales Manager" | "Sales Rep" | "Support Agent" | "Read-only"; };

export type LeadMergeInput = { "target_id": string; "source_version"?: (number | null); "target_version"?: (number | null); };

export type LeadMergePair = { "target_id": string; "source_version"?: (number | null); "target_version"?: (number | null); "source_id": string; };

export type LineInput = { "description": string; "quantity": (number | string); "unit_price": (number | string); };

export type LineResponse = { "id": string; "description": string; "quantity": string; "unit_price": string; "amount": string; };

export type LoginRequest = { "email": string; "password": string; };

export type MessageInput = { "body": string; "internal"?: boolean; };

export type PasswordChange = { "current_password": string; "new_password": string; };

export type PipelineInput = { "name": string; "stages"?: Array<string>; };

export type PipelineStageInput = { "id"?: (string | null); "name": string; "probability": number; "category": "open" | "won" | "lost"; };

export type PipelineUpdate = { "name"?: (string | null); "stages"?: (Array<PipelineStageInput> | null); };

export type ProfileUpdate = { "name": string; };

export type PublicForm = { "id": string; "title": string; "description": string; "organization": string; };

export type QuoteCreate = { "name": string; "valid_until"?: (string | null); "terms"?: string; "discount"?: (number | string); "lines": Array<LineInput>; "deal_id": string; };

export type QuoteEdit = { "name": string; "valid_until"?: (string | null); "terms"?: string; "discount"?: (number | string); "lines": Array<LineInput>; "version": number; };

export type QuoteList = { "items": Array<QuoteResponse>; "total": number; };

export type QuoteResponse = { "id": string; "deal_id": string; "party_id": (string | null); "contact_id": (string | null); "name": string; "status": "draft" | "issued" | "accepted" | "declined"; "currency": "INR"; "customer_name": string; "contact_name": string; "deal_name": string; "valid_until": (string | null); "terms": string; "subtotal": string; "discount": string; "total": string; "version": number; "created_at": string; "updated_at": string; "issued_at": (string | null); "decided_at": (string | null); "decision_note": string; "lines": Array<LineResponse>; "events": Array<EventResponse>; };

export type QuoteTransition = { "version": number; "note"?: string; "close_deal"?: boolean; "deal_version"?: (number | null); };

export type Receipt = { "accepted"?: true; "message"?: string; };

export type SignupRequest = { "email": string; "password": string; "name": string; "company_name": string; };

export type StageChange = { "stage_id": string; "version"?: (number | null); "reason"?: string; };

export type SubmissionInput = { "name": string; "email": string; "phone"?: string; "company"?: string; "message"?: string; "consent": true; };

export type SubmissionList = { "items": Array<SubmissionResponse>; "total": number; };

export type SubmissionResponse = { "id": string; "lead_id": string; "name": string; "message": string; "duplicate": boolean; "created_at": string; };

export type TeamCreate = { "email": string; "password": string; "name": string; "role"?: "Admin" | "Sales Manager" | "Sales Rep" | "Support Agent" | "Read-only"; };

export type TeamUpdate = { "role"?: ("Admin" | "Sales Manager" | "Sales Rep" | "Support Agent" | "Read-only" | null); "is_active"?: (boolean | null); };

export type TemplateInput = { "name": string; "subject": string; "body": string; };

export type UserResponse = { "id": string; "org_id": string; "name": string; "email": string; "role": string; "company_name": string; "is_active"?: boolean; };

export type ValidationError = { "loc": Array<(string | number)>; "msg": string; "type": string; };

export type ViewCreate = { "entity": "leads" | "contacts" | "parties" | "deals" | "activities" | "campaigns" | "tickets"; "name": string; "filters": ViewFilters; };

export type ViewFilters = { "q"?: string; "status"?: string; "sort"?: string; "pipeline_id"?: (string | null); "view"?: ("board" | "table" | null); };

export type ViewList = { "items": Array<ViewResponse>; "total": number; };

export type ViewResponse = { "id": string; "entity": "leads" | "contacts" | "parties" | "deals" | "activities" | "campaigns" | "tickets"; "name": string; "filters": ViewFilters; "version": number; "created_at": string; "updated_at": string; };

export type ViewUpdate = { "name": string; "filters": ViewFilters; "version": number; };

export type LeadInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "email"?: string; "phone"?: string; "company"?: string; "title"?: string; "source"?: string; "status"?: "New" | "Contacted" | "Qualified" | "Unqualified" | "Converted"; "value"?: (number | string); "score"?: number; "next_follow_up"?: (string | null); "notes"?: string; };

export type ContactInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "email"?: string; "phone"?: string; "company"?: string; "party_id"?: (string | null); "title"?: string; "notes"?: string; };

export type PartyInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "email"?: string; "phone"?: string; "website"?: string; "industry"?: string; "city"?: string; "notes"?: string; };

export type DealInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "party_id"?: (string | null); "contact_id"?: (string | null); "pipeline_id"?: (string | null); "stage_id"?: (string | null); "amount"?: (number | string); "probability"?: number; "expected_close_date"?: (string | null); "status"?: "open" | "won" | "lost"; "lost_reason"?: string; "notes"?: string; };

export type ActivityInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "type"?: "task" | "call" | "meeting" | "email" | "note" | "follow-up"; "status"?: "pending" | "completed"; "priority"?: "low" | "medium" | "high"; "due_date"?: (string | null); "entity_type"?: (string | null); "entity_id"?: (string | null); "notes"?: string; };

export type CampaignInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "type"?: string; "status"?: "draft" | "active" | "completed" | "paused"; "budget"?: (number | string); "spent"?: (number | string); "start_date"?: (string | null); "end_date"?: (string | null); "notes"?: string; };

export type TicketInput = { "name"?: string; "owner_id"?: (string | null); "tags"?: Array<string>; "version"?: (number | null); "deal_id"?: (string | null); "priority"?: "low" | "medium" | "high" | "urgent"; "status"?: "New" | "Open" | "Pending" | "Resolved" | "Closed"; "category"?: string; "party_id"?: (string | null); "contact_id"?: (string | null); "description"?: string; };

export type LivenessResponse = HealthResponse;

export type ReadinessResponse = HealthResponse;

export type ApiOperations = {
"GET /api/v1/health/live": { request: never; response: HealthResponse; };
"GET /api/v1/health/ready": { request: never; response: HealthResponse; };
"GET /api/v1/auth/options": { request: never; response: Record<string, boolean>; };
"POST /api/v1/auth/signup": { request: SignupRequest; response: UserResponse; };
"POST /api/v1/auth/login": { request: LoginRequest; response: UserResponse; };
"POST /api/v1/auth/logout": { request: never; response: void; };
"GET /api/v1/me": { request: never; response: UserResponse; };
"PATCH /api/v1/me": { request: ProfileUpdate; response: UserResponse; };
"GET /api/v1/auth/me": { request: never; response: UserResponse; };
"GET /api/v1/team": { request: never; response: Array<UserResponse>; };
"POST /api/v1/team": { request: TeamCreate; response: UserResponse; };
"POST /api/v1/auth/logout-all": { request: never; response: void; };
"POST /api/v1/auth/change-password": { request: PasswordChange; response: UserResponse; };
"POST /api/v1/team/invites": { request: InviteCreate; response: Record<string, unknown>; };
"GET /api/v1/auth/invites/{token}": { request: never; response: Record<string, string>; };
"POST /api/v1/auth/accept-invite": { request: InviteAccept; response: UserResponse; };
"PATCH /api/v1/team/{member_id}": { request: TeamUpdate; response: UserResponse; };
"GET /api/v1/auth/sessions": { request: never; response: Array<Record<string, unknown>>; };
"DELETE /api/v1/auth/sessions/{session_id}": { request: never; response: void; };
"GET /api/v1/automations": { request: never; response: Record<string, unknown>; };
"POST /api/v1/automations": { request: AutomationInput; response: Record<string, unknown>; };
"PATCH /api/v1/automations/{record_id}": { request: (AutomationInput | AutomationToggle); response: Record<string, unknown>; };
"GET /api/v1/automations/runs": { request: never; response: AutomationRunList; };
"GET /api/v1/automations/jobs": { request: never; response: AutomationJobList; };
"POST /api/v1/automations/jobs/{record_id}/retry": { request: never; response: AutomationJobResponse; };
"POST /api/v1/automations/jobs/{record_id}/cancel": { request: never; response: AutomationJobResponse; };
"GET /api/v1/notifications": { request: never; response: Record<string, unknown>; };
"POST /api/v1/notifications/{record_id}/read": { request: never; response: Record<string, unknown>; };
"GET /api/v1/email/templates": { request: never; response: Record<string, unknown>; };
"POST /api/v1/email/templates": { request: TemplateInput; response: Record<string, unknown>; };
"DELETE /api/v1/email/templates/{record_id}": { request: never; response: void; };
"PATCH /api/v1/email/templates/{record_id}": { request: TemplateInput; response: Record<string, unknown>; };
"GET /api/v1/email/messages": { request: never; response: Record<string, unknown>; };
"POST /api/v1/email/messages": { request: DraftInput; response: Record<string, unknown>; };
"GET /api/v1/email/messages/{record_id}": { request: never; response: Record<string, unknown>; };
"PATCH /api/v1/email/messages/{record_id}": { request: DraftInput; response: Record<string, unknown>; };
"DELETE /api/v1/email/messages/{record_id}": { request: never; response: void; };
"POST /api/v1/email/messages/{record_id}/send": { request: never; response: unknown; };
"GET /api/v1/integrations": { request: never; response: Record<string, unknown>; };
"GET /api/v1/attachments": { request: never; response: Record<string, unknown>; };
"POST /api/v1/attachments": { request: never; response: Record<string, unknown>; };
"GET /api/v1/attachments/{attachment_id}/download": { request: never; response: unknown; };
"DELETE /api/v1/attachments/{attachment_id}": { request: never; response: void; };
"GET /api/v1/reports/sales": { request: never; response: ForecastReport; };
"GET /api/v1/quotations": { request: never; response: QuoteList; };
"POST /api/v1/quotations": { request: QuoteCreate; response: QuoteResponse; };
"GET /api/v1/quotations/{quote_id}": { request: never; response: QuoteResponse; };
"PATCH /api/v1/quotations/{quote_id}": { request: QuoteEdit; response: QuoteResponse; };
"POST /api/v1/quotations/{quote_id}/{action}": { request: QuoteTransition; response: QuoteResponse; };
"GET /api/v1/saved-views": { request: never; response: ViewList; };
"POST /api/v1/saved-views": { request: ViewCreate; response: ViewResponse; };
"GET /api/v1/saved-views/{record_id}": { request: never; response: ViewResponse; };
"PATCH /api/v1/saved-views/{record_id}": { request: ViewUpdate; response: ViewResponse; };
"DELETE /api/v1/saved-views/{record_id}": { request: never; response: void; };
"GET /api/v1/custom-fields/definitions": { request: never; response: CustomDefinitionList; };
"POST /api/v1/custom-fields/definitions": { request: CustomDefinitionCreate; response: CustomDefinitionResponse; };
"PATCH /api/v1/custom-fields/definitions/{field_id}": { request: CustomDefinitionUpdate; response: CustomDefinitionResponse; };
"GET /api/v1/custom-fields/records/{entity}/{record_id}": { request: never; response: CustomRecordResponse; };
"PATCH /api/v1/custom-fields/records/{entity}/{record_id}": { request: CustomValuesUpdate; response: CustomRecordResponse; };
"GET /api/v1/capture-forms": { request: never; response: FormList; };
"POST /api/v1/capture-forms": { request: FormInput; response: FormResponse; };
"PATCH /api/v1/capture-forms/{record_id}": { request: FormInput; response: FormResponse; };
"GET /api/v1/capture-forms/{record_id}/submissions": { request: never; response: SubmissionList; };
"GET /api/v1/public/forms/{record_id}": { request: never; response: PublicForm; };
"POST /api/v1/public/forms/{record_id}": { request: SubmissionInput; response: Receipt; };
"GET /api/v1/dashboard/{role}": { request: never; response: Record<string, unknown>; };
"GET /api/v1/dashboard": { request: never; response: Record<string, unknown>; };
"GET /api/v1/reports/{name}": { request: never; response: Record<string, unknown>; };
"GET /api/v1/pipelines": { request: never; response: Record<string, unknown>; };
"POST /api/v1/pipelines": { request: PipelineInput; response: Record<string, unknown>; };
"GET /api/v1/calendar": { request: never; response: Record<string, unknown>; };
"GET /api/v1/deals/board-summary": { request: never; response: Record<string, unknown>; };
"GET /api/v1/workbench": { request: never; response: Record<string, unknown>; };
"PATCH /api/v1/pipelines/{pipeline_id}": { request: PipelineUpdate; response: Record<string, unknown>; };
"GET /api/v1/{entity}/{record_id}/overview": { request: never; response: Record<string, unknown>; };
"GET /api/v1/campaigns/{campaign_id}/members": { request: never; response: Record<string, unknown>; };
"POST /api/v1/campaigns/{campaign_id}/members": { request: CampaignMemberInput; response: Record<string, unknown>; };
"DELETE /api/v1/campaigns/{campaign_id}/members/{membership_id}": { request: never; response: void; };
"GET /api/v1/search": { request: never; response: Record<string, unknown>; };
"GET /api/v1/me/tasks": { request: never; response: Record<string, unknown>; };
"GET /api/v1/leads/duplicates": { request: never; response: Record<string, unknown>; };
"POST /api/v1/leads/{record_id}/merge": { request: LeadMergeInput; response: Record<string, unknown>; };
"POST /api/v1/leads/merge": { request: LeadMergePair; response: Record<string, unknown>; };
"POST /api/v1/leads/{record_id}/convert": { request: ConvertLead; response: Record<string, unknown>; };
"PATCH /api/v1/deals/{record_id}/stage": { request: StageChange; response: Record<string, unknown>; };
"POST /api/v1/deals/{record_id}/won": { request: never; response: Record<string, unknown>; };
"POST /api/v1/deals/{record_id}/lost": { request: Record<string, unknown>; response: Record<string, unknown>; };
"GET /api/v1/deals/{record_id}/history": { request: never; response: Record<string, unknown>; };
"GET /api/v1/tickets/{record_id}/messages": { request: never; response: Record<string, unknown>; };
"POST /api/v1/tickets/{record_id}/messages": { request: MessageInput; response: Record<string, unknown>; };
"POST /api/v1/activities/{record_id}/complete": { request: never; response: Record<string, unknown>; };
"GET /api/v1/{entity}/export": { request: never; response: unknown; };
"POST /api/v1/{entity}/import": { request: CSVImport; response: Record<string, unknown>; };
"GET /api/v1/{entity}/{record_id}/timeline": { request: never; response: Record<string, unknown>; };
"GET /api/v1/demo/status": { request: never; response: Record<string, unknown>; };
"POST /api/v1/demo/seed": { request: never; response: Record<string, unknown>; };
"GET /api/v1/{entity}": { request: never; response: Record<string, unknown>; };
"POST /api/v1/{entity}": { request: Record<string, unknown>; response: Record<string, unknown>; };
"GET /api/v1/{entity}/{record_id}": { request: never; response: Record<string, unknown>; };
"PATCH /api/v1/{entity}/{record_id}": { request: Record<string, unknown>; response: Record<string, unknown>; };
"DELETE /api/v1/{entity}/{record_id}": { request: never; response: void; };
};
