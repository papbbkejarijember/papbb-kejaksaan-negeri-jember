import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging
from pathlib import Path


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes
from lib.brevo_webhook import ensure_brevo_webhook
from lib.bootstrap import ensure_admin_account


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https://customer-assets-7cd3h4nn.emergentagent.net; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' ws: wss:; "
            "font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())  # background: a big index build must not block boot
    await ensure_admin_account()
    await ensure_brevo_webhook()
    yield
    client.close()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {"message": "Portal Lelang Kejaksaan Negeri Jember", "mode": "preproduction"}


from routers import auth, auctions, cron, notifications, webhooks

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(auctions.router, prefix="/auctions", tags=["auctions"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(cron.router, prefix="/cron", tags=["cron"])

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Include the router last so every endpoint remains under /api.
app.include_router(api_router)
