from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import UPLOAD_DIR
from app.db.base import Base
from app.db.session import engine
from app.models import City, Dealer, Car  # noqa: F401 — register models with Base
from app.routers import auth, city, dealer, car, leads

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CDM Server", version="1.0.0")

# Serve uploaded images at /uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register routers
app.include_router(auth.router)
app.include_router(city.router)
app.include_router(dealer.router)
app.include_router(car.router)
app.include_router(leads.router)


@app.get("/health")
def health_check():
    return {"status": "Server running clean"}
