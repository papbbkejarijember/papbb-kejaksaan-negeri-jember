from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from lib.auth import public_user, require_role, get_current_user
from lib.db import db
from models.auction import (
    AdminDashboard,
    Auction,
    AuctionCreate,
    AuctionDetail,
    Bid,
    BidCreate,
    ParticipantDashboard,
)


router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _normalise_datetime(value: str) -> str:
    return _parse_datetime(value).astimezone(timezone.utc).isoformat()


def _status(starts_at: str, ends_at: str) -> str:
    now = _now()
    if now < _parse_datetime(starts_at):
        return "upcoming"
    if now >= _parse_datetime(ends_at):
        return "ended"
    return "ongoing"


def _clean(doc: dict) -> dict:
    return {key: value for key, value in doc.items() if key != "_id"}


def _auction(doc: dict) -> Auction:
    clean = _clean(doc)
    clean["status"] = _status(clean["starts_at"], clean["ends_at"])
    return Auction(**clean)


async def _get_auction(auction_id: str) -> dict:
    auction = await db.auctions.find_one({"id": auction_id})
    if not auction:
        raise HTTPException(status_code=404, detail="Lelang tidak ditemukan")
    return auction


@router.get("", response_model=list[Auction])
async def list_auctions(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=60),
    status: str | None = Query(default=None, max_length=20),
):
    documents = await db.auctions.find().sort("created_at", -1).to_list(1000)
    result = []
    for doc in documents:
        item = _auction(doc)
        if category and category != "all" and item.category != category:
            continue
        if status and status != "all" and item.status != status:
            continue
        if search and search.lower() not in f"{item.title} {item.description} {item.location}".lower():
            continue
        result.append(item)
    return result


@router.get("/{auction_id}", response_model=AuctionDetail)
async def get_auction(auction_id: str):
    auction = await _get_auction(auction_id)
    bids = await db.bids.find({"auction_id": auction_id}).sort("created_at", -1).to_list(100)
    return AuctionDetail(**_auction(auction).model_dump(), bids=[Bid(**_clean(bid)) for bid in bids])


@router.post("", response_model=Auction)
async def create_auction(payload: AuctionCreate, request: Request):
    await require_role(request, "admin")
    starts_at = _normalise_datetime(payload.starts_at)
    ends_at = _normalise_datetime(payload.ends_at)
    if _parse_datetime(ends_at) <= _parse_datetime(starts_at):
        raise HTTPException(status_code=422, detail="Waktu selesai harus setelah waktu mulai")
    document = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "category": payload.category,
        "description": payload.description.strip(),
        "location": payload.location.strip(),
        "limit_price": payload.limit_price,
        "increment": payload.increment,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "highest_bid": None,
        "highest_bidder_id": None,
        "bid_count": 0,
        "created_at": _now().isoformat(),
    }
    await db.auctions.insert_one(document)
    return _auction(document)


@router.post("/{auction_id}/bids", response_model=Bid)
async def place_bid(auction_id: str, payload: BidCreate, request: Request):
    user = await require_role(request, "participant")
    auction = await _get_auction(auction_id)
    item = _auction(auction)
    if item.status != "ongoing":
        raise HTTPException(status_code=409, detail="Lelang belum atau sudah selesai")
    minimum = item.limit_price if item.highest_bid is None else item.highest_bid + item.increment
    if payload.amount < minimum:
        raise HTTPException(status_code=422, detail=f"Penawaran minimum berikutnya Rp {minimum:,.0f}")
    created_at = _now().isoformat()
    bid = {
        "id": str(uuid.uuid4()),
        "auction_id": auction_id,
        "bidder_id": user["id"],
        "bidder_name": user["full_name"],
        "amount": payload.amount,
        "created_at": created_at,
    }
    previous_bidder_id = auction.get("highest_bidder_id")
    await db.bids.insert_one(bid)
    await db.auctions.update_one(
        {"id": auction_id},
        {"$set": {"highest_bid": payload.amount, "highest_bidder_id": user["id"]}, "$inc": {"bid_count": 1}},
    )
    await db.notifications.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "channel": "email",
            "subject": "Penawaran Anda berhasil diterima",
            "message": f"Penawaran untuk {item.title} sebesar Rp {payload.amount:,.0f} tercatat.",
            "status": "simulated",
            "provider": "mock",
            "created_at": created_at,
        }
    )
    if previous_bidder_id and previous_bidder_id != user["id"]:
        await db.notifications.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": previous_bidder_id,
                "channel": "whatsapp",
                "subject": "Penawaran Anda terlampaui",
                "message": f"Penawaran pada {item.title} telah dilampaui peserta lain.",
                "status": "simulated",
                "provider": "mock",
                "created_at": created_at,
            }
        )
    return Bid(**bid)


@router.get("/dashboard/participant", response_model=ParticipantDashboard)
async def participant_dashboard(request: Request):
    user = await require_role(request, "participant")
    bids = await db.bids.find({"bidder_id": user["id"]}).sort("created_at", -1).to_list(100)
    notifications = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    bid_models = [Bid(**_clean(bid)) for bid in bids]
    return ParticipantDashboard(
        user=public_user(user),
        active_bids=len(bids),
        won_auctions=0,
        total_notifications=len(notifications),
        bids=bid_models,
        notifications=[_clean(notification) for notification in notifications],
    )


@router.get("/dashboard/admin", response_model=AdminDashboard)
async def admin_dashboard(request: Request):
    await require_role(request, "admin")
    documents = await db.auctions.find().sort("created_at", -1).to_list(1000)
    auctions = [_auction(doc) for doc in documents]
    return AdminDashboard(
        total_auctions=len(auctions),
        ongoing_auctions=sum(item.status == "ongoing" for item in auctions),
        upcoming_auctions=sum(item.status == "upcoming" for item in auctions),
        ended_auctions=sum(item.status == "ended" for item in auctions),
        auctions=auctions,
    )
