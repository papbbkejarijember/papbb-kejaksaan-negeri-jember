export type UserRole = "participant" | "admin";
export type AuctionStatus = "upcoming" | "ongoing" | "ended";
export type NotificationChannel = "email" | "whatsapp";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  phone: string | null;
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
  status: "simulated" | "submitted" | "failed";
  provider: string;
  created_at: string;
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
