// Generated from frontend/openapi.json. Do not edit.

export type AutomationInput = { "name": string; "trigger": "leads.created" | "leads.updated" | "leads.converted" | "deals.created" | "deals.won" | "deals.lost" | "deals.stage_changed" | "tickets.created" | "tickets.updated" | "activities.created" | "activities.completed"; "enabled"?: boolean; "conditions"?: Array<Condition>; "action"?: "create_task" | "notify"; "action_text": string; "due_days"?: number; };

export type AutomationToggle = { "enabled": boolean; };

export type CSVImport = { "csv": string; "mode"?: "skip" | "update" | "create"; };

export type CampaignMemberInput = { "entity_type": "leads" | "contacts"; "entity_id": string; };

export type Condition = { "field": "status" | "source" | "priority" | "score" | "amount" | "value" | "company"; "operator"?: "equals" | "contains" | "gte"; "value": string; };

export type ConvertLead = { "create_deal"?: boolean; "deal_name"?: (string | null); "amount"?: (number | string | null); "contact_id"?: (string | null); "party_id"?: (string | null); };

export type DraftInput = { "recipient": string; "subject": string; "body": string; "entity_type"?: (string | null); "entity_id"?: (string | null); };

export type ErrorBody = { "code": string; "message": string; "details"?: Record<string, unknown>; };

export type ErrorResponse = { "error": ErrorBody; };

export type HTTPValidationError = { "detail"?: Array<ValidationError>; };

export type HealthResponse = { "status"?: "ok"; };

export type InviteAccept = { "token": string; "name": string; "password": string; };

export type InviteCreate = { "email": string; "role"?: "Admin" | "Sales Manager" | "Sales Rep" | "Support Agent" | "Read-only"; };

export type LeadMergeInput = { "target_id": string; "source_version"?: (number | null); "target_version"?: (number | null); };

export type LeadMergePair = { "target_id": string; "source_version"?: (number | null); "target_version"?: (number | null); "source_id": string; };

export type LoginRequest = { "email": string; "password": string; };

export type MessageInput = { "body": string; "internal"?: boolean; };

export type PasswordChange = { "current_password": string; "new_password": string; };

export type PipelineInput = { "name": string; "stages"?: Array<string>; };

export type PipelineStageInput = { "id"?: (string | null); "name": string; "probability": number; "category": "open" | "won" | "lost"; };

export type PipelineUpdate = { "name"?: (string | null); "stages"?: (Array<PipelineStageInput> | null); };

export type ProfileUpdate = { "name": string; };

export type SignupRequest = { "email": string; "password": string; "name": string; "company_name": string; };

export type StageChange = { "stage_id": string; "version"?: (number | null); "reason"?: string; };

export type TeamCreate = { "email": string; "password": string; "name": string; "role"?: "Admin" | "Sales Manager" | "Sales Rep" | "Support Agent" | "Read-only"; };

export type TeamUpdate = { "role"?: ("Admin" | "Sales Manager" | "Sales Rep" | "Support Agent" | "Read-only" | null); "is_active"?: (boolean | null); };

export type TemplateInput = { "name": string; "subject": string; "body": string; };

export type UserResponse = { "id": string; "org_id": string; "name": string; "email": string; "role": string; "company_name": string; "is_active"?: boolean; };

export type ValidationError = { "loc": Array<(string | number)>; "msg": string; "type": string; };

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
"GET /api/v1/automations/runs": { request: never; response: Record<string, unknown>; };
"GET /api/v1/notifications": { request: never; response: Record<string, unknown>; };
"POST /api/v1/notifications/{record_id}/read": { request: never; response: Record<string, unknown>; };
"GET /api/v1/email/templates": { request: never; response: Record<string, unknown>; };
"POST /api/v1/email/templates": { request: TemplateInput; response: Record<string, unknown>; };
"DELETE /api/v1/email/templates/{record_id}": { request: never; response: void; };
"PATCH /api/v1/email/templates/{record_id}": { request: TemplateInput; response: Record<string, unknown>; };
"GET /api/v1/email/messages": { request: never; response: Record<string, unknown>; };
"POST /api/v1/email/messages": { request: DraftInput; response: Record<string, unknown>; };
"POST /api/v1/email/messages/{record_id}/send": { request: never; response: unknown; };
"PATCH /api/v1/email/messages/{record_id}": { request: DraftInput; response: Record<string, unknown>; };
"DELETE /api/v1/email/messages/{record_id}": { request: never; response: void; };
"GET /api/v1/integrations": { request: never; response: Record<string, unknown>; };
"GET /api/v1/attachments": { request: never; response: Record<string, unknown>; };
"POST /api/v1/attachments": { request: never; response: Record<string, unknown>; };
"GET /api/v1/attachments/{attachment_id}/download": { request: never; response: unknown; };
"DELETE /api/v1/attachments/{attachment_id}": { request: never; response: void; };
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
