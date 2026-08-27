// Order status helpers — pure functions for status logic

export type OrderStatus =
  | 'pending'
  | 'paid'
  | 'processing'
  | 'fulfilled'
  | 'active'
  | 'expired'
  | 'cancelled'
  | 'refunded'
  | 'payment_failed';

export type StatusGroup = 'in-progress' | 'success' | 'terminal-bad';

export const STATUS_GROUPS: Record<StatusGroup, OrderStatus[]> = {
  'in-progress': ['pending', 'paid', 'processing'],
  success: ['fulfilled', 'active'],
  'terminal-bad': ['expired', 'cancelled', 'refunded', 'payment_failed'],
};

export function getStatusGroup(status: string): StatusGroup {
  if (STATUS_GROUPS['in-progress'].includes(status as OrderStatus)) return 'in-progress';
  if (STATUS_GROUPS.success.includes(status as OrderStatus)) return 'success';
  return 'terminal-bad';
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: 'Awaiting Payment',
    paid: 'Payment Received',
    processing: 'Provisioning',
    fulfilled: 'Proxy Active',
    active: 'Proxy Active',
    expired: 'Expired',
    cancelled: 'Cancelled',
    refunded: 'Refunded',
    payment_failed: 'Payment Failed',
  };
  return labels[status] || status;
}

export function getStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    pending: 'clock',
    paid: 'check',
    processing: 'spinner',
    fulfilled: 'check-circle',
    active: 'check-circle',
    expired: 'clock-counter-clockwise',
    cancelled: 'x-circle',
    refunded: 'arrow-counter-clockwise',
    payment_failed: 'warning-circle',
  };
  return icons[status] || 'question';
}

export interface OrderAction {
  kind: 'rotate' | 'renew' | 'retry_payment' | 'reorder' | 'cancel' | 'contact_support' | 'download_receipt';
  label: string;
  href?: string;
  disabled?: boolean;
  reason?: string;
  confirm?: boolean;
  variant: 'primary' | 'secondary' | 'tertiary' | 'danger';
}

export function getActionsForStatus(
  status: string,
  orderId: string,
  options: {
    rotationsLeft?: number;
    isRenewable?: boolean;
    isNearExpiry?: boolean;
  } = {}
): OrderAction[] {
  const { rotationsLeft = 0, isRenewable = false, isNearExpiry = false } = options;
  const actions: OrderAction[] = [];

  switch (status) {
    case 'pending':
      actions.push({ kind: 'cancel', label: 'Cancel Order', confirm: true, variant: 'danger' });
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
    case 'paid':
    case 'processing':
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
    case 'fulfilled':
    case 'active':
      if (rotationsLeft > 0) {
        actions.push({ kind: 'rotate', label: `Rotate Key (${rotationsLeft} left)`, variant: 'primary' });
      }
      if (isRenewable || isNearExpiry) {
        actions.push({ kind: 'renew', label: 'Renew', href: `/order/checkout?renew=${orderId}`, variant: 'secondary' });
      }
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
    case 'expired':
      if (isRenewable) {
        actions.push({ kind: 'renew', label: 'Renew', href: `/order/checkout?renew=${orderId}`, variant: 'primary' });
      }
      actions.push({ kind: 'reorder', label: 'Order New', href: '/order', variant: 'secondary' });
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
    case 'cancelled':
      actions.push({ kind: 'reorder', label: 'Order New', href: '/order', variant: 'primary' });
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
    case 'refunded':
      actions.push({ kind: 'reorder', label: 'Order New', href: '/order', variant: 'primary' });
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
    case 'payment_failed':
      actions.push({ kind: 'retry_payment', label: 'Retry Payment', href: `/order/checkout?renew=${orderId}`, variant: 'primary' });
      actions.push({ kind: 'cancel', label: 'Cancel Order', confirm: true, variant: 'danger' });
      actions.push({ kind: 'contact_support', label: 'Contact Support', variant: 'tertiary' });
      break;
  }

  return actions;
}

export interface TimelineStep {
  key: string;
  label: string;
  date: string;
  state: 'done' | 'current' | 'pending';
}

export function getTimelineSteps(status: string, dates: { created?: string; paid?: string; fulfilled?: string; expires?: string }): TimelineStep[] {
  const steps: TimelineStep[] = [];

  steps.push({ key: 'placed', label: 'Order Placed', date: dates.created || '', state: 'done' });

  if (['paid', 'processing', 'fulfilled', 'active', 'expired', 'refunded'].includes(status)) {
    steps.push({ key: 'paid', label: 'Payment Confirmed', date: dates.paid || '', state: 'done' });
  } else if (status === 'payment_failed') {
    steps.push({ key: 'paid', label: 'Payment Failed', date: '', state: 'current' });
  } else {
    steps.push({ key: 'paid', label: 'Payment Confirmed', date: '', state: 'pending' });
  }

  if (['fulfilled', 'active', 'expired'].includes(status)) {
    steps.push({ key: 'provisioned', label: 'Proxy Provisioned', date: dates.fulfilled || '', state: 'done' });
  } else if (status === 'processing') {
    steps.push({ key: 'provisioned', label: 'Proxy Provisioning', date: '', state: 'current' });
  } else if (status !== 'payment_failed' && status !== 'cancelled') {
    steps.push({ key: 'provisioned', label: 'Proxy Provisioned', date: '', state: 'pending' });
  }

  if (status === 'expired') {
    steps.push({ key: 'expired', label: 'Expired', date: dates.expires || '', state: 'current' });
  } else if (['fulfilled', 'active'].includes(status) && dates.expires) {
    steps.push({ key: 'expires', label: 'Expires', date: dates.expires, state: 'pending' });
  }

  if (status === 'cancelled') {
    steps.push({ key: 'cancelled', label: 'Cancelled', date: '', state: 'current' });
  }

  if (status === 'refunded') {
    steps.push({ key: 'refunded', label: 'Refunded', date: '', state: 'current' });
  }

  return steps;
}
