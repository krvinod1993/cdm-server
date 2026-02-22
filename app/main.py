from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import UPLOAD_DIR
from app.db.base import Base
from app.db.session import engine
from app.models import City, Dealer, Vehicle, VehicleCategory  # noqa: F401 — register models with Base
from app.routers import auth, city, dealer, car, leads, staff, permissions, vehicle_categories, public_vehicle_router

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CDM Server", version="1.0.0")

# Serve uploaded images at /uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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
app.include_router(staff.router)
app.include_router(permissions.router)
app.include_router(vehicle_categories.router)
app.include_router(public_vehicle_router.router)


@app.get("/health")
def health_check():
    return {"status": "Server running clean"}
