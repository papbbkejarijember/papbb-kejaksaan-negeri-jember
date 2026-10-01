export type UserRole = "participant" | "admin";
export type AuctionStatus = "upcoming" | "ongoing" | "ended";
export type NotificationChannel = "email" | "whatsapp";
export type NotificationStatus = "simulated" | "submitted" | "delivered" | "opened" | "soft_bounce" | "hard_bounce" | "blocked" | "invalid" | "failed";
export type VerificationStatus = "not_submitted" | "pending" | "approved" | "rejected";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  phone: string | null;
  verification_status: VerificationStatus;
  created_at: string;
}

export interface SessionResponse {
  user: User;
}

export interface Auction {
  id: string;
  title: string;
  category: string;
  description: string;
  location: string;
  limit_price: number;
  increment: number;
  starts_at: string;
  ends_at: string;
  status: AuctionStatus;
  highest_bid: number | null;
  bid_count: number;
  winner_name: string | null;
  winning_bid: number | null;
  closed_at: string | null;
  created_at: string;
}

export interface Bid {
  id: string;
  auction_id: string;
  bidder_id: string;
  bidder_name: string;
  amount: number;
  created_at: string;
}

export interface AuctionDetail extends Auction {
  bids: Bid[];
}

export interface Notification {
  id: string;
  user_id: string;
  channel: NotificationChannel;
  subject: string;
  message: string;
  status: NotificationStatus;
  provider: string;
  provider_message_id: string | null;
  event: string | null;
  error: string | null;
  status_history: NotificationStatusEvent[];
  updated_at: string | null;
  created_at: string;
}

export interface NotificationStatusEvent {
  status: NotificationStatus;
  provider_event: string | null;
  at: string;
  provider_ts: string | number | null;
}

export interface ParticipantDashboard {
  user: User;
  active_bids: number;
  won_auctions: number;
  total_notifications: number;
  bids: Bid[];
  notifications: Notification[];
}

export interface AdminDashboard {
  total_auctions: number;
  ongoing_auctions: number;
  upcoming_auctions: number;
  ended_auctions: number;
  auctions: Auction[];
}

export interface AuctionCreatePayload {
  title: string;
  category: string;
  description: string;
  location: string;
  limit_price: number;
  increment: number;
  starts_at: string;
  ends_at: string;
}

export interface IdentitySubmission {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  nik: string;
  address: string;
  ktp_image_data: string;
  status: VerificationStatus;
  submitted_at: string;
  reviewed_at: string | null;
  review_note: string | null;
  consented_at: string | null;
}

export interface NotificationConfig {
  email_mode: "brevo" | "mock";
  whatsapp_mode: "mock" | "disabled";
  sender_email: string | null;
}

export interface AuditLog {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface NotificationTestResponse {
  status: "simulated" | "submitted" | "failed";
  notifications: Notification[];
}

export type EmailAnalyticsRange = "7d" | "30d" | "all";

export interface EmailAnalyticsPoint {
  date: string;
  sent: number;
  delivered: number;
  opened: number;
  failed: number;
}

export interface EmailAnalytics {
  range: EmailAnalyticsRange;
  from_date: string | null;
  to_date: string;
  totals: {
    sent: number;
    delivered: number;
    opened: number;
    failed: number;
  };
  delivery_rate: number;
  open_rate: number;
  failure_rate: number;
  trend: EmailAnalyticsPoint[];
}

export interface AuctionReport {
  generated_at: string;
  auction: Auction;
  bids: Bid[];
}
