from datetime import datetime, timezone
import base64
import binascii
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from lib.audit import write_audit
from lib.auth import public_user, require_role
from lib.db import db
from lib.email_service import record_mock_whatsapp, send_email_notification
from lib.rate_limit import enforce_rate_limit
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


def _validate_image_data(value: str | None) -> str | None:
    if value is None: return None
    if not value.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
        raise HTTPException(status_code=422, detail="Foto harus JPG, PNG, atau WEBP")
    if len(value) > 4_500_000: raise HTTPException(status_code=413, detail="Ukuran foto terlalu besar. Maksimal sekitar 3,3 MB")
    encoded = value.split(",", 1)[1]
    try: raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc: raise HTTPException(status_code=422, detail="Data foto tidak valid") from exc
    if len(raw) > 3_300_000: raise HTTPException(status_code=413, detail="Ukuran foto terlalu besar. Maksimal 3,3 MB")
    if value.startswith("data:image/jpeg") and not raw.startswith(b"\xff\xd8\xff"): raise HTTPException(status_code=422, detail="File JPEG tidak valid")
    if value.startswith("data:image/png") and not raw.startswith(b"\x89PNG\r\n\x1a\n"): raise HTTPException(status_code=422, detail="File PNG tidak valid")
    if value.startswith("data:image/webp") and not (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"): raise HTTPException(status_code=422, detail="File WEBP tidak valid")
    return value

def _auction(doc: dict) -> Auction:
    clean = _clean(doc)
    has_image = bool(clean.pop("image_data", None))
    clean["image_url"] = f"/api/auctions/{clean['id']}/image" if has_image else None
    clean["status"] = _status(clean["starts_at"], clean["ends_at"], clean.get("manual_status"))
    return Auction(**clean)


def _masked_bid(doc: dict) -> Bid:
    clean = _clean(doc)
    name = clean.get("bidder_name", "Peserta")
    clean["bidder_name"] = " ".join(f"{part[:1]}***" for part in name.split())
    return Bid(**clean)


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


@router.get("/{auction_id}/image")
async def auction_image(auction_id: str):
    auction = await _get_auction(auction_id)
    value = auction.get("image_data")
    if not value: raise HTTPException(status_code=404, detail="Foto objek tidak tersedia")
    header, encoded = value.split(",", 1)
    try: content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc: raise HTTPException(status_code=500, detail="Foto objek rusak") from exc
    return Response(content=content, media_type=header.removeprefix("data:").removesuffix(";base64"), headers={"Cache-Control": "public, max-age=300"})

@router.get("/{auction_id}", response_model=AuctionDetail)
async def get_auction(auction_id: str):
    auction = await _get_auction(auction_id)
    bids = await db.bids.find({"auction_id": auction_id}).sort("created_at", -1).to_list(100)
    return AuctionDetail(**_auction(auction).model_dump(), bids=[_masked_bid(bid) for bid in bids])


@router.post("", response_model=Auction)
async def create_auction(payload: AuctionCreate, request: Request):
    admin = await require_role(request, "admin")
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
        "image_data": _validate_image_data(payload.image_data),
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
    await write_audit(actor=admin, action="auction_created", target_type="auction", target_id=document["id"], request=request)
    return _auction(document)


@router.patch("/{auction_id}", response_model=Auction)
async def update_auction(auction_id: str, payload: AuctionUpdate, request: Request):
    admin = await require_role(request, "admin")
    current = await _get_auction(auction_id)
    if _auction(current).status == "ended":
        raise HTTPException(status_code=409, detail="Lelang yang selesai tidak dapat diedit")
    changes = payload.model_dump(exclude_none=True)
    if "image_data" in changes: changes["image_data"] = _validate_image_data(changes["image_data"])
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
        await write_audit(actor=admin, action="auction_updated", target_type="auction", target_id=auction_id, request=request, metadata={"fields": sorted(changes.keys())})
    updated = await _get_auction(auction_id)
    return _auction(updated)


@router.post("/{auction_id}/close", response_model=Auction)
async def close_auction(auction_id: str, request: Request):
    admin = await require_role(request, "admin")
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
    await write_audit(actor=admin, action="auction_closed", target_type="auction", target_id=auction_id, request=request, metadata={"has_winner": bool(winner)})
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
    await enforce_rate_limit(request, scope="bid", identifier=user["id"], limit=30, window_seconds=60)
    if user.get("verification_status") != "approved":
        raise HTTPException(status_code=403, detail="Identitas peserta harus disetujui sebelum menawar")
    auction = await _get_auction(auction_id)
    item = _auction(auction)
    if item.status != "ongoing":
        raise HTTPException(status_code=409, detail="Lelang belum atau sudah selesai")
    previous_bidder_id = auction.get("highest_bidder_id")
    if auction.get("highest_bid") is None:
        bid_filter = {"id": auction_id, "highest_bid": None, "manual_status": {"$ne": "ended"}}
        minimum = item.limit_price
    else:
        bid_filter = {"id": auction_id, "highest_bid": auction["highest_bid"], "increment": auction["increment"], "manual_status": {"$ne": "ended"}}
        minimum = item.highest_bid + item.increment
    if payload.amount < minimum:
        raise HTTPException(status_code=422, detail=f"Penawaran minimum berikutnya Rp {minimum:,.0f}")
    claimed = await db.auctions.update_one(
        bid_filter,
        {"$set": {"highest_bid": payload.amount, "highest_bidder_id": user["id"]}, "$inc": {"bid_count": 1}},
    )
    if claimed.modified_count != 1:
        fresh = await _get_auction(auction_id)
        fresh_item = _auction(fresh)
        fresh_minimum = fresh_item.limit_price if fresh_item.highest_bid is None else fresh_item.highest_bid + fresh_item.increment
        raise HTTPException(status_code=409, detail=f"Penawaran berubah. Minimum penawaran berikutnya Rp {fresh_minimum:,.0f}")
    created_at = _now().isoformat()
    bid = {"id": str(uuid.uuid4()), "auction_id": auction_id, "bidder_id": user["id"], "bidder_name": user["full_name"], "amount": payload.amount, "created_at": created_at}
    try:
        await db.bids.insert_one(bid)
    except Exception:
        await db.auctions.update_one(
            {"id": auction_id, "highest_bid": payload.amount, "highest_bidder_id": user["id"]},
            {"$set": {"highest_bid": auction.get("highest_bid"), "highest_bidder_id": previous_bidder_id}, "$inc": {"bid_count": -1}},
        )
        raise
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