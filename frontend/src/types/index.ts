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
  // Sprint 13: per-GB pricing + city picker. Populated from CatalogTemplate.
  price_per_gb?: number | null;
  min_gb?: number | null;
  max_gb?: number | null;
  gb_tiers?: number[] | null;
  supports_city?: boolean;
  cities?: { [country_code: string]: CatalogCity[] };
}

export interface Order {
  order_id: string;
  tx_ref?: string;
  status: OrderStatus | string;
  plan_type?: PlanType | string;
  plan_code?: string;
  country?: string;
  quantity?: number;
  amount_paid_ngn?: number;
  currency?: string;
  customer_phone?: string;
  customer_name?: string;
  customer_email?: string;
  styxproxy_credential?: StyxproxyCredential;
  created_at?: string;
  fulfilled_at?: string;
  expires_at?: string;
  is_renewable?: boolean;
  rotation_count?: number;
  max_rotations?: number;
  notes?: string;
  refund_requested?: boolean;
  refund_reason?: string;
  refunded_at?: string;
  inflight?: boolean;
}

export interface StyxproxyCredential {
  id: string;
  bun_username?: string;
  styxproxy_username?: string;
  provider_username?: string;
  provider_password?: string;
  provider_name?: string;
  pool_type?: string;
  customer_phone?: string;
  order_id?: string | number;
  protocol?: string;
  upstream_proxy_ip?: string;
  upstream_proxy_port: number;
  styxproxy_password?: string;
  dante_port?: number;
  status: CredentialStatus | string;
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
  plan_counts: Record<string, number>;
}

// Cart item — represents a single line in the buyer's cart.
// Always carries the user-selected country code so the order can be
// fulfilled against the correct geo, even when the plan is GLOBAL.
export interface CartItem {
  plan_code: string;        // either a real plan_code (ISP-UK-1) or a synthetic "{TYPE}-{COUNTRY}-{BASE}" code
  name: string;
  flag: string;             // country flag of the selected geo
  price_ngn: number;        // base price for residential/mobile is per-GB; for DC/ISP is per-IP
  quantity: number;         // for DC/ISP = number of IPs; for residential/mobile = IP proxy count (legacy compat)
  country_code: string;     // user-selected country code (always populated)
  plan_type: PlanType;
  // Sprint 13: per-GB pricing + city picker support
  quantity_gb?: number;     // GB amount for residential/mobile (preferred over quantity for those plan types)
  city_id?: number | null;  // null = random from country pool
  city_name?: string | null;
  price_per_gb?: number;    // DB-canonical per-GB price (residential/mobile only)
  min_gb?: number;
  max_gb?: number;
  gb_tiers?: number[];
  supports_city?: boolean;
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
  email: string;
  role: string;
  totp_enabled: boolean;
  expires_in: number;
  message?: string;
}

export interface AdminSetupCheckInviteResponse {
  valid: boolean;
  email?: string | null;
  role?: string | null;
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
  email?: string;
  admin_phone?: string;
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
  admin_phone?: string;
  email?: string;
  phone?: string;
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

export interface AdminInvite {
  invite_code: string;
  email: string | null;
  role: string;
  max_uses: number;
  uses_count: number;
  expires_at: string | null;
  used_at: string | null;
  used_by: string | null;
  created_at: string;
}

export interface AdminInvitesListResponse {
  invites: AdminInvite[];
  total: number;
}

export interface OrderHistoryEntry {
  ts: string;
  event: string;
  details?: Record<string, unknown>;
}

export interface OrderDetail extends Order {
  customer?: Customer;
  credentials?: StyxproxyCredential[];
  history?: OrderHistoryEntry[];
}

export interface CredentialDetail extends StyxproxyCredential {
  rotation_count?: number;
  max_rotations?: number;
  last_rotated_at?: string | null;
  last_used_at?: string | null;
  usage_log?: Array<{ ts: string; ip?: string; bytes_in?: number; bytes_out?: number }>;
  customer_phone?: string;
  provider_username?: string;
  provider_password?: string;
  provider_name?: string;
  pool_type?: string;
  protocol?: string;
  order_id?: string | number;
}

export interface CharonEscalation {
  id: string;
  scenario_id?: string | null;
  tx_ref?: string | null;
  summary: string;
  reason?: string | null;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  created_at: string;
  updated_at?: string | null;
  assignee?: string | null;
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
  price_per_gb: number | null;
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
  price_per_gb?: number;
  quantity: number;
  duration_days: number;
  features?: Record<string, unknown>;
  is_active: boolean;
  sort_order: number;
}

export interface PlanUpdate {
  price_ngn?: number;
  price_per_gb?: number;
  quantity?: number;
  duration_days?: number;
  features?: Record<string, unknown>;
  is_active?: boolean;
  sort_order?: number;
}

// ============== Plan Settings (Admin) ==============
export interface PlanSettingValue {
  price_per_gb?: number | null;
  price_per_ip?: number | null;
  available_countries: string[];
  gb_tiers?: number[] | null;      // integer array, not string
  supports_city?: boolean | null;   // null for ISP/DC
  rotation_modes?: string[] | null; // null for RESIDENTIAL/MOBILE
}

export interface PlanSetting {
  id: number;
  plan_type: string;
  setting_key: string;
  setting_value: PlanSettingValue;
  is_active: boolean;
}

// ============== Country Plan Types (Sprint 27) ==============
// GET /api/admin/countries → { countries: CountryCPT[], total: number }
export interface CPTPlanTypeStatus {
  plan_type: string;
  enabled: boolean;
  price_per_ip: number | null;
  price_per_gb: number | null;
  provider_id: number | null;
}

export interface CountryCPT {
  code: string;
  name: string;
  flag_emoji: string;
  region: string;
  enabled_plan_types: string[]; // simplified list from GET /countries
  plan_types?: Record<string, CPTPlanTypeStatus>; // full detail from GET /countries/:code
}

export interface CountryCPTDetail extends CountryCPT {
  plan_types: Record<string, CPTPlanTypeStatus>;
}

export interface CPTUpdateResult {
  country_code: string;
  plan_type: string;
  enabled: boolean;
  price_per_ip: number | null;
  price_per_gb: number | null;
  provider_id: number | null;
}

// ============== Catalog Templates (Admin) ==============
export interface CatalogTemplate {
  plan_type: string;
  available_countries: string[];
  default_countries?: string[];
  updated_at: string;
}

// ============== Contact Submissions ==============
export interface ContactSubmission {
  id: string;
  name: string;
  email: string;
  message: string;
  phone?: string;
  admin_phone?: string;
  tx_ref?: string;
  subject?: string;
  status: 'pending' | 'replied' | 'closed' | 'in_progress' | 'resolved';
  admin_notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface ContactSubmissionsResponse {
  data: ContactSubmission[];
  total: number;
  submissions?: ContactSubmission[];
  pagination?: { page: number; limit: number; total: number; has_next: boolean };
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
  conversation_id?: string;
  customer_email?: string;
  customer_phone?: string;
  customer_message: string;
  history_summary?: string;
  status: 'pending' | 'reviewed' | 'closed' | 'resolved';
  admin_notes?: string;
  resolved_at?: string;
  created_at: string;
  tx_ref?: string;
  summary?: string;
}

export interface EscalationsResponse {
  data: Escalation[];
  escalations?: Escalation[];
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

// ============== Admin Permissions (Sprint 14) ==============
export interface AdminPermission {
  code: string;
  description: string;
  is_sensitive: boolean;
}

export interface AdminPermissionWithGrant extends AdminPermission {
  granted: boolean;
}

export interface AdminPermissionsByCategory {
  [category: string]: AdminPermissionWithGrant[];
}

export interface AdminMyPermissionsResponse {
  email: string;
  role: AdminRole;
  permission_count: number;
  permissions_by_category: AdminPermissionsByCategory;
}

export interface AdminAllPermissionsResponse {
  total: number;
  categories: string[];
  permissions_by_category: {
    [category: string]: AdminPermission[];
  };
}

// ============== TOTP Step-up (Sprint 14) ==============
export interface AdminTotpStatusResponse {
  totp_enabled: boolean;
  step_upped: boolean;
  step_up_expires_at: string | null;
  step_up_window_seconds: number;
}

export interface AdminTotpElevateRequest {
  totp_code: string;
  remember_device: boolean;
}

export interface AdminTotpElevateResponse {
  elevated: boolean;
  expires_at: string;
  window_seconds: number;
  session_token?: string;
  session_token_header?: string;
}

export interface AdminGrantPermissionRequest {
  admin_email: string;
  permission_code: string;
}

export interface AdminGrantPermissionResponse {
  granted: boolean;
  admin_email: string;
  permission_code: string;
  permission_is_sensitive: boolean;
}

export interface AdminRevokePermissionResponse {
  revoked: boolean;
  admin_email: string;
  permission_code: string;
}

export interface RlsPolicyResponse {
  id: number;
  table_name: string;
  policy_name: string;
  policy_enabled: boolean;
  description?: string | null;
  notes?: string | null;
  using_clause?: string | null;
  with_check?: string | null;
  role_name?: string | null;
  policy_status?: string | null;
  created_by?: string | null;
  applied_at?: string | null;
  rolled_back_at?: string | null;
  last_audit?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RlsPolicyListResponse {
  policies: RlsPolicyResponse[];
  total: number;
  enabled_count: number;
  not_started_count: number;
}

export interface RlsPolicyToggleRequest {
  table_name: string;
  enable: boolean;
  using_clause?: string;
  with_check?: string;
  notes?: string;
}

export interface RlsPolicyToggleResponse extends RlsPolicyResponse {
  pg_rls_state: string;
  pg_policy_count: number;
  policies?: string[];
  app_policy?: string;
  admin_policy?: string | null;
}

export interface RlsRolloutPhase {
  phase: string;
  table_name: string;
  rationale: string;
  risk: 'low' | 'medium' | 'high';
  completed: boolean;
  enabled_at: string | null;
}

export interface RlsRolloutPlanResponse {
  phases: RlsRolloutPhase[];
  next_phase: string | null;
  connection_string_pinned: boolean;
}

export interface RlsSafeStatus {
  total_tables: number;
  rls_enabled_count: number;
  rls_disabled_count: number;
  policies: RlsPolicyResponse[];
  bypass_role_exists: boolean;
  current_user_role: string;
  bypass_role_attr_present: boolean;
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
  orders_today: number;
  orders_this_week: number;
  revenue_today_ngn: number;
  revenue_this_week_ngn: number;
  revenue_this_month_ngn: number;
  active_proxies: number;
  churned_today: number;
  escalations_open: number;
  support_threads_open: number;
  contact_submissions_open: number;
  charon_llm_status: string;
  charon_total_requests: number;
  charon_escalated_replies: number;
  charon_llm_errors: number;
  charon_tokens_used_total: number;
}

// ============== Catalog (BE-driven) ==============
// Matches /api/catalog — returns plan templates from the DB, not hardcoded FE.
export type CatalogRotationMode = 'rotating' | 'static';
export type CatalogPlanType = 'datacenter' | 'residential' | 'mobile' | 'isp';

export interface CatalogVariant {
  plan_code: string;
  plan_type: CatalogPlanType;
  country: string;          // ISO alpha-2 (GB, US, DE, etc.)
  rotation_mode: CatalogRotationMode;
  price_ngn: number;
  quantity: number;          // GB
  duration_days: number;
  is_active: boolean;
}

export interface CatalogCity {
  id: number;
  city_name: string;
  state_code?: string | null;
  isp_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface CatalogTemplate {
  plan_type: CatalogPlanType;
  rotation_mode_options: CatalogRotationMode[];
  available_countries: string[];
  base_quantity_gb: number;
  base_price_ngn: number;             // legacy per-IP price (DC/ISP)
  base_price_per_gb?: number | null; // per-GB (residential/mobile)
  base_price_per_ip?: number | null; // per-IP (DC/ISP)
  min_gb?: number | null;            // minimum GB customer can buy
  max_gb?: number | null;            // maximum GB customer can buy
  gb_tiers?: number[] | null;        // suggested GB tiers
  supports_city: boolean;            // residential/mobile only
  cities: { [country_code: string]: CatalogCity[] };  // country_code -> cities
  duration_days: number;
  static_price_multiplier: number;
  supports_country_change: boolean;
  description: string;
  variants: CatalogVariant[];
}

export interface CatalogResponse {
  templates: CatalogTemplate[];
}

// ============== Payment Status Polling ==============
// Matches GET /api/orders/{order_id}/status
export type PaymentNextAction =
  | 'poll'                          // keep polling
  | 'redirect_to_proxy_details'     // success — credentials ready
  | 'show_retry'                   // payment failed — show retry button
  | 'show_failure'                 // order cancelled/expired
  | 'provider_down';                // upstream proxy provider unavailable

export interface PaymentStatusCredential {
  credential_id: number;
  styxproxy_username: string;
  styxproxy_password: string;
  proxy_host: string;
  proxy_port_socks5: number;
  proxy_port_http: number;
  protocol: string;
  assigned_static_ip?: string | null;
  curl_socks5_example: string;
  curl_http_example: string;
  python_socks5_example: string;
  manage_url: string;
}

export interface OrderPaymentStatus {
  order_id: string;
  plan_type: string;
  plan_code: string;
  country: string;
  rotation_mode: string;
  quantity_gb: number;
  duration_days: number;
  amount_paid_ngn: number;
  currency: string;
  order_status: OrderStatus;
  payment_status: 'pending' | 'paid' | 'failed' | string;
  payment_reference: string | null;
  created_at: string;
  paid_at: string | null;
  fulfilled_at: string | null;
  expires_at: string | null;
  // Driver of the frontend UX
  next_action: PaymentNextAction;
  next_action_url?: string | null;
  user_message: string;
  credential?: PaymentStatusCredential | null;
}

// Analytics types
export interface FunnelStage {
  stage: string;
  count: number;
  conversion_rate: number | null;
}

export interface FunnelData {
  total_events: number;
  stages: FunnelStage[];
  period_days: number;
}

export interface AnalyticsEvent {
  id: number;
  event_name: string;
  session_id: string | null;
  customer_phone: string | null;
  country: string | null;
  plan_code: string | null;
  channel: string;
  meta: Record<string, unknown>;
  created_at: string;
}
