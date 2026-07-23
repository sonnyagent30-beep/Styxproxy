// Product Types
export type PlanType = 'ISP' | 'DC' | 'RESIDENTIAL' | 'MOBILE';
export type OrderStatus = 'pending' | 'paid' | 'fulfilled' | 'active' | 'expired' | 'cancelled' | 'refunded';
export type CredentialStatus = 'active' | 'expired' | 'revoked' | 'suspended';

export type ProductGroup = 'ISP' | 'RESIDENTIAL' | 'MOBILE' | 'DC';

export interface Product {
  plan_code: string;
  plan_type: PlanType;
  groupKey: ProductGroup;
  country: string;
  flag: string;
  price_ngn: number;
  quantity: number;
  duration_days: number;
  features: string[];
}

export interface Order {
  order_id: string;
  status: OrderStatus;
  plan_type?: PlanType;
  country?: string;
  amount_paid_ngn?: number;
  styxproxy_credential?: StyxproxyCredential;
  created_at: string;
  expires_at?: string;
}

export interface StyxproxyCredential {
  id: number;
  styxproxy_username: string;
  upstream_proxy_ip?: string;
  upstream_proxy_port: number;
  dante_port?: number;
  status: CredentialStatus;
  expires_at?: string;
}

export interface Customer {
  id: string;
  phone: string;
  name: string;
  blocked: boolean;
  total_orders: number;
  lifetime_value_ngn: number;
  created_at: string;
}

export interface PaymentInitiateResponse {
  payment_id: string;
  checkout_url: string;
  amount_ngn: number;
  expires_at: string;
}

export interface AdminStats {
  total_customers: number;
  active_orders: number;
  total_revenue_ngn: number;
  free_trials_today: number;
  active_credentials: number;
}

// Cart item — represents a single line in the buyer's cart.
// Always carries the user-selected country code so the order can be
// fulfilled against the correct geo, even when the plan is GLOBAL.
export interface CartItem {
  plan_code: string;        // either a real plan_code (ISP-UK-1) or a synthetic "{TYPE}-{COUNTRY}-{BASE}" code
  name: string;
  flag: string;             // country flag of the selected geo
  price_ngn: number;
  quantity: number;
  country_code: string;     // user-selected country code (always populated)
  plan_type: PlanType;
}

// API Response Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// Charon Admin Types
export interface CharonConversation {
  conversation_id: string;
  last_message: string;
  last_message_at: string;
  message_count: number;
  escalated: boolean;
}

export interface CharonLogEntry {
  ts: string;
  channel: string;
  conversation_id: string;
  user_message: string;
  response?: string;
  scenario_id?: string;
  escalated?: boolean;
  error?: string;
  tool_calls?: Array<{
    tool: string;
    params: Record<string, unknown>;
    result?: Record<string, unknown>;
    error?: string;
  }>;
}

// Learned Files Types
export interface LearnedFile {
  name: string;
  path: string;
  size: number;
  modified_at: string;
  editable?: boolean;
}

export interface LearnedFilesResponse {
  files: LearnedFile[];
}

export interface LearnContentResponse {
  name: string;
  path: string;
  content: string;
}

export interface LearnRequest {
  title: string;
  content: string;
  filename?: string;
}

export interface LearnResponse {
  ok: boolean;
  filepath?: string;
  message: string;
}

// ============ Charon Knowledge (admin reads + writes knowledge files) ============

export interface KnowledgeFile {
  name: string;
  path: string;
  size: number;
  modified_at: string;
  editable: boolean;
}

export interface AllKnowledgeFilesResponse {
  knowledge: KnowledgeFile[];
  learned: KnowledgeFile[];
}

export interface UpdateKnowledgeRequest {
  title: string;
  content: string;
}

export interface UpdateKnowledgeResponse {
  ok: boolean;
  message: string;
  name: string;
  path: string;
  size: number;
}

// ============ Charon Q/A Evaluation ============

export interface EvalQuestion {
  id: string;
  question: string;
  expected_keywords: string[];
  expected_scenario: string | null;
  source: string;
}

export interface EvalSetResponse {
  name: string;
  description: string;
  questions: EvalQuestion[];
}

export interface EvalResult {
  id: string;
  question: string;
  answer: string;
  passed: boolean;
  matched_keywords: string[];
  missing_keywords: string[];
  expected_scenario: string | null;
  matched_scenario: string | null;
  latency_ms: number;
}

export interface EvalRunResponse {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  results: EvalResult[];
  ran_at: string;
}

// ============== Admin Auth Types ==============
export type AdminRole = 'admin' | 'superadmin' | 'viewer';

export interface AdminSetupRequest {
  invite_code: string;
  email: string;
  password: string;
}

export interface AdminSetupTOTPResponse {
  temp_token: string;
  totp_secret: string;
  otpauth_url: string;
  backup_codes: string[];
  message: string;
}

export interface AdminSetupResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  email: string;
  role: string;
  totp_enabled: boolean;
  message: string;
}

export interface AdminLoginRequest {
  email: string;
  password: string;
  totp_code?: string;
}

export interface AdminLoginResponse {
  access_token: string;
  token_type: string;
  email: string;
  role: string;
  totp_enabled: boolean;
  expires_in: number;
}

export interface AdminMeResponse {
  email: string;
  role: string;
  totp_enabled: boolean;
  password_set_at?: string;
  failed_attempts: number;
  locked_until?: string;
  created_at: string;
  last_used?: string;
}

export interface AdminChangePasswordRequest {
  current_pin: string;
  new_pin: string;
}

export interface AdminChangePasswordResponse {
  message: string;
  pin_set_at: string;
}

export interface AdminChangeTOTPRequest {
  action: 'enable' | 'disable';
  totp_code?: string;
}

export interface AdminChangeTOTPResponse {
  totp_enabled: boolean;
  message: string;
}

// Admin Team Member
export interface AdminTeamMember {
  id: string;
  phone: string;
  role: AdminRole;
  totp_enabled: boolean;
  created_at: string;
  last_used?: string;
  failed_attempts: number;
  locked_until?: string;
}

export interface AdminInviteCreateRequest {
  email?: string;
  role: AdminRole;
  expires_in_hours?: number;
  max_uses?: number;
}

export interface AdminInviteCreateResponse {
  invite_code: string;
  email?: string;
  role: string;
  expires_at?: string;
  max_uses: number;
  created_by: string;
}

// ============== Blog Types ==============
export type PostStatus = 'draft' | 'pending' | 'approved' | 'published' | 'scheduled' | 'archived';

export interface BlogCategory {
  id: string;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  post_count?: number;
}

export interface BlogPost {
  id: string; // UUID
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  cover_image_url?: string;
  author: string; // admin phone/email
  status: PostStatus;
  submitted_at?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  scheduled_at?: string;
  published_at?: string;
  meta_description?: string;
  tags?: string[];
  featured?: boolean;
  view_count: number;
  created_at: string;
  updated_at: string;
  categories?: BlogCategory[];
}

export interface BlogPostCreate {
  title: string;
  content: string;
  excerpt?: string;
  cover_image_url?: string;
  meta_description?: string;
  tags?: string;
  scheduled_at?: string;
  featured?: boolean;
  category_ids?: string[];
}

export interface BlogPostUpdate extends Partial<BlogPostCreate> {
  status?: PostStatus;
}

export interface BlogPostsResponse {
  posts: BlogPost[];
  pagination: {
    page: number;
    limit: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface BlogCategoriesResponse {
  categories: BlogCategory[];
  pagination: {
    page: number;
    limit: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// ============== Channel Feature Flags ==============
export interface ChannelConfig {
  enabled: boolean;
  url: string;
}

export interface ChannelFeatureFlags {
  telegram: ChannelConfig;
  whatsapp: ChannelConfig;
}

// ============== Plans (Admin) ==============
export interface Plan {
  id: number;
  plan_code: string;
  plan_type: string;
  country: string;
  price_ngn: number;
  quantity: number;
  duration_days: number;
  features: Record<string, unknown> | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface PlanCreate {
  plan_code: string;
  plan_type: string;
  country: string;
  price_ngn: number;
  quantity: number;
  duration_days: number;
  features?: Record<string, unknown>;
  is_active: boolean;
  sort_order: number;
}

export interface PlanUpdate {
  price_ngn?: number;
  quantity?: number;
  duration_days?: number;
  features?: Record<string, unknown>;
  is_active?: boolean;
  sort_order?: number;
}

// ============== Contact Submissions ==============
export interface ContactSubmission {
  id: string;
  name: string;
  email: string;
  message: string;
  phone?: string;
  tx_ref?: string;
  status: 'pending' | 'replied' | 'closed';
  admin_notes?: string;
  created_at: string;
}

export interface ContactSubmissionsResponse {
  data: ContactSubmission[];
  total: number;
}

// ============== Support Threads ==============
export type SupportThreadStatus = 'open' | 'closed';

export interface SupportMessage {
  id: string;
  thread_id: string;
  direction: 'inbound' | 'outbound';
  from_email: string;
  to_email: string;
  subject: string;
  body_text?: string;
  body_html?: string;
  resend_id?: string;
  in_reply_to?: string;
  references?: string;
  created_at: string;
}

export interface SupportThread {
  id: string;
  customer_email: string;
  customer_name?: string | null;
  subject: string;
  status: SupportThreadStatus;
  order_id?: string | null;
  resend_last_message_id?: string | null;
  last_message_at: string;
  created_at: string;
  messages?: SupportMessage[];
}

export interface SupportThreadDetail extends SupportThread {
  messages: SupportMessage[];
}

export interface SupportThreadsResponse {
  threads: SupportThread[];
  pagination: {
    page: number;
    limit: number;
    total_items?: number;
    total?: number;
    total_pages?: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// ============== Charon Escalations ==============
export interface Escalation {
  id: string;
  conversation_id: string;
  customer_email?: string;
  customer_phone?: string;
  customer_message: string;
  history_summary?: string;
  status: 'pending' | 'reviewed' | 'closed';
  admin_notes?: string;
  resolved_at?: string;
  created_at: string;
}

export interface EscalationsResponse {
  data: Escalation[];
  total: number;
}

// ============== Admin Audit Log ==============
export interface AdminAuditLog {
  id: string;
  admin_email: string;
  action: string;
  resource: string;
  ip_address: string;
  created_at: string;
}

export interface AdminAuditLogResponse {
  data: AdminAuditLog[];
  pagination: {
    page: number;
    limit: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// ============== Admin (Superadmin view) ==============
export interface Admin {
  id: string;
  email: string;
  phone: string;
  role: AdminRole;
  totp_enabled: boolean;
  locked: boolean;
  created_at: string;
  last_used?: string;
}

export interface AdminCreateRequest {
  email: string;
  phone: string;
  password: string;
  role: AdminRole;
}

export interface AdminRoleUpdateRequest {
  email: string;
  role: AdminRole;
}

// ============== Provider Costs ==============
export interface ProviderCost {
  provider_name: string;
  total_orders: number;
  total_cost_usd: number;
  margin_estimate_percent: number;
}

export interface ProviderCostsResponse {
  providers: ProviderCost[];
  note?: string;
}

// ============== System Settings ==============
export interface SystemSetting {
  key: string;
  value: string;
  updated_at: string;
}

export interface SystemSettingsResponse {
  settings: SystemSetting[];
}

// ============== Global Search ==============
export interface GlobalSearchResult {
  id: string;
  type: 'customer' | 'order' | 'ticket' | 'contact_submission';
  title: string;
  subtitle: string;
  url?: string;
}

export interface GlobalSearchResponse {
  results: GlobalSearchResult[];
  total: number;
}

// ============== Metrics Overview ==============
export interface MetricsOverview {
  total_customers: number;
  total_orders: number;
  total_revenue_usd: number;
  active_credentials: number;
}
