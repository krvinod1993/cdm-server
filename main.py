import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from routers import dealer, car, auth

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CDM Server", version="1.0.0")

# Serve uploaded images at /uploads
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(dealer.router)
app.include_router(car.router)


@app.get("/health")
def health_check():
    return {"status": "Server running clean"}
