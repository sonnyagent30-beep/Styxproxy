import type { 
  Product, 
  Order, 
  PaymentInitiateResponse, 
  AdminStats,
  Customer,
  ApiResponse,
  PaginatedResponse,
  StyxproxyCredential,
  CharonConversation,
  CharonLogEntry,
  LearnedFile,
  LearnedFilesResponse,
  LearnContentResponse,
  LearnRequest,
  LearnResponse,
  AdminLoginRequest,
  AdminLoginResponse,
  AdminSetupRequest,
  AdminSetupTOTPResponse,
  AdminSetupResponse,
  AdminMeResponse,
  AdminTeamMember,
  AdminInviteCreateRequest,
  AdminInviteCreateResponse,
  BlogPost,
  BlogPostCreate,
  BlogPostUpdate,
  BlogPostsResponse,
  BlogCategory,
  BlogCategoriesResponse,
  ChannelFeatureFlags,
  Plan,
  PlanCreate,
  PlanUpdate,
  ContactSubmission,
  ContactSubmissionsResponse,
  Escalation,
  EscalationsResponse,
  SupportThread,
  SupportThreadDetail,
  SupportThreadsResponse,
  SupportThreadStatus,
  Admin,
  AdminCreateRequest,
  AdminRoleUpdateRequest,
  AdminAuditLog,
  AdminAuditLogResponse,
  ProviderCost,
  ProviderCostsResponse,
  SystemSetting,
  SystemSettingsResponse,
  GlobalSearchResult,
  GlobalSearchResponse,
  MetricsOverview,
  AdminRole,
} from '@/types';

// Admin API calls go through Next.js middleware (src/middleware.ts)
// which rewrites /api/admin/* → https://api.styxproxy.com/api/admin/*
const API_BASE_URL = ''; // relative — browser always talks to same origin

class ApiClient {
  private baseUrl: string;
  private adminToken: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // Store admin token
  setAdminToken(token: string | null) {
    this.adminToken = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('admin_token', token);
      } else {
        localStorage.removeItem('admin_token');
      }
    }
  }

  getAdminToken(): string | null {
    if (this.adminToken) return this.adminToken;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('admin_token');
    }
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      // Add admin token to headers if available
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
      };
      
      const adminToken = this.getAdminToken();
      // Attach Bearer token to ALL admin API endpoints
      // (some start with '/admin/...' and others with '/api/admin/...')
      if (adminToken && (endpoint.startsWith('/admin') || endpoint.startsWith('/api/admin'))) {
        headers['Authorization'] = `Bearer ${adminToken}`;
      }

      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { 
          error: errorData.detail || `HTTP error ${response.status}` 
        };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return { 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      };
    }
  }

  // Products
  async getProducts(): Promise<ApiResponse<Product[]>> {
    return this.request<Product[]>('/products');
  }

  // Orders
  async createOrder(planCode: string, country: string, quantity: number = 1): Promise<ApiResponse<Order>> {
    return this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify({
        plan_code: planCode,
        country,
        quantity,
      }),
    });
  }

  async getOrder(orderId: string): Promise<ApiResponse<Order>> {
    return this.request<Order>(`/orders/${orderId}`);
  }

  async cancelOrder(orderId: string, reason: string): Promise<ApiResponse<{ order_id: string; status: string; refund_processed: boolean }>> {
    return this.request(`/orders/${orderId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async reportDeadProxy(orderId: string, screenshotUrl: string, issueDescription: string): Promise<ApiResponse<{ order_id: string; ban_reported: boolean; status: string; replacement_estimate_hours: number }>> {
    return this.request(`/orders/${orderId}/report-dead`, {
      method: 'POST',
      body: JSON.stringify({
        screenshot_url: screenshotUrl,
        issue_description: issueDescription,
      }),
    });
  }

  // Payments
  async initiatePayment(planCode: string, quantity: number, customerPhone: string): Promise<ApiResponse<PaymentInitiateResponse>> {
    return this.request<PaymentInitiateResponse>('/payments/initiate', {
      method: 'POST',
      body: JSON.stringify({
        plan_code: planCode,
        quantity,
        customer_phone: customerPhone,
      }),
    });
  }

  // Trials
  async claimTrial(disclaimerAccepted: boolean): Promise<ApiResponse<{ trial_id: number; status: string; styxproxy_credential: { bun_username: string; upstream_proxy_ip: string; upstream_proxy_port: number; expires_at: string } }>> {
    return this.request('/trials/claim', {
      method: 'POST',
      body: JSON.stringify({ disclaimer_accepted: disclaimerAccepted }),
    });
  }

  // Admin
  async getAdminStats(): Promise<ApiResponse<AdminStats>> {
    return this.request<AdminStats>('/api/admin/stats');
  }

  async getOrders(page: number = 1, limit: number = 20): Promise<ApiResponse<PaginatedResponse<Order>>> {
    return this.request<PaginatedResponse<Order>>(`/admin/orders?page=${page}&limit=${limit}`);
  }

  async getCustomers(page: number = 1, limit: number = 20): Promise<ApiResponse<PaginatedResponse<Customer>>> {
    return this.request<PaginatedResponse<Customer>>(`/admin/customers?page=${page}&limit=${limit}`);
  }

  async blockCustomer(customerId: string, reason: string): Promise<ApiResponse<{ blocked: boolean }>> {
    return this.request(`/admin/customers/${customerId}/block`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  // Charon Admin
  async getCharonConversations(page: number = 1, limit: number = 20): Promise<ApiResponse<{ conversations: CharonConversation[]; total: number; limit: number; offset: number }>> {
    return this.request(`/charon/conversations?page=${page}&limit=${limit}`);
  }

  async getCharonLogs(
    limit: number = 100,
    offset: number = 0,
    conversationId?: string,
    channel?: string,
    escalated?: boolean,
    dateFrom?: string,
    dateTo?: string
  ): Promise<ApiResponse<{ logs: CharonLogEntry[]; total: number; limit: number; offset: number }>> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (conversationId) params.append('conversation_id', conversationId);
    if (channel) params.append('channel', channel);
    if (escalated !== undefined) params.append('escalated', String(escalated));
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    return this.request(`/charon/logs?${params.toString()}`);
  }

  getCharonStreamUrl(): string {
    return `${this.baseUrl}/charon/stream`;
  }

  // Learned Files Management
  async getLearnedFiles(): Promise<ApiResponse<LearnedFilesResponse>> {
    return this.request<LearnedFilesResponse>('/api/admin/charon/learned');
  }

  async getLearnedFileContent(filename: string): Promise<ApiResponse<LearnContentResponse>> {
    return this.request<LearnContentResponse>(`/admin/charon/learned/${encodeURIComponent(filename)}`);
  }

  async deleteLearnedFile(filename: string): Promise<ApiResponse<{ ok: boolean; message: string }>> {
    return this.request('/api/admin/charon/learned', {
      method: 'DELETE',
      body: JSON.stringify({ filename }),
    });
  }

  async learnContent(data: LearnRequest): Promise<ApiResponse<LearnResponse>> {
    return this.request<LearnResponse>('/charon/learn', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Health
  async healthCheck(): Promise<ApiResponse<{ status: string; version: string; database: string; timestamp: string }>> {
    return this.request('/health');
  }

  // ============== Admin Auth ==============
  
  // Check if admin is already set up
  async checkAdminSetupStatus(): Promise<ApiResponse<{ setup_required: boolean }>> {
    return this.request('/api/admin/auth/status');
  }

  // Step 1: check if invite code is valid
  async checkInviteCode(code: string): Promise<ApiResponse<{ valid: boolean; email?: string; role?: string }>> {
    return this.request('/api/admin/auth/setup/check', {
      method: 'POST',
      body: JSON.stringify({ invite_code: code }),
    });
  }

  // Initial admin setup — step 2: submit credentials → returns TOTP secret + backup codes
  async setupAdmin(data: AdminSetupRequest): Promise<ApiResponse<AdminSetupTOTPResponse>> {
    return this.request<AdminSetupTOTPResponse>('/api/admin/auth/setup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Complete admin setup — step 2: verify TOTP code
  async setupAdminComplete(data: { temp_token: string; totp_code: string }): Promise<ApiResponse<AdminSetupResponse>> {
    return this.request<AdminSetupResponse>('/api/admin/auth/setup/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Admin login (email-based)
  async adminLogin(data: AdminLoginRequest): Promise<ApiResponse<AdminLoginResponse>> {
    return this.request<AdminLoginResponse>('/api/admin/auth/login/email', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Admin setup step 1: invite + credentials → TOTP secret
  async adminSetupStep1(data: AdminSetupRequest): Promise<ApiResponse<AdminSetupTOTPResponse>> {
    return this.request<AdminSetupTOTPResponse>('/api/admin/auth/setup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Admin setup step 2: TOTP code → access token
  async adminSetupStep2(data: { temp_token: string; totp_code: string }): Promise<ApiResponse<AdminSetupResponse>> {
    return this.request<AdminSetupResponse>('/api/admin/auth/setup/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Get current admin info
  async getAdminMe(): Promise<ApiResponse<AdminMeResponse>> {
    return this.request<AdminMeResponse>('/api/admin/auth/me');
  }

  // Admin logout
  async adminLogout(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/api/admin/auth/logout', {
      method: 'POST',
    });
  }

  // Get admin team (SuperAdmin only)
  async getAdminTeam(): Promise<ApiResponse<{ members: AdminTeamMember[] }>> {
    return this.request('/api/admin/auth/team');
  }

  // Create admin invite (SuperAdmin only)
  async createAdminInvite(data: AdminInviteCreateRequest): Promise<ApiResponse<AdminInviteCreateResponse>> {
    return this.request<AdminInviteCreateResponse>('/api/admin/auth/invite', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Change admin PIN
  async changeAdminPin(currentPin: string, newPin: string): Promise<ApiResponse<{ message: string }>> {
    return this.request('/api/admin/auth/password', {
      method: 'POST',
      body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
    });
  }

  // Toggle TOTP
  async toggleAdminTOTP(action: 'enable' | 'disable', totpCode?: string): Promise<ApiResponse<{ totp_enabled: boolean; message: string }>> {
    return this.request('/api/admin/auth/totp', {
      method: 'POST',
      body: JSON.stringify({ action, totp_code: totpCode }),
    });
  }

  // ============== Blog ==============

  // Get all published blog posts (public) - supports optional tag filter
  async getBlogPosts(page: number = 1, limit: number = 10, tag?: string, category?: string): Promise<ApiResponse<BlogPostsResponse>> {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (tag) params.set('tag', tag);
    if (category) params.set('category', category);
    return this.request<BlogPostsResponse>(`/api/blog/posts?${params.toString()}`);
  }

  // Get single blog post by slug (public)
  async getBlogPost(slug: string): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/api/blog/posts/${slug}`);
  }

  // Get all blog posts for admin (includes unpublished)
  async getAdminBlogPosts(page: number = 1, limit: number = 20): Promise<ApiResponse<BlogPostsResponse>> {
    return this.request<BlogPostsResponse>(`/api/admin/blog/posts?page=${page}&limit=${limit}`);
  }

  // Create blog post (admin)
  async createBlogPost(data: BlogPostCreate): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>('/api/admin/blog/posts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Update blog post (admin)
  async updateBlogPost(id: string, data: BlogPostUpdate): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/api/admin/blog/posts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Delete blog post (admin)
  async deleteBlogPost(id: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/admin/blog/posts/${id}`, {
      method: 'DELETE',
    });
  }

  // Blog post workflow actions
  async publishPost(id: string): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/api/admin/blog/posts/${id}/publish`, {
      method: 'POST',
    });
  }

  async unpublishPost(id: string): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/api/admin/blog/posts/${id}/unpublish`, {
      method: 'POST',
    });
  }

  async approvePost(id: string): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/api/admin/blog/posts/${id}/approve`, {
      method: 'POST',
    });
  }

  async rejectPost(id: string, reason: string): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/api/admin/blog/posts/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  // ============== Blog Categories ==============

  // Get all categories (public)
  async getBlogCategories(): Promise<ApiResponse<BlogCategoriesResponse>> {
    return this.request<BlogCategoriesResponse>('/api/blog/categories');
  }

  // Get single category (public)
  async getBlogCategory(slug: string): Promise<ApiResponse<BlogCategory>> {
    return this.request<BlogCategory>(`/api/blog/categories/${slug}`);
  }

  // Get all categories for admin
  async getAdminBlogCategories(): Promise<ApiResponse<BlogCategoriesResponse>> {
    return this.request<BlogCategoriesResponse>('/api/blog/admin/categories');
  }

  // Create category (admin)
  async createBlogCategory(data: { name: string; description?: string; color?: string }): Promise<ApiResponse<BlogCategory>> {
    return this.request<BlogCategory>('/api/blog/admin/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Update category (admin)
  async updateBlogCategory(id: string, data: { name?: string; description?: string; color?: string }): Promise<ApiResponse<BlogCategory>> {
    return this.request<BlogCategory>(`/api/blog/admin/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Delete category (admin)
  async deleteBlogCategory(id: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/blog/admin/categories/${id}`, {
      method: 'DELETE',
    });
  }

  // ============== Channel Feature Flags ==============

  // Get channel feature flags (public - no auth required)
  async getChannelFeatureFlags(): Promise<ApiResponse<ChannelFeatureFlags>> {
    return this.request<ChannelFeatureFlags>('/api/admin/features/channels');
  }

  // Update channel feature flags (admin only)
  async updateChannelFeatureFlags(data: ChannelFeatureFlags): Promise<ApiResponse<ChannelFeatureFlags>> {
    return this.request<ChannelFeatureFlags>('/api/admin/features/channels', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ============== Plans (Admin) ==============

  async getPlans(page: number = 1, limit: number = 20, filters?: {
    plan_type?: string;
    country?: string;
    is_active?: boolean;
  }): Promise<ApiResponse<PaginatedResponse<Plan>>> {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (filters?.plan_type) params.append('plan_type', filters.plan_type);
    if (filters?.country) params.append('country', filters.country);
    if (filters?.is_active !== undefined) params.append('is_active', String(filters.is_active));
    return this.request<PaginatedResponse<Plan>>(`/api/admin/plans?${params.toString()}`);
  }

  async getPlan(planId: number): Promise<ApiResponse<Plan>> {
    return this.request<Plan>(`/api/admin/plans/${planId}`);
  }

  async createPlan(data: PlanCreate): Promise<ApiResponse<Plan>> {
    return this.request<Plan>('/api/admin/plans', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePlan(planId: number, data: PlanUpdate): Promise<ApiResponse<Plan>> {
    return this.request<Plan>(`/api/admin/plans/${planId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deletePlan(planId: number): Promise<ApiResponse<{ status: string; plan_id: number }>> {
    return this.request(`/api/admin/plans/${planId}`, {
      method: 'DELETE',
    });
  }

  // ============== Support Threads =============

  async getSupportThreads(status?: string, page = 1, limit = 20): Promise<ApiResponse<SupportThreadsResponse>> {
    let url = `/api/admin/support/threads?page=${page}&limit=${limit}`;
    if (status && status !== 'all') url += `&status=${status}`;
    return this.request<SupportThreadsResponse>(url);
  }

  async getSupportThread(threadId: string): Promise<ApiResponse<SupportThreadDetail>> {
    return this.request<SupportThreadDetail>(`/api/admin/support/threads/${threadId}`);
  }

  async replySupportThread(threadId: string, replyHtml: string, adminName = 'Dannion'): Promise<ApiResponse<{ status: string; message_id: string; thread_id: string }>> {
    return this.request(`/api/admin/support/threads/${threadId}/reply`, {
      method: 'POST',
      body: JSON.stringify({ reply_html: replyHtml, admin_name: adminName }),
    });
  }

  async closeSupportThread(threadId: string): Promise<ApiResponse<{ status: string }>> {
    return this.request(`/api/admin/support/threads/${threadId}/close`, { method: 'POST' });
  }

  async reopenSupportThread(threadId: string): Promise<ApiResponse<{ status: string }>> {
    return this.request(`/api/admin/support/threads/${threadId}/reopen`, { method: 'POST' });
  }

  // ============== Contact Submissions =============

  async getContactSubmissions(status?: string, page = 1, limit = 20): Promise<ApiResponse<ContactSubmissionsResponse>> {
    let url = `/api/admin/contact-submissions?page=${page}&limit=${limit}`;
    if (status) url += `&status=${status}`;
    return this.request<ContactSubmissionsResponse>(url);
  }

  async replyContactSubmission(id: string, adminNotes: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request(`/api/admin/contact-submissions/${id}/reply`, {
      method: 'POST',
      body: JSON.stringify({ admin_notes: adminNotes }),
    });
  }

  async updateContactSubmission(id: string, status: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request(`/api/admin/contact-submissions/${id}?status=${status}`, {
      method: 'PATCH',
    });
  }

  // ============== Charon Escalations =============

  async getEscalations(status?: string, page = 1, limit = 20): Promise<ApiResponse<EscalationsResponse>> {
    let url = `/api/admin/escalations?page=${page}&limit=${limit}`;
    if (status) url += `&status=${status}`;
    return this.request<EscalationsResponse>(url);
  }

  async respondEscalation(id: string, adminNotes: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request(`/api/admin/escalations/${id}/respond`, {
      method: 'POST',
      body: JSON.stringify({ admin_notes: adminNotes }),
    });
  }

  async updateEscalation(id: string, status: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request(`/api/admin/escalations/${id}?status=${status}`, {
      method: 'PATCH',
    });
  }

  // ============== Admin Team Management (Full CRUD) ==============

  async getAdmins(page: number = 1, limit: number = 20): Promise<ApiResponse<{ admins: Admin[]; pagination: { page: number; limit: number; total_items: number; total_pages: number; has_next: boolean; has_prev: boolean } }>> {
    return this.request(`/api/admin/admins?page=${page}&limit=${limit}`);
  }

  async createAdmin(data: AdminCreateRequest): Promise<ApiResponse<{ admin: Admin; message: string }>> {
    return this.request('/api/admin/admins', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAdminRole(email: string, role: AdminRole): Promise<ApiResponse<{ message: string }>> {
    return this.request('/api/admin/admins/role', {
      method: 'PATCH',
      body: JSON.stringify({ email, role }),
    });
  }

  async lockAdmin(email: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/admin/admins/${encodeURIComponent(email)}/lock`, {
      method: 'POST',
    });
  }

  async unlockAdmin(email: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/admin/admins/${encodeURIComponent(email)}/unlock`, {
      method: 'POST',
    });
  }

  async deactivateAdmin(email: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/admin/admins/${encodeURIComponent(email)}/deactivate`, {
      method: 'POST',
    });
  }

  // ============== Audit Log ==============

  async getAuditLogs(params?: {
    action?: string;
    admin_email?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    limit?: number;
  }): Promise<ApiResponse<AdminAuditLogResponse>> {
    const searchParams = new URLSearchParams();
    if (params?.action) searchParams.append('action', params.action);
    if (params?.admin_email) searchParams.append('admin_email', params.admin_email);
    if (params?.date_from) searchParams.append('date_from', params.date_from);
    if (params?.date_to) searchParams.append('date_to', params.date_to);
    if (params?.page) searchParams.append('page', String(params.page));
    if (params?.limit) searchParams.append('limit', String(params.limit));
    return this.request(`/api/admin/audit-log?${searchParams.toString()}`);
  }

  // ============== Provider Costs ==============

  async getProviderCosts(): Promise<ApiResponse<ProviderCostsResponse>> {
    return this.request('/api/admin/providers/costs');
  }

  // ============== System Settings ==============

  async getSettings(): Promise<ApiResponse<SystemSettingsResponse>> {
    return this.request('/api/admin/settings');
  }

  async updateSetting(key: string, value: string): Promise<ApiResponse<{ message: string }>> {
    return this.request('/api/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify({ key, value }),
    });
  }

  async createSetting(key: string, value: string): Promise<ApiResponse<{ message: string }>> {
    return this.request('/api/admin/settings', {
      method: 'POST',
      body: JSON.stringify({ key, value }),
    });
  }

  // ============== Global Search ==============

  async globalSearch(q: string): Promise<ApiResponse<GlobalSearchResponse>> {
    return this.request(`/api/admin/search?q=${encodeURIComponent(q)}`);
  }

  // ============== Metrics Overview ==============

  async getMetricsOverview(): Promise<ApiResponse<MetricsOverview>> {
    return this.request('/api/admin/metrics/overview');
  }

  // ============== Admin Invites (for team page) ==============

  async getAdminInvites(): Promise<ApiResponse<{ invites: Array<{ id: number; email?: string; role: string; invite_code: string; expires_at: string; max_uses: number; uses: number; created_by: string }> }>> {
    return this.request('/api/admin/auth/invites');
  }

  async deleteAdminInvite(inviteId: number): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/admin/auth/invites/${inviteId}`, {
      method: 'DELETE',
    });
  }

  async updateTeamMemberRole(phone: string, role: AdminRole): Promise<ApiResponse<{ message: string }>> {
    return this.request('/api/admin/auth/team/role', {
      method: 'PATCH',
      body: JSON.stringify({ phone, role }),
    });
  }

  async lockTeamMember(phone: string, action: 'lock' | 'unlock'): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/api/admin/auth/team/${action}`, {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
  }
}

export const api = new ApiClient();
export default api;
