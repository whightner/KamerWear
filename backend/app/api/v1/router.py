from fastapi import APIRouter

from app.api.v1.endpoints import (
    addresses,
    auth,
    cart,
    categories,
    checkout,
    health,
    orders,
    products,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(addresses.router)
api_router.include_router(cart.router)
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
