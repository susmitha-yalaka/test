# app/main.py
import logging
from fastapi import FastAPI
from app.core.logconfig import configure_logging
from app.routers import orders, inventory, products, webhook
from app.flows_operations.routers import test_flow
from app.core.database import init_db, check_db_connection

# Basic logging config
configure_logging()


app = FastAPI(title="Boutique Flow Backend", version="1.0.0")

# Routers
app.include_router(test_flow.router, prefix="/flows", tags=["flows"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(webhook.router, prefix="", tags=["webhook"])


@app.on_event("startup")
def on_startup():
    check_db_connection()
    init_db()
    logging.getLogger("app.main").info("Startup complete.")
