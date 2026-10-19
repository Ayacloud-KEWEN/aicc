"""Online payment with Stripe Checkout (test mode for the demo).

Card details are typed on Stripe's hosted page only: neither this server nor the AI
ever sees them. There is no webhook (the Raspberry Pi is only reachable on Tailscale),
so payment status is read back from Stripe: when the success page loads and while the
call page polls an unpaid order.

PAYMENT_MODE=stripe enables it (needs STRIPE_SECRET_KEY); anything else = pay at pickup.
"""

import os
from collections.abc import Awaitable, Callable

import stripe
from loguru import logger

from restaurant import store

# Calls waiting for a payment: order_id -> coroutine that tells the AI and the page.
payment_listeners: dict[str, Callable[[dict], Awaitable[None]]] = {}


def enabled() -> bool:
    return os.getenv("PAYMENT_MODE", "pickup").lower() == "stripe"


def _client() -> stripe.StripeClient:
    return stripe.StripeClient(os.environ["STRIPE_SECRET_KEY"])


async def create_checkout(order: dict, origin: str) -> dict:
    """Create a Checkout Session for an order; returns {"id", "url"}."""
    session = await _client().v1.checkout.sessions.create_async(
        params={
            "mode": "payment",
            "line_items": [
                {
                    "quantity": line["quantity"],
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": round(line["unit_price"] * 100),
                        "product_data": {"name": line["name"] + (f" ({line['note']})" if line["note"] else "")},
                    },
                }
                for line in order["lines"]
            ],
            "metadata": {"order_id": order["id"]},
            "client_reference_id": order["id"],
            "success_url": f"{origin}/?paid={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{origin}/?cancelled={order['id']}",
        }
    )
    return {"id": session.id, "url": session.url}


async def _mark_paid(order: dict) -> dict:
    updated = store.update_order(order["id"], payment="paid")
    logger.info(f"Order {order['id']} paid")
    listener = payment_listeners.pop(order["id"], None)
    if listener:
        await listener(updated)
    return updated


async def refresh(order: dict) -> dict:
    """Ask Stripe whether a pending order has been paid; update it if so."""
    if order.get("payment") != "pending" or not order.get("payment_session_id") or not enabled():
        return order
    session = await _client().v1.checkout.sessions.retrieve_async(order["payment_session_id"])
    if session.payment_status == "paid":
        return await _mark_paid(order)
    return order


async def confirm_session(session_id: str) -> dict | None:
    """Called by the success page with Stripe's session id; returns the order."""
    session = await _client().v1.checkout.sessions.retrieve_async(session_id)
    order = store.get_order((session.metadata or {}).get("order_id", ""))
    if not order:
        return None
    if session.payment_status == "paid" and order.get("payment") == "pending":
        return await _mark_paid(order)
    return order
