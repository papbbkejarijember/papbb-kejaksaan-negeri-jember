from typing import Literal

from pydantic import BaseModel, Field

from models.auth import UserPublic
from models.notification import Notification


AuctionStatus = Literal["upcoming", "ongoing", "ended"]


class AuctionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    category: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=2, max_length=180)
    limit_price: float = Field(gt=0)
    increment: float = Field(gt=0)
    starts_at: str = Field(min_length=10, max_length=40)
    ends_at: str = Field(min_length=10, max_length=40)


class AuctionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=180)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    description: str | None = Field(default=None, min_length=10, max_length=2000)
    location: str | None = Field(default=None, min_length=2, max_length=180)
    limit_price: float | None = Field(default=None, gt=0)
    increment: float | None = Field(default=None, gt=0)
    starts_at: str | None = Field(default=None, min_length=10, max_length=40)
    ends_at: str | None = Field(default=None, min_length=10, max_length=40)


class Auction(BaseModel):
    id: str
    title: str
    category: str
    description: str
    location: str
    limit_price: float
    increment: float
    starts_at: str
    ends_at: str
    status: AuctionStatus
    highest_bid: float | None = None
    bid_count: int = 0
    winner_name: str | None = None
    winning_bid: float | None = None
    closed_at: str | None = None
    created_at: str


class BidCreate(BaseModel):
    amount: float = Field(gt=0)


class Bid(BaseModel):
    id: str
    auction_id: str
    bidder_id: str
    bidder_name: str
    amount: float
    created_at: str


class AuctionDetail(Auction):
    bids: list[Bid] = Field(default_factory=list)


class AuctionReport(BaseModel):
    generated_at: str
    auction: Auction
    bids: list[Bid]


class ParticipantDashboard(BaseModel):
    user: UserPublic
    active_bids: int
    won_auctions: int
    total_notifications: int
    bids: list[Bid]
    notifications: list[Notification]


class AdminDashboard(BaseModel):
    total_auctions: int
    ongoing_auctions: int
    upcoming_auctions: int
    ended_auctions: int
    auctions: list[Auction]
