from fastapi import FastAPI

from app.database import Base, engine
from app import models
from app.routes import products

# Create database tables during initial development.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="E-Commerce Product & Inventory Service",
    description="Microservice for product catalogue and inventory management",
    version="1.0.0"
)

app.include_router(products.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "service": "Product Service",
        "status": "healthy"
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to E-Commerce Product Service",
        "documentation": "/docs"
    }
