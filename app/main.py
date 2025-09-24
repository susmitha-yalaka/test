from fastapi import FastAPI
from app.routers import orders, inventory, products
from app.flows_operations.routers import test_flow
from app.core.database import init_db

app = FastAPI(title="Boutique Flow Backend", version="1.0.0")

# Routers
app.include_router(test_flow.router, prefix="/flows", tags=["flows"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(products.router, prefix="/products", tags=["products"])


@app.on_event("startup")
async def on_startup():
    await init_db()
