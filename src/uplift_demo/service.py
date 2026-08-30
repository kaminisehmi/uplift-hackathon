from typing import List

from .models import Order
from .settings import AppSettings

settings = AppSettings()


def load_order(payload: dict) -> Order:
    return Order.model_validate(payload)


def load_order_json(raw: str) -> Order:
    return Order.model_validate_json(raw)


def order_subtotal(order: Order) -> float:
    return sum(item.quantity * item.unit_price for item in order.items)


def order_total(order: Order) -> float:
    taxed = (order_subtotal(order) - order.discount) * (1 + settings.tax_rate)
    return round(taxed, 2)


def apply_discount(order: Order, amount: float) -> Order:
    return order.model_copy(update={"discount": amount})


def order_summary(order: Order) -> dict:
    data = order.model_dump()
    return {
        "order_id": data["order_id"],
        "customer_email": data["customer"]["email"],
        "item_count": len(data["items"]),
        "total": order_total(order),
        "currency": settings.currency,
    }


def export_order(order: Order) -> str:
    return order.model_dump_json()


def order_schema() -> dict:
    return Order.model_json_schema()


def top_skus(orders: List[Order], limit: int = 3) -> List[str]:
    counts: dict = {}
    for order in orders:
        for item in order.items:
            counts[item.sku] = counts.get(item.sku, 0) + item.quantity
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [sku for sku, _ in ranked[:limit]]
