from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service_cab import (
    VEHICLE_TYPE_MAPPING, EXTENDED_LOCATIONS, CITY_LIST,
    calculate_ride_estimate, generate_YJ_ride_confirmation
)
from connection import send_to_event_hub

app = FastAPI(title="YJ Cabs Ride Booking API", description="Professional ride booking system")

# Get directories
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")

# Ensure directories exist
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=templates_dir)

# Add custom static URL helper to all templates
def static_url(path: str):
    """Generate URL for static files"""
    return f"/static/{path}"

templates.env.globals['static_url'] = static_url

@app.get("/")
async def booking_home(request: Request):
    """Main booking page"""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/api/locations")
async def get_locations():
    """Get list of available locations"""
    return {"locations": list(set(EXTENDED_LOCATIONS))}

@app.get("/api/vehicle-types")
async def get_vehicle_types():
    """Get available vehicle types with pricing"""
    return {"vehicles": VEHICLE_TYPE_MAPPING}

@app.post("/api/estimate")
async def estimate_ride(origin: str = Form(...), destination: str = Form(...)):
    """Get fare estimates for all vehicle types"""
    estimates = []
    for vehicle in VEHICLE_TYPE_MAPPING:
        estimate = calculate_ride_estimate(origin, destination, vehicle)
        estimates.append({
            'vehicle_type_id': vehicle['vehicle_type_id'],
            'vehicle_type': vehicle['vehicle_type'],
            'description': vehicle['description'],
            'estimated_fare': estimate['fare'],
            'distance_miles': estimate['distance'],
            'duration_minutes': estimate['duration'],
            'surge_multiplier': estimate['surge'],
            'base_fare': estimate['base_fare'],
            'distance_fare': estimate['distance_fare'],
            'time_fare': estimate['time_fare']
        })
    return {"estimates": sorted(estimates, key=lambda x: x['estimated_fare'])}

@app.post("/api/book")
async def book_ride(
    origin: str = Form(...),
    destination: str = Form(...),
    vehicle_type: str = Form(...),
    estimated_fare: float = Form(...),
    distance: float = Form(...),
    duration: int = Form(...)
):
    """Book a ride and generate full confirmation data"""
    ride_data = generate_YJ_ride_confirmation(
        origin=origin,
        destination=destination,
        vehicle_type=vehicle_type,
        distance=distance,
        duration=duration
    )
    result = send_to_event_hub(ride_data)
    return {"success": True, "ride_confirmation": ride_data}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "YJ Booking API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)