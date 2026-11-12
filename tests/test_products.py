def create_sample_product(client, stock=50):
    response = client.post(
        "/products",
        json={
            "name": "Wireless Mouse",
            "description": "Bluetooth wireless mouse",
            "price": 799.00,
            "stock_quantity": stock
        }
    )
    return response


def test_create_product(client):
    response = create_sample_product(client)

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Wireless Mouse"
    assert data["price"] == "799.00"
    assert data["stock_quantity"] == 50


def test_get_product(client):
    create_response = create_sample_product(client)
    product_id = create_response.json()["id"]

    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Wireless Mouse"


def test_get_all_products(client):
    create_sample_product(client)

    response = client.get("/products")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_check_product_availability(client):
    create_response = create_sample_product(client)
    product_id = create_response.json()["id"]

    response = client.get(
        f"/products/{product_id}/availability"
    )

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["available_quantity"] == 50


def test_reserve_stock(client):
    create_response = create_sample_product(client)
    product_id = create_response.json()["id"]

    response = client.post(
        f"/products/{product_id}/reservations",
        json={
            "order_reference": "TEST-ORDER-001",
            "quantity": 3
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["order_reference"] == "TEST-ORDER-001"
    assert data["quantity"] == 3
    assert data["status"] == "RESERVED"

    availability = client.get(
        f"/products/{product_id}/availability"
    )

    assert availability.json()["available_quantity"] == 47


def test_reject_reservation_when_stock_insufficient(client):
    create_response = create_sample_product(client, stock=5)
    product_id = create_response.json()["id"]

    response = client.post(
        f"/products/{product_id}/reservations",
        json={
            "order_reference": "TEST-ORDER-002",
            "quantity": 10
        }
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient stock available"

    availability = client.get(
        f"/products/{product_id}/availability"
    )

    assert availability.json()["available_quantity"] == 5


def test_update_product(client):
    create_response = create_sample_product(client)
    product_id = create_response.json()["id"]

    response = client.put(
        f"/products/{product_id}",
        json={
            "name": "Updated Wireless Mouse",
            "price": 899.00
        }
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Wireless Mouse"
    assert response.json()["price"] == "899.00"


def test_release_reserved_stock(client):
    create_response = create_sample_product(client)
    product_id = create_response.json()["id"]

    reservation_response = client.post(
        f"/products/{product_id}/reservations",
        json={
            "order_reference": "TEST-RELEASE-001",
            "quantity": 5
        }
    )

    assert reservation_response.status_code == 201

    reservation_id = reservation_response.json()["reservation_id"]

    release_response = client.post(
        f"/products/{product_id}/reservations/{reservation_id}/release"
    )

    assert release_response.status_code == 200

    availability = client.get(
        f"/products/{product_id}/availability"
    )

    assert availability.json()["available_quantity"] == 50


def test_reservation_idempotency(client):
    create_response = create_sample_product(client)
    product_id = create_response.json()["id"]

    payload = {
        "order_reference": "TEST-IDEMPOTENT-001",
        "quantity": 5
    }

    first_response = client.post(
        f"/products/{product_id}/reservations",
        json=payload
    )

    second_response = client.post(
        f"/products/{product_id}/reservations",
        json=payload
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    availability = client.get(
        f"/products/{product_id}/availability"
    )

    assert availability.json()["available_quantity"] == 45
