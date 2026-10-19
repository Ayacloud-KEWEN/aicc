"""Demo web server: restaurant site, kitchen board, and WebRTC signalling for AI calls.

Run:  python server.py   then open http://localhost:7860
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pipecat.transports.smallwebrtc.connection import IceServer, SmallWebRTCConnection
# The browser sends its offer after ICE gathering completes, so no trickle-ICE endpoint is needed.
from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequest, SmallWebRTCRequestHandler

import payments
import providers
from bot import run_bot
from restaurant import CATEGORY_NAMES, MENU, RESTAURANT, store

STATIC = Path(__file__).parent / "static"

# STUN finds the public address for calls across the internet. Over Tailscale or a LAN it is
# not needed and gathering it costs ~5 s per call, so set STUN_URLS= (empty) to skip it.
STUN_URLS = [u.strip() for u in os.getenv("STUN_URLS", "stun:stun.l.google.com:19302").split(",") if u.strip()]
webrtc = SmallWebRTCRequestHandler(ice_servers=[IceServer(urls=u) for u in STUN_URLS] or None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await webrtc.close()


app = FastAPI(title="AI ordering demo", lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/kitchen")
async def kitchen():
    return FileResponse(STATIC / "kitchen.html")


@app.get("/api/config")
async def config():
    return {
        "providers": providers.selected(),
        "missing_keys": providers.missing_keys(),
        "ice_servers": [{"urls": u} for u in STUN_URLS],
        "payment": "stripe" if payments.enabled() else "pickup",
    }


@app.get("/api/menu")
async def menu():
    return {"restaurant": RESTAURANT, "categories": CATEGORY_NAMES, "items": MENU}


@app.get("/api/orders")
async def orders():
    return {"orders": list(reversed(store.orders)), "reservations": list(reversed(store.reservations))}


@app.get("/api/orders/{order_id}/payment")
async def order_payment(order_id: str):
    """Payment state of an order; asks Stripe when it is still pending (no webhook)."""
    order = store.get_order(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    try:
        order = await payments.refresh(order)
    except Exception as e:
        logger.warning(f"Stripe lookup failed for {order_id}: {e}")
    return {"order_id": order["id"], "payment": order.get("payment"), "total": order["total"]}


@app.get("/api/payment/confirm")
async def payment_confirm(session_id: str):
    """Stripe's success redirect lands on /?paid=<session_id>; the page calls this."""
    if not payments.enabled():
        raise HTTPException(400, "payments disabled")
    try:
        order = await payments.confirm_session(session_id)
    except Exception as e:
        logger.warning(f"Stripe confirm failed: {e}")
        raise HTTPException(502, "could not reach Stripe")
    if not order:
        raise HTTPException(404, "order not found")
    return {"order_id": order["id"], "payment": order.get("payment"), "total": order["total"]}


@app.post("/api/orders/{order_id}/status")
async def set_status(order_id: str, request: Request):
    body = await request.json()
    if body.get("status") not in {"new", "preparing", "ready", "done"}:
        raise HTTPException(400, "invalid status")
    order = store.set_order_status(order_id, body["status"])
    if not order:
        raise HTTPException(404, "order not found")
    return order


@app.post("/api/offer")
async def offer(request: Request, background_tasks: BackgroundTasks):
    missing = providers.missing_keys()
    if missing:
        raise HTTPException(503, f"Missing API keys in .env: {', '.join(missing)}")
    body = await request.json()
    request_data = body.get("request_data") or body.get("requestData") or {}
    lang = request_data.get("lang", "fr")
    # The page's own origin (e.g. https://pi.tailnet.ts.net:10051), for Stripe's return URLs.
    origin = str(request_data.get("origin") or request.base_url).rstrip("/")

    async def on_connection(connection: SmallWebRTCConnection):
        background_tasks.add_task(run_bot, connection, lang, origin)

    return await webrtc.handle_web_request(
        SmallWebRTCRequest.from_dict({k: v for k, v in body.items() if k in {"sdp", "type", "pc_id", "restart_pc", "request_data", "requestData"}}),
        on_connection,
    )


app.mount("/static", StaticFiles(directory=STATIC), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    logger.info(f"Demo running on http://localhost:{port}")
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=port)
