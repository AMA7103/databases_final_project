import argparse
import csv
import json
import random
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone, time as clock_time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from faker import Faker


TABLES = {
    "users": "user_id full_name email created_at",
    "addresses": "address_id user_id recipient_name line1 line2 city region postal_code country_code",
    "categories": "category_id name slug",
    "products": "product_id category_id name description base_price return_allowed return_window_days restocking_fee_percent is_active created_at",
    "product_variants": "variant_id product_id sku size color price stock_quantity is_active",
    "carts": "cart_id user_id status last_device created_at updated_at",
    "cart_items": "cart_id variant_id quantity added_at",
    "shipping_options": "shipping_option_id name base_cost min_delivery_days max_delivery_days is_active",
    "orders": "order_id user_id cart_id shipping_address_id billing_address_id shipping_option_id status placed_at subtotal tax_amount shipping_amount total_amount expected_ship_date expected_delivery_date shipped_at delivered_at tracking_number",
    "order_items": "order_item_id order_id variant_id product_name_snapshot quantity unit_price",
    "payments": "payment_id order_id method_type provider provider_token provider_transaction_id status amount created_at paid_at",
    "returns": "return_id order_item_id quantity resolution exchange_variant_id status refund_status exchange_status refund_amount restocking_fee return_shipping_method return_tracking_number return_label_url requested_at completed_at",
}

CATEGORIES = [
    (1, "Headphones", "headphones"),
    (2, "Fashion", "fashion"),
    (3, "Home Décor", "home-decor"),
    (4, "Electronics", "electronics"),
    (5, "Kitchen", "kitchen"),
    (6, "Beauty", "beauty"),
    (7, "Sports", "sports"),
    (8, "Books", "books"),
]

SHIPPING = [
    (1, "Standard", "5.99", 5, 8),
    (2, "Express", "12.99", 2, 4),
    (3, "Overnight", "24.99", 1, 1)
]

SEARCH_TERMS = [
    "wireless headphones", "summer dress", "ceramic vase",
    "blue dress", "gift ideas", "running shoes",
    "Bluetooth headphones", "home decor"
]

DEVICES = ["laptop", "tablet", "phone"]


def sql_time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")


def money(value):
    return f"{value.quantize(Decimal('0.01')):.2f}"


def write_json(handle, value):
    handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def generate(args):
    if args.users < 2 or args.products < 3 or args.orders < 7 or args.events < 14:
        raise ValueError("Use at least 2 users, 3 products, 7 orders, and 14 events")

    rng = random.Random(args.seed)
    fake = Faker("en_US")
    fake.seed_instance(args.seed)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)
    out = Path(args.output)

    for directory in ("mysql", "mongodb", "redis"):
        (out / directory).mkdir(parents=True, exist_ok=True)

    def between(earliest, latest=now):
        earliest = max(earliest, start)
        seconds = max(0, (latest - earliest).total_seconds())
        return earliest + timedelta(seconds=rng.random() * seconds)

    with ExitStack() as stack:
        writers = {}

        for table, names in TABLES.items():
            handle = stack.enter_context(
                open(out / "mysql" / f"{table}.csv", "w", newline="", encoding="utf-8")
            )
            writers[table] = csv.DictWriter(handle, fieldnames=names.split())
            writers[table].writeheader()

        product_file = stack.enter_context(
            open(out / "mongodb" / "product_attributes.jsonl", "w", encoding="utf-8")
        )
        event_file = stack.enter_context(
            open(out / "mongodb" / "events.jsonl", "w", encoding="utf-8")
        )
        session_file = stack.enter_context(
            open(out / "redis" / "sessions.jsonl", "w", encoding="utf-8")
        )

        def write(table, row):
            writers[table].writerow(row)

        # Users and addresses
        joined = {}

        for uid in range(1, args.users + 1):
            name = "Sarah" if uid == 1 else fake.name()
            created = start if uid == 1 else between(
                start, start + timedelta(days=240)
            )
            joined[uid] = created

            write("users", dict(
                user_id=uid,
                full_name=name,
                email=f"user{uid}@example.test",
                created_at=sql_time(created)
            ))

            write("addresses", dict(
                address_id=uid,
                user_id=uid,
                recipient_name=name,
                line1=fake.street_address(),
                line2="",
                city=fake.city(),
                region=fake.state_abbr(),
                postal_code=fake.postcode(),
                country_code="US"
            ))

        for cid, name, slug in CATEGORIES:
            write("categories", dict(
                category_id=cid, name=name, slug=slug
            ))

        for sid, name, cost, low, high in SHIPPING:
            write("shipping_options", dict(
                shipping_option_id=sid,
                name=name,
                base_cost=cost,
                min_delivery_days=low,
                max_delivery_days=high,
                is_active=1
            ))

        # Products and variants
        titles = {
            1: ["Wireless Headphones", "Studio Headphones", "Noise-Cancelling Headphones"],
            2: ["Summer Dress", "Cotton Dress", "Casual Dress"],
            3: ["Ceramic Vase", "Stoneware Vase", "Decorative Vase"],
            4: ["Portable Speaker", "Smart Lamp", "USB-C Charger"],
            5: ["Chef Knife", "Coffee Grinder", "Cutting Board"],
            6: ["Face Moisturizer", "Skin Cleanser", "Hair Brush"],
            7: ["Running Shoes", "Yoga Mat", "Water Bottle"],
            8: ["Paperback Novel", "Cookbook", "Notebook"]
        }

        variants = defaultdict(list)
        prices = {}
        product_names = {}
        restocking = {}
        next_variant = 1

        for pid in range(1, args.products + 1):
            cid, _, slug = CATEGORIES[(pid - 1) % len(CATEGORIES)]

            label = {
                1: "Wireless Headphones",
                2: "Summer Dress",
                3: "Ceramic Vase"
            }.get(pid)

            label = label or f"{rng.choice(titles[cid])} {pid:05d}"
            base = Decimal(rng.randrange(1200, 22000)) / 100
            restock = Decimal("5.00") if cid == 2 else Decimal("0.00")

            product_names[pid] = label
            restocking[pid] = restock

            write("products", dict(
                product_id=pid,
                category_id=cid,
                name=label,
                description=f"{label} for everyday use",
                base_price=money(base),
                return_allowed=1,
                return_window_days=30,
                restocking_fee_percent=money(restock),
                is_active=1,
                created_at=sql_time(start)
            ))

            if cid == 2:
                choices = [
                    (size, color)
                    for color in ("blue", "aqua-blue", "black")
                    for size in ("Small", "Medium", "Large")
                ]
                attributes = {
                    "material": rng.choice(["cotton", "linen", "polyester"]),
                    "style": "summer dress",
                    "care_instructions": "Machine wash cold"
                }

            elif cid == 1:
                choices = [(None, color) for color in ("black", "blue")]
                attributes = {
                    "battery_life_hours": rng.choice([20, 30, 40]),
                    "connectivity": "Bluetooth",
                    "weight_grams": 250,
                    "noise_cancellation": True
                }

            elif cid == 3:
                choices = [(None, color) for color in ("white", "blue")]
                attributes = {
                    "material": "ceramic",
                    "ceramic_type": "stoneware",
                    "height_cm": 26,
                    "width_cm": 15,
                    "weight_grams": 1200,
                    "care_instructions": "Hand wash only"
                }

            else:
                choices = [(None, None)]
                attributes = {
                    "brand": rng.choice(["North", "Atlas", "Willow"]),
                    "description": f"Specifications for {label}"
                }

            for size, color in choices:
                vid = next_variant
                next_variant += 1

                price = base + Decimal(rng.randrange(0, 500)) / 100
                prices[vid] = price
                variants[pid].append((vid, size, color))

                stock = rng.randrange(0, 36)
                if pid == 1:
                    stock = 3
                elif pid in (2, 3):
                    stock = max(4, stock)

                write("product_variants", dict(
                    variant_id=vid,
                    product_id=pid,
                    sku=f"SKU-{vid:07d}",
                    size=size or "",
                    color=color or "",
                    price=money(price),
                    stock_quantity=stock,
                    is_active=1
                ))

            write_json(product_file, {
                "product_id": pid,
                "category_slug": slug,
                "attributes": attributes,
                "image_urls": [f"/static/products/{pid}.jpg"],
                "visualization": {
                    "dimensions_cm": [15, 15, 26],
                    "compare_to": "coffee mug"
                } if cid == 3 else {}
            })

        def pick_variant(pid, size=None, color=None):
            matches = [
                v for v in variants[pid]
                if (size is None or v[1] == size)
                and (color is None or v[2] == color)
            ]
            return rng.choice(matches)[0]

        # Orders, converted carts, payments, and returns
        order_item_id = 0
        return_id = 0
        carts_by_user = defaultdict(list)
        sarah_ages = [340, 280, 210, 130, 40, 18, 5]

        for oid in range(1, args.orders + 1):
            sarah_order = oid <= 7
            uid = 1 if sarah_order else rng.randint(1, args.users)

            placed = (
                now - timedelta(days=sarah_ages[oid - 1])
                if sarah_order else between(joined[uid])
            )
            age = (now - placed).days

            if sarah_order and oid in (4, 5):
                status = "delivered"
            elif age >= 14:
                status = rng.choices(["delivered", "cancelled"], [96, 4])[0]
            elif age >= 5:
                status = rng.choice(["shipped", "processing"])
            else:
                status = rng.choice(["placed", "paid", "processing"])

            cart_created = max(
                joined[uid], placed - timedelta(hours=rng.randint(1, 72))
            )
            device = "tablet" if sarah_order and oid == 5 else rng.choice(DEVICES)

            write("carts", dict(
                cart_id=oid,
                user_id=uid,
                status="converted",
                last_device=device,
                created_at=sql_time(cart_created),
                updated_at=sql_time(placed)
            ))
            carts_by_user[uid].append((oid, cart_created))

            if oid == 5:
                product_ids = [1, 2, 3]
            elif oid == 4:
                product_ids = [2]
            else:
                product_ids = rng.sample(
                    range(1, args.products + 1),
                    min(rng.randint(1, 3), args.products)
                )

            items = []
            subtotal = Decimal("0.00")

            for pid in product_ids:
                if oid == 5 and pid == 2:
                    vid = pick_variant(pid, "Small", "aqua-blue")
                elif oid == 4 and pid == 2:
                    vid = pick_variant(pid, "Large", "blue")
                else:
                    vid = pick_variant(pid)

                quantity = rng.randint(1, 2)
                unit_price = prices[vid]
                subtotal += unit_price * quantity
                order_item_id += 1

                items.append((order_item_id, pid, vid, quantity, unit_price))

                write("cart_items", dict(
                    cart_id=oid,
                    variant_id=vid,
                    quantity=quantity,
                    added_at=sql_time(cart_created)
                ))

                write("order_items", dict(
                    order_item_id=order_item_id,
                    order_id=oid,
                    variant_id=vid,
                    product_name_snapshot=product_names[pid],
                    quantity=quantity,
                    unit_price=money(unit_price)
                ))

            ship_id = 2 if oid == 5 else rng.randint(1, 3)
            ship_cost = Decimal(SHIPPING[ship_id - 1][2])
            tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))
            total = subtotal + tax + ship_cost

            expected_ship = (placed + timedelta(days=2)).date()
            expected_delivery = (
                placed + timedelta(days=SHIPPING[ship_id - 1][4] + 2)
            ).date()

            shipped = status in ("shipped", "delivered")
            delivered = status == "delivered"

            write("orders", dict(
                order_id=oid,
                user_id=uid,
                cart_id=oid,
                shipping_address_id=uid,
                billing_address_id=uid,
                shipping_option_id=ship_id,
                status=status,
                placed_at=sql_time(placed),
                subtotal=money(subtotal),
                tax_amount=money(tax),
                shipping_amount=money(ship_cost),
                total_amount=money(total),
                expected_ship_date=expected_ship,
                expected_delivery_date=expected_delivery,
                shipped_at=sql_time(placed + timedelta(days=2)) if shipped else "",
                delivered_at=sql_time(
                    placed + timedelta(days=SHIPPING[ship_id - 1][4] + 2)
                ) if delivered else "",
                tracking_number=f"TRK{oid:012d}" if shipped else ""
            ))

            has_refund = False

            for item_id, pid, vid, quantity, unit_price in items:
                special_refund = oid == 4 and pid == 2
                special_exchange = oid == 5 and pid == 2
                random_return = delivered and age >= 25 and rng.random() < 0.012

                if not (special_refund or special_exchange or random_return):
                    continue

                return_id += 1
                exchange = special_exchange or (
                    random_return and rng.random() < 0.25
                )

                fee = (
                    Decimal("0.00") if exchange
                    else (unit_price * restocking[pid] / 100).quantize(Decimal("0.01"))
                )
                refund = Decimal("0.00") if exchange else unit_price - fee
                has_refund = has_refund or not exchange

                requested = min(
                    now - timedelta(days=1), placed + timedelta(days=12)
                )

                if special_exchange:
                    exchange_vid = pick_variant(pid, "Medium", "aqua-blue")
                else:
                    exchange_vid = pick_variant(pid) if exchange else ""

                write("returns", dict(
                    return_id=return_id,
                    order_item_id=item_id,
                    quantity=1,
                    resolution="exchange" if exchange else "refund",
                    exchange_variant_id=exchange_vid,
                    status="completed",
                    refund_status="not_applicable" if exchange else "processed",
                    exchange_status="completed" if exchange else "not_applicable",
                    refund_amount=money(refund),
                    restocking_fee=money(fee),
                    return_shipping_method="Prepaid label",
                    return_tracking_number=f"RET{return_id:012d}",
                    return_label_url=f"/returns/labels/{return_id}.pdf",
                    requested_at=sql_time(requested),
                    completed_at=sql_time(
                        min(now, requested + timedelta(days=5))
                    )
                ))

            payment_status = (
                "failed" if status == "cancelled"
                else "partially_refunded" if has_refund
                else "approved"
            )

            write("payments", dict(
                payment_id=oid,
                order_id=oid,
                method_type=(
                    "credit_card"
                    if sarah_order or rng.random() < 0.75
                    else "bank_account"
                ),
                provider="SyntheticPay",
                provider_token=f"tok_test_{oid:09d}",
                provider_transaction_id=f"txn_test_{oid:09d}",
                status=payment_status,
                amount=money(total),
                created_at=sql_time(placed),
                paid_at=sql_time(placed) if payment_status != "failed" else ""
            ))

        # Active and abandoned carts from the last 30 days
        extra_users = [1] + rng.sample(
            range(2, args.users + 1),
            min(5999, args.users - 1)
        )

        for idx, uid in enumerate(extra_users, start=1):
            cart_id = args.orders + idx
            created = between(max(joined[uid], now - timedelta(days=30)))
            status = "active" if uid == 1 or rng.random() < 0.6 else "abandoned"

            write("carts", dict(
                cart_id=cart_id,
                user_id=uid,
                status=status,
                last_device="laptop" if uid == 1 else rng.choice(DEVICES),
                created_at=sql_time(created),
                updated_at=sql_time(created)
            ))

            carts_by_user[uid].append((cart_id, created))

            if uid == 1:
                pids = [1, 2, 3]
            else:
                pids = rng.sample(
                    range(1, args.products + 1),
                    min(rng.randint(1, 3), args.products)
                )

            for pid in pids:
                vid = (
                    pick_variant(pid, "Medium", "aqua-blue")
                    if uid == 1 and pid == 2
                    else pick_variant(pid)
                )

                write("cart_items", dict(
                    cart_id=cart_id,
                    variant_id=vid,
                    quantity=rng.randint(1, 2),
                    added_at=sql_time(created)
                ))

        # Sessions for multiple devices
        session_by_user = {}
        primary_device = {}

        for uid in range(1, args.users + 1):
            devices = (
                ["tablet", "laptop"] if uid == 1
                else [rng.choice(DEVICES)]
            )
            primary_device[uid] = devices[0]

            for device in devices:
                sid = f"session-{uid}-{device}"
                session_by_user[(uid, device)] = sid

                write_json(session_file, {
                    "session_id": sid,
                    "user_id": uid,
                    "device": device
                })

        # Historical behavior events
        event_types = [
            "product_view", "product_click", "search",
            "cart_add", "cart_remove", "cart_update"
        ]
        weights = [55, 18, 15, 6, 3, 3]
        forced = []

        for days, pid, device in [
            (1, 1, "laptop"),
            (3, 2, "tablet"),
            (5, 3, "laptop"),
            (7, 1, "tablet"),
            (12, 2, "laptop"),
            (45, 3, "tablet")
        ]:
            forced.append(dict(
                user_id=1,
                product_id=pid,
                event_type="product_view",
                occurred_at=(now - timedelta(days=days)).isoformat(),
                device=device,
                session_id=session_by_user[(1, device)],
                duration_ms=45000,
                timezone="America/Chicago"
            ))

        chicago = ZoneInfo("America/Chicago")

        for days, hour, term in [
            (1, 2, "headphones"),
            (2, 8, "blue dress"),
            (3, 14, "headphones"),
            (5, 20, "ceramic vase"),
            (8, 10, "blue dress"),
            (12, 17, "headphones"),
            (16, 22, "summer dress"),
            (25, 4, "headphones")
        ]:
            local_date = (
                now.astimezone(chicago) - timedelta(days=days)
            ).date()

            local_dt = datetime.combine(
                local_date, clock_time(hour, 20), tzinfo=chicago
            )

            forced.append(dict(
                user_id=1,
                event_type="search",
                search_term=term,
                occurred_at=local_dt.astimezone(timezone.utc).isoformat(),
                device="laptop",
                session_id=session_by_user[(1, "laptop")],
                timezone="America/Chicago"
            ))

        for event_id in range(1, args.events + 1):
            if event_id > args.events - len(forced):
                index = event_id - (args.events - len(forced)) - 1
                event = forced[index]

            else:
                uid = rng.randint(1, args.users)
                kind = rng.choices(event_types, weights)[0]
                device = primary_device[uid]

                event = dict(
                    user_id=uid,
                    event_type=kind,
                    device=device,
                    timezone="America/Chicago"
                )

                if kind.startswith("cart_") and carts_by_user[uid]:
                    cart_id, cart_created = rng.choice(carts_by_user[uid])
                    event["cart_id"] = cart_id
                    timestamp = between(cart_created)
                else:
                    timestamp = between(joined[uid])

                event["occurred_at"] = timestamp.isoformat()
                event["session_id"] = session_by_user.get((uid, device))

                if kind == "search":
                    event["search_term"] = rng.choice(SEARCH_TERMS)
                else:
                    event["product_id"] = rng.randint(1, args.products)

                    if kind == "product_view":
                        event["duration_ms"] = rng.randrange(1000, 300001)

            write_json(event_file, {"event_id": event_id, **event})

    print(
        f"Generated {args.users:,} users, {args.products:,} products, "
        f"{args.orders:,} orders, and {args.events:,} events in {out}/"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate e-commerce synthetic data"
    )
    parser.add_argument("--users", type=int, default=10000)
    parser.add_argument("--products", type=int, default=5000)
    parser.add_argument("--orders", type=int, default=100000)
    parser.add_argument("--events", type=int, default=500000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data")
    generate(parser.parse_args())
