import json
import time
from datetime import datetime, timezone


# Expiration times in seconds
SESSION_TTL = 604800
CART_TTL = 604800
RECENT_TTL = 2592000
STOCK_TTL = 86400
RECENT_LIMIT = 50


# User sessions
def save_session(r, session_id, user_id, device):
    key = f"session:{session_id}"
    with r.pipeline(transaction=True) as pipe:
        pipe.hset(key, mapping={
            "user_id": user_id,
            "device": device
        })
        pipe.expire(key, SESSION_TTL)
        pipe.execute()


def get_session(r, session_id):
    data = r.hgetall(f"session:{session_id}")
    if not data:
        return None
    return {
        "user_id": int(data["user_id"]),
        "device": data["device"]
    }


def delete_session(r, session_id):
    r.delete(f"session:{session_id}")


# Active cart cache
def save_cart(r, user_id, cart_id, items, last_device):
    cart = {
        "cart_id": cart_id,
        "items": items,
        "last_device": last_device,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    r.set(
        f"cart:{user_id}",
        json.dumps(cart),
        ex=CART_TTL
    )


def get_cart(r, user_id):
    data = r.get(f"cart:{user_id}")
    return json.loads(data) if data else None


def invalidate_cart(r, user_id):
    r.delete(f"cart:{user_id}")


# Recently viewed products
def add_recent_view(r, user_id, product_id, viewed_at=None):
    key = f"recent:{user_id}"
    timestamp = time.time() if viewed_at is None else viewed_at

    r.zadd(key, {str(product_id): timestamp})

    count = r.zcard(key)
    if count > RECENT_LIMIT:
        r.zremrangebyrank(key, 0, count - RECENT_LIMIT - 1)

    r.expire(key, RECENT_TTL)


def get_recent_views(r, user_id, limit=5):
    products = r.zrevrange(f"recent:{user_id}", 0, limit - 1)
    return [int(product_id) for product_id in products]


# Inventory cache
def cache_stock(r, variant_id, quantity):
    r.set(
        f"stock:{variant_id}",
        quantity,
        ex=STOCK_TTL
    )


def get_cached_stock(r, variant_id):
    quantity = r.get(f"stock:{variant_id}")
    return int(quantity) if quantity is not None else None


def invalidate_stock(r, variant_id):
    r.delete(f"stock:{variant_id}")
