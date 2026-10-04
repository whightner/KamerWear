"""Restore the clean presentation state of a local demo database.

    python -m app.db.reset_demo --yes

DANGER: this deletes every user, order, return, support conversation and Fit
Profile in the configured database, then reloads the catalog. It refuses to
run without --yes, against a non-local database host (unless --allow-remote)
or when APP_ENV/ENVIRONMENT is "production".

It then creates:
- believable stock (most variants 8-24 units, a few low-stock and sold-out
  sizes to demonstrate the badges);
- accounts: an admin and a demo customer from DEMO_ADMIN_EMAIL /
  DEMO_ADMIN_PASSWORD and DEMO_CUSTOMER_EMAIL / DEMO_CUSTOMER_PASSWORD
  (environment only, never in the code), plus two fictional customers that
  can't log in (random passwords);
- six orders in useful states, one active and one refunded (demo) return, an
  open and a closed support conversation, all with professional text.

Everything is deterministic except generated references (KW-/KR-/KS-...).
Run it on the day of the presentation: the return window counts from the
(back-dated) delivery times it creates.
"""

import argparse
import json
import os
import secrets
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.create_admin import AdminCreationError, create_admin
from app.db.seed import CATALOG_FILE, CATEGORIES, seed_catalog
from app.db.session import SessionLocal
from app.models import (
    Address,
    AuthSession,
    Cart,
    CartItem,
    Category,
    FitEstimate,
    FitProfile,
    Inventory,
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Product,
    ProductVariant,
    ReturnReason,
    ReturnRequest,
    Role,
    SenderRole,
    SupportConversation,
    SupportSubject,
    User,
    UserProfile,
)
from app.schemas.auth import RegisterRequest
from app.schemas.orders import OrderCreate
from app.services import orders as order_service
from app.services import returns as return_service
from app.services import support as support_service
from app.services.auth import normalize_email

LOCAL_HOSTS = {None, "", "localhost", "127.0.0.1", "::1"}

# (slug, size, colour index) -> units. Everything else gets 8-24 units.
LOW_STOCK = {
    ("canvas-messenger-bag", None, 0): 3,
    ("urban-runner-02", "44", 0): 2,
    ("classic-hoodie", "XL", 0): 1,
    ("city-bomber-jacket", "XL", 0): 4,
    ("featherlight-puffer", "XS", 0): 5,
}
SOLD_OUT = {
    ("urban-runner-02", "45", 0),
    ("core-heavy-tee", "XXL", 0),
    ("everyday-cargo", "36", 0),
}

ADDRESS = {
    "label": "Home",
    "country_code": "CM",
    "region": "Littoral",
    "city": "Douala",
    "quarter": "Bonamoussadi",
    "street_or_landmark": "Rue des Palmiers, near the pharmacy",
}


def refuse(message: str) -> None:
    print(f"Refusing to reset: {message}", file=sys.stderr)
    raise SystemExit(2)


def check_safe(args) -> None:
    if not args.yes:
        refuse("this deletes all users and orders. Re-run with --yes to confirm.")
    env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    if env in {"prod", "production"}:
        refuse(f"APP_ENV/ENVIRONMENT is {env!r}.")
    url = make_url(settings.database_url)
    if url.host not in LOCAL_HOSTS and not args.allow_remote:
        refuse(f"database host {url.host!r} is not local (use --allow-remote if intended).")


def wipe(db: Session) -> None:
    """Deletes people, transactions and catalog rows that aren't in the seed data
    (e.g. products created while testing the admin). Order lines, returns,
    messages, variants and images cascade."""
    for model in (
        SupportConversation,
        ReturnRequest,
        Order,
        Cart,
        Address,
        FitEstimate,
        FitProfile,
        AuthSession,
        User,
    ):
        db.execute(delete(model))
    data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    db.execute(delete(Product).where(Product.slug.not_in([p["slug"] for p in data])))
    db.execute(delete(Category).where(Category.slug.not_in(list(CATEGORIES))))
    db.flush()


def presentation_stock(db: Session) -> dict[str, int]:
    counts = {"normal": 0, "low": 0, "sold_out": 0}
    products = db.scalars(select(Product).order_by(Product.id)).all()
    for product in products:
        colours = list(dict.fromkeys(v.color_name for v in product.variants))
        for variant in sorted(product.variants, key=lambda v: v.id):
            key = (product.slug, variant.size, colours.index(variant.color_name))
            inventory = variant.inventory or Inventory()
            variant.inventory = inventory
            inventory.reserved = 0
            if key in SOLD_OUT:
                inventory.on_hand, kind = 0, "sold_out"
            elif key in LOW_STOCK:
                inventory.on_hand, kind = LOW_STOCK[key], "low"
            else:
                inventory.on_hand, kind = 8 + (variant.id * 7) % 17, "normal"
            counts[kind] += 1
    db.flush()
    return counts


def make_customer(
    db: Session, email: str, password: str | None, first: str, last: str, phone: str
) -> tuple[User, bool]:
    """A customer account. Without a password it gets a random one (can't log in)."""
    usable = password is not None
    data = RegisterRequest(
        email=email,
        password=password or secrets.token_urlsafe(24),
        first_name=first,
        last_name=last,
    )
    user = User(
        email=normalize_email(str(data.email)),
        password_hash=hash_password(data.password),
        role=Role.customer,
        is_active=True,
        is_verified=False,
        profile=UserProfile(first_name=first, last_name=last, phone=phone),
    )
    db.add(user)
    db.flush()
    db.add(
        Address(
            user_id=user.id,
            recipient_name=f"{first} {last}",
            phone=phone,
            is_default=True,
            **ADDRESS,
        )
    )
    db.flush()
    return user, usable


def variant(db: Session, slug: str, size: str | None, colour: int = 0) -> ProductVariant:
    product = db.scalar(select(Product).where(Product.slug == slug))
    colours = list(dict.fromkeys(v.color_name for v in product.variants))
    return next(v for v in product.variants if v.size == size and v.color_name == colours[colour])


def place(db: Session, user: User, lines, method: PaymentMethod) -> Order:
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
    cart.items = [
        CartItem(variant_id=variant(db, *line[:3]).id, quantity=line[3]) for line in lines
    ]
    db.flush()
    address = db.scalar(select(Address).where(Address.user_id == user.id))
    order, _ = order_service.create_order(
        db, user, OrderCreate(address_id=address.id, payment_method=method), uuid.uuid4().hex
    )
    return order


STEPS = [
    OrderStatus.confirmed,
    OrderStatus.preparing,
    OrderStatus.shipped,
    OrderStatus.out_for_delivery,
    OrderStatus.delivered,
]
NOTES = {
    OrderStatus.confirmed: "Thank you! Your order is confirmed.",
    OrderStatus.shipped: "Handed to our Douala courier.",
    OrderStatus.out_for_delivery: "Your courier will call before arriving.",
    OrderStatus.delivered: "Delivered. Enjoy your new items!",
}


def advance(db: Session, order: Order, until: OrderStatus, admin: User) -> None:
    for status in STEPS:
        order_service.change_status(db, order, status, NOTES.get(status), changed_by=admin)
        if status == until:
            return


def backdate(db: Session, order: Order, start: datetime, step: timedelta) -> None:
    """Spreads the order's history over time so timelines look real."""
    order.created_at = start
    for index, event in enumerate(order.status_history):
        event.created_at = start + step * index
    db.flush()


def demo_data(db: Session, admin: User, amina: User, brice: User, clarisse: User) -> dict:
    now = datetime.now(UTC)
    hour = timedelta(hours=1)
    summary = {}

    a = place(
        db,
        amina,
        [("classic-hoodie", "M", 0, 1), ("core-joggers", "M", 0, 1)],
        PaymentMethod.mobile_money,
    )
    advance(db, a, OrderStatus.confirmed, admin)
    backdate(db, a, now - 20 * hour, 2 * hour)
    summary["Confirmed"] = a.order_number

    b = place(db, amina, [("urban-runner-02", "42", 0, 1)], PaymentMethod.card)
    advance(db, b, OrderStatus.shipped, admin)
    backdate(db, b, now - 52 * hour, 8 * hour)
    summary["Shipped"] = b.order_number

    c = place(
        db,
        amina,
        [("core-heavy-tee", "M", 0, 2), ("everyday-cargo", "32", 0, 1)],
        PaymentMethod.cash_on_delivery,
    )
    advance(db, c, OrderStatus.delivered, admin)
    order_service.change_payment_status(
        db, c, PaymentStatus.paid, "Cash collected by the courier.", changed_by=admin
    )
    backdate(db, c, now - 96 * hour, 10 * hour)
    summary["Delivered (return-eligible)"] = c.order_number

    d = place(db, amina, [("trail-zip-jacket", "M", 0, 1)], PaymentMethod.mobile_money)
    advance(db, d, OrderStatus.delivered, admin)
    backdate(db, d, now - 110 * hour, 10 * hour)
    active = return_service.create_return(
        db,
        amina,
        d.order_number,
        [
            return_service.NewItem(
                d.items[0].id,
                1,
                ReturnReason.wrong_size,
                "The sleeves are too short for me; I usually wear L.",
            )
        ],
        "Could I exchange it for size L if it is available?",
    )
    summary["Delivered + active return"] = f"{d.order_number} / {active.return_number}"

    e = place(db, brice, [("featherlight-puffer", "L", 0, 1)], PaymentMethod.card)
    advance(db, e, OrderStatus.delivered, admin)
    order_service.change_payment_status(
        db, e, PaymentStatus.paid, "Card payment confirmed (demo).", changed_by=admin
    )
    backdate(db, e, now - 140 * hour, 10 * hour)
    done = return_service.create_return(
        db,
        brice,
        e.order_number,
        [
            return_service.NewItem(
                e.items[0].id, 1, ReturnReason.damaged, "The zip is broken at the bottom."
            )
        ],
        None,
    )
    return_service.approve(db, done, admin, "Sorry about that. Please bring it to our Akwa shop.")
    return_service.receive(
        db,
        done,
        admin,
        {done.items[0].id: False},
        "Received. The zip is damaged, so the jacket can't be resold.",
        "Sent to the supplier as a defect.",
    )
    return_service.refund(
        db, done, admin, "Refund of 26 500 FCFA recorded.", mark_order_payment_refunded=True
    )
    summary["Delivered + refunded return (demo)"] = f"{e.order_number} / {done.return_number}"

    f = place(
        db,
        clarisse,
        [("sunset-zip-hoodie", "S", 0, 1), ("essential-v-tee", "S", 1, 2)],
        PaymentMethod.cash_on_delivery,
    )
    f.created_at = now - 2 * hour
    summary["New, awaiting confirmation"] = f.order_number

    conversation = support_service.create(
        db,
        amina,
        SupportSubject.delivery,
        "Hello, my Urban Runner 02 order has shipped. Could you tell me roughly when it "
        "will arrive in Bonamoussadi?",
        order_number=b.order_number,
    )
    db.flush()
    support_service.send(
        db,
        conversation,
        admin,
        SenderRole.store,
        "Hello Amina, your parcel left our Douala hub this morning. Our courier "
        "usually delivers in Bonamoussadi within 1 to 2 days and will call you "
        "before arriving.",
    )
    support_service.send(
        db, conversation, amina, SenderRole.customer, "Thank you! Can the courier come after 5 pm?"
    )
    times = [now - 30 * hour, now - 29 * hour, now - 3 * hour]
    for message, when in zip(conversation.messages, times, strict=True):
        message.created_at = when
    conversation.messages[0].read_at = conversation.messages[1].created_at
    conversation.messages[1].read_at = conversation.messages[2].created_at
    conversation.created_at = times[0]
    conversation.last_message_at = times[-1]
    summary["Open support conversation"] = conversation.conversation_number

    closed = support_service.create(
        db,
        brice,
        SupportSubject.return_question,
        "Hello, I have returned the Featherlight Puffer. When will the refund be done?",
        return_number=done.return_number,
    )
    db.flush()
    support_service.send(
        db,
        closed,
        admin,
        SenderRole.store,
        "Hello Brice, we received the jacket and recorded your refund today. "
        "Thank you for your patience.",
    )
    support_service.mark_read(db, closed, SenderRole.store)
    support_service.mark_read(db, closed, SenderRole.customer)
    support_service.close(db, closed)
    for message, when in zip(closed.messages, [now - 50 * hour, now - 48 * hour], strict=True):
        message.created_at = when
    closed.last_message_at = now - 48 * hour
    db.flush()
    return summary


def rebuild_visual_index(db: Session) -> str:
    try:
        from app.ai.encoder import EncoderUnavailable, get_encoder
        from app.services.visual_search import build_index

        encoder = get_encoder()
    except EncoderUnavailable:
        return (
            "model not available: run `python -m app.ai.prepare_visual_search` and "
            "`python -m app.ai.visual_search_index`"
        )
    result = build_index(db, encoder, trigger="cli")
    return f"rebuilt ({result})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset the local demo database.")
    parser.add_argument("--yes", action="store_true", help="confirm deleting all demo data")
    parser.add_argument("--allow-remote", action="store_true", help="allow a non-local host")
    args = parser.parse_args(argv)
    check_safe(args)

    env = os.environ.get
    for name in ("DEMO_ADMIN_PASSWORD", "DEMO_CUSTOMER_PASSWORD"):
        if (env(name) or "").startswith("CHANGE_ME"):
            refuse(f"{name} still has the placeholder from .env.example.")
    with SessionLocal() as db:
        wipe(db)
        counts = seed_catalog(db)
        stock = presentation_stock(db)
        db.commit()

        admin_email, admin_password = env("DEMO_ADMIN_EMAIL"), env("DEMO_ADMIN_PASSWORD")
        if admin_email and admin_password:
            try:
                admin = create_admin(db, admin_email, admin_password, "Store", "Manager")
            except AdminCreationError as exc:
                refuse(f"DEMO_ADMIN_*: {exc}")
            admin_note = f"admin {admin.email}"
        else:
            # Needed to sign the demo history; it can't log in (random password).
            admin = create_admin(
                db,
                "operations@example.com",
                secrets.token_urlsafe(24) + "aA1",
                "Store",
                "Operations",
            )
            admin_note = (
                "no DEMO_ADMIN_EMAIL/DEMO_ADMIN_PASSWORD: create one with "
                "`python -m app.db.create_admin`"
            )

        customer_email = env("DEMO_CUSTOMER_EMAIL") or "amina.demo@example.com"
        try:
            amina, usable = make_customer(
                db,
                customer_email,
                env("DEMO_CUSTOMER_PASSWORD"),
                "Amina",
                "Ndongo",
                "+237 6 77 10 20 30",
            )
        except ValueError as exc:
            refuse(f"DEMO_CUSTOMER_*: {exc}")
        brice, _ = make_customer(
            db, "brice.demo@example.com", None, "Brice", "Mbarga", "+237 6 99 40 50 60"
        )
        clarisse, _ = make_customer(
            db, "clarisse.demo@example.com", None, "Clarisse", "Fotso", "+237 6 55 70 80 90"
        )
        customer_email = amina.email
        summary = demo_data(db, admin, amina, brice, clarisse)
        db.commit()
        index = rebuild_visual_index(db)
        db.commit()

    print("Demo database reset.")
    print("  Catalog: " + ", ".join(f"{n} {k}" for k, n in counts.items()))
    print(f"  Stock: {stock['normal']} normal, {stock['low']} low, {stock['sold_out']} sold out")
    print(
        f"  Accounts: {admin_note}; customer {customer_email}"
        + ("" if usable else " (no DEMO_CUSTOMER_PASSWORD: can't log in)")
        + "; Brice Mbarga and Clarisse Fotso (fictional, no login)"
    )
    for label, value in summary.items():
        print(f"  {label}: {value}")
    print(f"  Visual search index: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
