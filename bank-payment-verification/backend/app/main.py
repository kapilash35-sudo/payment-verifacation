from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routers import payments, webhooks, customers, websocket
from app.db.database import engine
from app.db import models
import os

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Automated Bank Payment Verification System")

os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/ela", exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Configure CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(websocket.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Payment Verification API"}
