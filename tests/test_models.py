import pytest
from pydantic import ValidationError

from uplift_demo.models import Customer, Order, OrderItem


def make_order(**overrides):
    payload = {
        "order_id": "ORD-1001",
        "customer": {"name": "  Ada Lovelace ", "email": "ada@example.com"},
        "items": [
            {"sku": "SKU-APPLE", "quantity": 2, "unit_price": 3.50},
            {"sku": "SKU-PEAR", "quantity": 1, "unit_price": 5.00},
        ],
    }
    payload.update(overrides)
    return Order(**payload)


def test_valid_order_parses():
    order = make_order()
    assert order.order_id == "ORD-1001"
    assert len(order.items) == 2


def test_customer_name_is_stripped():
    order = make_order()
    assert order.customer.name == "Ada Lovelace"


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        Customer(name="Bob", email="not-an-email")


def test_quantity_must_be_positive():
    with pytest.raises(ValidationError):
        OrderItem(sku="SKU-X1", quantity=0, unit_price=1.0)


def test_order_requires_at_least_one_item():
    with pytest.raises(ValidationError):
        make_order(items=[])


def test_order_id_must_have_prefix():
    with pytest.raises(ValidationError):
        make_order(order_id="1001")


def test_discount_cannot_exceed_subtotal():
    with pytest.raises(ValidationError):
        make_order(discount=999.0)


def test_order_items_are_immutable():
    order = make_order()
    with pytest.raises(ValidationError):
        order.items[0].quantity = 99
