from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.database import get_db
from app.models import Product, StockReservation
from app.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    AvailabilityResponse,
    StockReservationRequest,
    StockReservationResponse
)

router = APIRouter(
    prefix="/products",
    tags=["Products & Inventory"]
)


# 1. Create Product
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    new_product = Product(**product.model_dump())

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


# 2. Get All Products
@router.get("", response_model=list[ProductResponse])
def get_products(db: Session = Depends(get_db)):

    return db.query(Product).order_by(Product.id).all()


# 3. Get Product By ID
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


# 4. Update Product
@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    updates = product_data.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)

    return product


# 5. Check Product Availability
@router.get(
    "/{product_id}/availability",
    response_model=AvailabilityResponse
)
def check_availability(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return AvailabilityResponse(
        product_id=product.id,
        available=product.stock_quantity > 0,
        available_quantity=product.stock_quantity
    )


# 6. Reserve Product Stock
@router.post(
    "/{product_id}/reservations",
    response_model=StockReservationResponse,
    status_code=status.HTTP_201_CREATED
)
def reserve_stock(
    product_id: int,
    request: StockReservationRequest,
    db: Session = Depends(get_db)
):

    # Check whether this order already has a reservation.
    existing = db.query(StockReservation).filter(
        StockReservation.order_reference == request.order_reference
    ).first()

    if existing:
        if (
            existing.product_id != product_id
            or existing.quantity != request.quantity
        ):
            raise HTTPException(
                status_code=409,
                detail="Order reference already used for a different reservation"
            )

        return StockReservationResponse(
            reservation_id=existing.id,
            order_reference=existing.order_reference,
            product_id=existing.product_id,
            quantity=existing.quantity,
            status=existing.status
        )

    # Atomically decrement stock only if enough stock exists.
    result = db.execute(
        update(Product)
        .where(
            Product.id == product_id,
            Product.stock_quantity >= request.quantity
        )
        .values(
            stock_quantity=Product.stock_quantity - request.quantity
        )
    )

    if result.rowcount == 0:

        db.rollback()

        product = db.query(Product).filter(
            Product.id == product_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        raise HTTPException(
            status_code=409,
            detail="Insufficient stock available"
        )

    reservation = StockReservation(
        order_reference=request.order_reference,
        product_id=product_id,
        quantity=request.quantity,
        status="RESERVED"
    )

    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return StockReservationResponse(
        reservation_id=reservation.id,
        order_reference=reservation.order_reference,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=reservation.status
    )


# 7. Release Reserved Stock
@router.post(
    "/{product_id}/reservations/{reservation_id}/release",
    response_model=StockReservationResponse
)
def release_stock(
    product_id: int,
    reservation_id: str,
    db: Session = Depends(get_db)
):

    reservation = db.query(StockReservation).filter(
        StockReservation.id == reservation_id,
        StockReservation.product_id == product_id
    ).with_for_update().first()

    if not reservation:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    if reservation.status == "RELEASED":
        return StockReservationResponse(
            reservation_id=reservation.id,
            order_reference=reservation.order_reference,
            product_id=reservation.product_id,
            quantity=reservation.quantity,
            status=reservation.status
        )

    if reservation.status != "RESERVED":
        raise HTTPException(
            status_code=409,
            detail="Reservation cannot be released"
        )

    db.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(
            stock_quantity=Product.stock_quantity + reservation.quantity
        )
    )

    reservation.status = "RELEASED"

    db.commit()
    db.refresh(reservation)

    return StockReservationResponse(
        reservation_id=reservation.id,
        order_reference=reservation.order_reference,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=reservation.status
    )
