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
  AdminSetupResponse,
  AdminMeResponse,
  AdminTeamMember,
  AdminInviteCreateRequest,
  AdminInviteCreateResponse,
  BlogPost,
  BlogPostCreate,
  BlogPostUpdate,
  BlogPostsResponse,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
      if (adminToken && endpoint.startsWith('/admin')) {
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
    return this.request<AdminStats>('/admin/stats');
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
    return this.request<LearnedFilesResponse>('/admin/charon/learned');
  }

  async getLearnedFileContent(filename: string): Promise<ApiResponse<LearnContentResponse>> {
    return this.request<LearnContentResponse>(`/admin/charon/learned/${encodeURIComponent(filename)}`);
  }

  async deleteLearnedFile(filename: string): Promise<ApiResponse<{ ok: boolean; message: string }>> {
    return this.request('/admin/charon/learned', {
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
    return this.request('/admin/auth/status');
  }

  // Initial admin setup (first time)
  async setupAdmin(data: AdminSetupRequest): Promise<ApiResponse<AdminSetupResponse>> {
    return this.request<AdminSetupResponse>('/admin/auth/setup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Admin login
  async adminLogin(data: AdminLoginRequest): Promise<ApiResponse<AdminLoginResponse>> {
    return this.request<AdminLoginResponse>('/admin/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Get current admin info
  async getAdminMe(): Promise<ApiResponse<AdminMeResponse>> {
    return this.request<AdminMeResponse>('/admin/auth/me');
  }

  // Admin logout
  async adminLogout(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/admin/auth/logout', {
      method: 'POST',
    });
  }

  // Get admin team (SuperAdmin only)
  async getAdminTeam(): Promise<ApiResponse<{ members: AdminTeamMember[] }>> {
    return this.request('/admin/auth/team');
  }

  // Create admin invite (SuperAdmin only)
  async createAdminInvite(data: AdminInviteCreateRequest): Promise<ApiResponse<AdminInviteCreateResponse>> {
    return this.request<AdminInviteCreateResponse>('/admin/auth/invite', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Change admin PIN
  async changeAdminPin(currentPin: string, newPin: string): Promise<ApiResponse<{ message: string }>> {
    return this.request('/admin/auth/password', {
      method: 'POST',
      body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
    });
  }

  // Toggle TOTP
  async toggleAdminTOTP(action: 'enable' | 'disable', totpCode?: string): Promise<ApiResponse<{ totp_enabled: boolean; message: string }>> {
    return this.request('/admin/auth/totp', {
      method: 'POST',
      body: JSON.stringify({ action, totp_code: totpCode }),
    });
  }

  // ============== Blog ==============

  // Get all published blog posts (public)
  async getBlogPosts(page: number = 1, limit: number = 10): Promise<ApiResponse<BlogPostsResponse>> {
    return this.request<BlogPostsResponse>(`/blog/posts?page=${page}&limit=${limit}&published=true`);
  }

  // Get single blog post by slug (public)
  async getBlogPost(slug: string): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/blog/posts/${slug}`);
  }

  // Get all blog posts for admin (includes unpublished)
  async getAdminBlogPosts(page: number = 1, limit: number = 20): Promise<ApiResponse<BlogPostsResponse>> {
    return this.request<BlogPostsResponse>(`/admin/blog/posts?page=${page}&limit=${limit}`);
  }

  // Create blog post (admin)
  async createBlogPost(data: BlogPostCreate): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>('/admin/blog/posts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Update blog post (admin)
  async updateBlogPost(id: number, data: BlogPostUpdate): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/admin/blog/posts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Delete blog post (admin)
  async deleteBlogPost(id: number): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/admin/blog/posts/${id}`, {
      method: 'DELETE',
    });
  }

  // Publish/unpublish blog post (admin)
  async toggleBlogPostPublish(id: number, published: boolean): Promise<ApiResponse<BlogPost>> {
    return this.request<BlogPost>(`/admin/blog/posts/${id}/publish`, {
      method: 'POST',
      body: JSON.stringify({ published }),
    });
  }
}

export const api = new ApiClient();
export default api;
