import json

from uplift_demo import service
from uplift_demo.models import Order


PAYLOAD = {
    "order_id": "ORD-2002",
    "customer": {"name": "Grace Hopper", "email": "grace@example.com"},
    "items": [
        {"sku": "SKU-COBOL", "quantity": 1, "unit_price": 100.0},
        {"sku": "SKU-NAVY", "quantity": 3, "unit_price": 10.0},
    ],
    "discount": 30.0,
}


def test_load_order_from_dict():
    order = service.load_order(PAYLOAD)
    assert isinstance(order, Order)
    assert order.customer.email == "grace@example.com"


def test_load_order_from_json():
    order = service.load_order_json(json.dumps(PAYLOAD))
    assert order.order_id == "ORD-2002"


def test_subtotal_and_total():
    order = service.load_order(PAYLOAD)
    assert service.order_subtotal(order) == 130.0
    assert service.order_total(order) == 108.0  # (130 - 30) * 1.08


def test_apply_discount_returns_updated_copy():
    order = service.load_order(PAYLOAD)
    updated = service.apply_discount(order, 50.0)
    assert updated.discount == 50.0
    assert order.discount == 30.0


def test_order_summary_shape():
    order = service.load_order(PAYLOAD)
    summary = service.order_summary(order)
    assert summary == {
        "order_id": "ORD-2002",
        "customer_email": "grace@example.com",
        "item_count": 2,
        "total": 108.0,
        "currency": "USD",
    }


def test_export_order_round_trips():
    order = service.load_order(PAYLOAD)
    raw = service.export_order(order)
    again = service.load_order_json(raw)
    assert again == order


def test_schema_lists_required_fields():
    schema = service.order_schema()
    assert set(schema["required"]) >= {"order_id", "customer", "items"}


def test_top_skus_ranked_by_quantity():
    orders = [service.load_order(PAYLOAD), service.load_order(PAYLOAD)]
    assert service.top_skus(orders, limit=1) == ["SKU-NAVY"]
