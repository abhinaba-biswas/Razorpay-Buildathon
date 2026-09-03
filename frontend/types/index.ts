export interface CartItem {
  sku_id: string;
  name: string;
  qty: number;
  price_inr: number;
}

export interface PendingConfirmation {
  order_id: string;
  action: string;
  items: Array<{ name: string; qty: number }>;
  total_inr: number;
}

export interface UiState {
  cart: CartItem[];
  total_inr: number;
}

export interface ChatResponse {
  reply_text: string;
  ui_state: UiState;
  pending_confirmation: PendingConfirmation | null;
  payment_link: string | null;
}

export interface AuditRow {
  id: number;
  timestamp: string;
  session_id: string;
  action: string;
  reasoning: string;
  bound_check_result: string;
  razorpay_response_summary: string;
  outcome: string;
  inputs_redacted: string;
}

export interface Notification {
  type: 'payment_success' | 'payment_failed';
  order_id: string;
  total_inr?: number;
  reason?: string;
}

// Discriminated union for all renderable chat messages
export type ChatMessage =
  | { id: string; kind: 'user';    text: string }
  | { id: string; kind: 'agent';   text: string }
  | { id: string; kind: 'typing' }
  | { id: string; kind: 'gate';    data: PendingConfirmation }
  | { id: string; kind: 'pay';     url: string; total_inr: number }
  | { id: string; kind: 'success'; order_id: string; total_inr: number }
  | { id: string; kind: 'failure'; reason: string; order_id: string };
