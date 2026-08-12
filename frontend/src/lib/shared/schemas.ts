/**
 * Shared Zod schemas — single source of truth for FE/BE contract.
 * Keep in sync with backend/app/schemas.py Pydantic models.
 */
import { z } from 'zod';

export const PlanTypeSchema = z.enum(['ISP', 'DC', 'RESIDENTIAL', 'MOBILE']);
export type PlanType = z.infer<typeof PlanTypeSchema>;

export const OrderStatusSchema = z.enum(['pending','paid','fulfilled','active','expired','cancelled','refunded','pending_verification']);
export type OrderStatus = z.infer<typeof OrderStatusSchema>;

export const CredentialStatusSchema = z.enum(['active','expired','revoked','suspended']);
export type CredentialStatus = z.infer<typeof CredentialStatusSchema>;

export const ProtocolSchema = z.enum(['http','https','socks5']);
export type Protocol = z.infer<typeof ProtocolSchema>;

export const PoolTypeSchema = z.enum(['paid','free_trial','refunded_recycled']);
export type PoolType = z.infer<typeof PoolTypeSchema>;

export const PhoneSchema = z.string().regex(/^\+?[\d\s\-]{10,20}$/, 'Invalid phone');
export type Phone = z.infer<typeof PhoneSchema>;

export const StyxproxyCredentialSchema = z.object({
  id: z.string(),
  bun_username: z.string().optional(),
  styxproxy_username: z.string().optional(),
  provider_username: z.string().optional(),
  provider_password: z.string().optional(),
  provider_name: z.string().optional(),
  pool_type: PoolTypeSchema.optional(),
  customer_phone: PhoneSchema.optional(),
  order_id: z.string().optional(),
  protocol: ProtocolSchema.optional(),
  upstream_proxy_ip: z.string().optional(),
  upstream_proxy_port: z.number().int().optional(),
  styxproxy_password: z.string().optional(),
  dante_port: z.number().int().optional(),
  status: CredentialStatusSchema,
  expires_at: z.string().datetime().optional(),
});
export type StyxproxyCredential = z.infer<typeof StyxproxyCredentialSchema>;

export const OrderSchema = z.object({
  order_id: z.string(),
  tx_ref: z.string().optional(),
  status: OrderStatusSchema,
  plan_type: PlanTypeSchema.optional(),
  plan_code: z.string().optional(),
  country: z.string().optional(),
  quantity: z.number().int().optional(),
  amount_paid_ngn: z.number().optional(),
  currency: z.string().optional(),
  customer_phone: PhoneSchema.optional(),
  customer_name: z.string().optional(),
  customer_email: z.string().email().optional(),
  styxproxy_credential: StyxproxyCredentialSchema.optional(),
  created_at: z.string().datetime().optional(),
  fulfilled_at: z.string().datetime().optional(),
  expires_at: z.string().datetime().optional(),
  is_renewable: z.boolean().optional(),
  rotation_count: z.number().int().optional(),
  max_rotations: z.number().int().optional(),
  notes: z.string().optional(),
  refund_requested: z.boolean().optional(),
  refund_reason: z.string().optional(),
  refunded_at: z.string().datetime().optional(),
});
export type Order = z.infer<typeof OrderSchema>;

export const CustomerSchema = z.object({
  id: z.string().uuid(),
  phone: PhoneSchema,
  name: z.string().min(1).max(30),
  blocked: z.boolean(),
  total_orders: z.number().int().nonnegative(),
  lifetime_value_ngn: z.number().nonnegative(),
  created_at: z.string().datetime(),
});
export type Customer = z.infer<typeof CustomerSchema>;

export const CartItemSchema = z.object({
  plan_code: z.string(), name: z.string(), flag: z.string(),
  price_ngn: z.number().positive(), plan_type: PlanTypeSchema, country: z.string(),
  city: z.string().optional(), gb_tier: z.number().int().optional(),
  quantity: z.number().int().positive().optional(), gb_per_ip: z.number().int().positive().optional(),
  plan_id: z.number().int(), variant_id: z.number().int(), template_label: z.string(),
});
export type CartItem = z.infer<typeof CartItemSchema>;

export const AdminLoginRequestSchema = z.object({
  email: z.string().email(), password: z.string().min(1), totp_code: z.string().regex(/^\d{6}$/).optional(),
});
export type AdminLoginRequest = z.infer<typeof AdminLoginRequestSchema>;

export const AdminLoginResponseSchema = z.object({
  access_token: z.string(), token_type: z.string(), email: z.string().email(),
  role: z.string(), totp_enabled: z.boolean(), expires_in: z.number().int(),
});
export type AdminLoginResponse = z.infer<typeof AdminLoginResponseSchema>;

export const PaymentInitiateRequestSchema = z.object({
  plan_code: z.string(), country: z.string(),
  quantity: z.number().int().positive().optional(),
  gb_tier: z.number().int().positive().optional(),
  city: z.string().optional(), referrer_name: z.string().optional(),
});
export type PaymentInitiateRequest = z.infer<typeof PaymentInitiateRequestSchema>;

export const PaymentInitiateResponseSchema = z.object({
  payment_id: z.string(), checkout_url: z.string().url(),
  amount_ngn: z.number().positive(), expires_at: z.string().datetime(),
});
export type PaymentInitiateResponse = z.infer<typeof PaymentInitiateResponseSchema>;

export const CredentialRotationRequestSchema = z.object({
  order_id: z.string(),
  reason: z.enum(['user_request','admin_request','security_incident','dead_proxy']).optional(),
});
export type CredentialRotationRequest = z.infer<typeof CredentialRotationRequestSchema>;

export const AdminStatsSchema = z.object({
  total_customers: z.number().int().nonnegative(), active_orders: z.number().int().nonnegative(),
  total_revenue_ngn: z.number().nonnegative(), free_trials_today: z.number().int().nonnegative(),
  active_credentials: z.number().int().nonnegative(),
  plan_counts: z.record(z.string(), z.number().int().nonnegative()),
});
export type AdminStats = z.infer<typeof AdminStatsSchema>;
