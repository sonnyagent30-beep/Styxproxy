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
  bun_username: string;
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
    total: number;
    total_pages: number;
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
  filepath: string;
  message: string;
}

// ============== Admin Auth Types ==============
export type AdminRole = 'admin' | 'superadmin' | 'viewer';

export interface AdminSetupRequest {
  invite_code: string;
  pin: string;
  totp_code?: string;
}

export interface AdminSetupResponse {
  admin_phone: string;
  role: string;
  totp_enabled: boolean;
  message: string;
}

export interface AdminLoginRequest {
  admin_phone: string;
  pin: string;
  totp_code?: string;
}

export interface AdminLoginResponse {
  access_token: string;
  token_type: string;
  admin_phone: string;
  role: string;
  totp_enabled: boolean;
  expires_in: number;
}

export interface AdminMeResponse {
  admin_phone: string;
  role: string;
  totp_enabled: boolean;
  pin_set_at?: string;
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
export interface BlogPost {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  cover_image?: string;
  author: string;
  published: boolean;
  published_at?: string;
  created_at: string;
  updated_at: string;
  tags?: string[];
}

export interface BlogPostCreate {
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  cover_image?: string;
  author?: string;
  published?: boolean;
  tags?: string[];
}

export interface BlogPostUpdate extends Partial<BlogPostCreate> {}

export interface BlogPostsResponse {
  posts: BlogPost[];
  total: number;
  page: number;
  limit: number;
}
