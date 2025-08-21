import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import config
from app.core.db import database
from app.routers import webhook, admin, testRouter
from app.flowsOperations.routers import testFlow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

app = FastAPI(title="WhatsApp Automation (FastAPI - stateless)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# mount routers
app.include_router(webhook.router)
app.include_router(admin.router)
app.include_router(testRouter.router)
app.include_router(testFlow.router)
