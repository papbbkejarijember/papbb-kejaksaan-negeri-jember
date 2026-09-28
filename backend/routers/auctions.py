from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from lib.auth import public_user, require_role
from lib.db import db
from lib.email_service import record_mock_whatsapp, send_email_notification
from models.auction import (
    AdminDashboard,
    Auction,
    AuctionCreate,
    AuctionDetail,
    AuctionReport,
    AuctionUpdate,
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


def _status(starts_at: str, ends_at: str, manual_status: str | None = None) -> str:
    if manual_status == "ended":
        return "ended"
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
    clean["status"] = _status(clean["starts_at"], clean["ends_at"], clean.get("manual_status"))
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


@router.get("/public/results", response_model=list[Auction])
async def public_results():
    documents = await db.auctions.find().sort("closed_at", -1).to_list(1000)
    return [item for item in (_auction(doc) for doc in documents) if item.status == "ended"]


@router.get("/dashboard/participant", response_model=ParticipantDashboard)
async def participant_dashboard(request: Request):
    user = await require_role(request, "participant")
    bids = await db.bids.find({"bidder_id": user["id"]}).sort("created_at", -1).to_list(100)
    notifications = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    return ParticipantDashboard(
        user=public_user(user),
        active_bids=len(bids),
        won_auctions=await db.auctions.count_documents({"winner_id": user["id"]}),
        total_notifications=len(notifications),
        bids=[Bid(**_clean(bid)) for bid in bids],
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


@router.get("/reports/{auction_id}", response_model=AuctionReport)
async def auction_report(auction_id: str, request: Request):
    await require_role(request, "admin")
    auction = await _get_auction(auction_id)
    bids = await db.bids.find({"auction_id": auction_id}).sort("amount", -1).to_list(1000)
    return AuctionReport(
        generated_at=_now().isoformat(),
        auction=_auction(auction),
        bids=[Bid(**_clean(bid)) for bid in bids],
    )


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
        "manual_status": None,
        "winner_id": None,
        "winner_name": None,
        "winning_bid": None,
        "closed_at": None,
        "created_at": _now().isoformat(),
    }
    await db.auctions.insert_one(document)
    return _auction(document)


@router.patch("/{auction_id}", response_model=Auction)
async def update_auction(auction_id: str, payload: AuctionUpdate, request: Request):
    await require_role(request, "admin")
    current = await _get_auction(auction_id)
    if _auction(current).status == "ended":
        raise HTTPException(status_code=409, detail="Lelang yang selesai tidak dapat diedit")
    changes = payload.model_dump(exclude_none=True)
    if "starts_at" in changes:
        changes["starts_at"] = _normalise_datetime(changes["starts_at"])
    if "ends_at" in changes:
        changes["ends_at"] = _normalise_datetime(changes["ends_at"])
    starts_at = changes.get("starts_at", current["starts_at"])
    ends_at = changes.get("ends_at", current["ends_at"])
    if _parse_datetime(ends_at) <= _parse_datetime(starts_at):
        raise HTTPException(status_code=422, detail="Waktu selesai harus setelah waktu mulai")
    if changes:
        await db.auctions.update_one({"id": auction_id}, {"$set": changes})
    updated = await _get_auction(auction_id)
    return _auction(updated)


@router.post("/{auction_id}/close", response_model=Auction)
async def close_auction(auction_id: str, request: Request):
    await require_role(request, "admin")
    auction = await _get_auction(auction_id)
    if auction.get("manual_status") == "ended":
        return _auction(auction)
    winning_bid = await db.bids.find_one({"auction_id": auction_id}, sort=[("amount", -1)])
    winner = await db.users.find_one({"id": winning_bid["bidder_id"]}) if winning_bid else None
    closed_at = _now().isoformat()
    updates = {
        "manual_status": "ended",
        "closed_at": closed_at,
        "winner_id": winner["id"] if winner else None,
        "winner_name": winner["full_name"] if winner else None,
        "winning_bid": winning_bid["amount"] if winning_bid else None,
    }
    await db.auctions.update_one({"id": auction_id}, {"$set": updates})
    if winner and winning_bid:
        message = f"Selamat, Anda ditetapkan sebagai pemenang {auction['title']} dengan nilai Rp {winning_bid['amount']:,.0f}."
        await send_email_notification(
            user_id=winner["id"], recipient=winner["email"], subject="Pengumuman pemenang lelang",
            message=message, event="auction_winner", auction_id=auction_id,
        )
        await record_mock_whatsapp(
            user_id=winner["id"], subject="Pengumuman pemenang lelang", message=message,
            event="auction_winner", auction_id=auction_id,
        )
    updated = await _get_auction(auction_id)
    return _auction(updated)


@router.post("/{auction_id}/bids", response_model=Bid)
async def place_bid(auction_id: str, payload: BidCreate, request: Request):
    user = await require_role(request, "participant")
    if user.get("verification_status") != "approved":
        raise HTTPException(status_code=403, detail="Identitas peserta harus disetujui sebelum menawar")
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
    await send_email_notification(
        user_id=user["id"], recipient=user["email"], subject="Penawaran Anda berhasil diterima",
        message=f"Penawaran untuk {item.title} sebesar Rp {payload.amount:,.0f} tercatat.",
        event="bid_accepted", auction_id=auction_id,
    )
    if previous_bidder_id and previous_bidder_id != user["id"]:
        previous_user = await db.users.find_one({"id": previous_bidder_id})
        if previous_user:
            outbid_message = f"Penawaran Anda pada {item.title} telah dilampaui peserta lain."
            await send_email_notification(
                user_id=previous_user["id"], recipient=previous_user["email"],
                subject="Penawaran Anda terlampaui", message=outbid_message,
                event="outbid", auction_id=auction_id,
            )
            await record_mock_whatsapp(
                user_id=previous_user["id"], subject="Penawaran Anda terlampaui",
                message=outbid_message, event="outbid", auction_id=auction_id,
            )
    return Bid(**bid)