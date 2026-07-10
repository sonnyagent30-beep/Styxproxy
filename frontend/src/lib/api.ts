import type { 
  Product, 
  Order, 
  PaymentInitiateResponse, 
  AdminStats,
  Customer,
  ApiResponse,
  PaginatedResponse,
  StyxproxyCredential
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
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

  // Health
  async healthCheck(): Promise<ApiResponse<{ status: string; version: string; database: string; timestamp: string }>> {
    return this.request('/health');
  }
}

export const api = new ApiClient();
export default api;
