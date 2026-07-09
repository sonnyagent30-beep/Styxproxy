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
  provider: 'proxy-seller' | 'dataimpulse';
}

export interface Order {
  order_id: string;
  status: OrderStatus;
  plan_type?: PlanType;
  country?: string;
  amount_paid_ngn?: number;
  bunche_credential?: BuncheCredential;
  created_at: string;
  expires_at?: string;
}

export interface BuncheCredential {
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
