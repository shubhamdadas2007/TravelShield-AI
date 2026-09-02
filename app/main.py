import os
import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import engine, Base, get_db
from app.models import (
    User, Trip, ItineraryItem, Booking, TransportDetail, Disruption,
    RecoveryPlan, ItemStatus, ItemType, TransportType, PreferenceTier
)
from app.services.disruption_engine import DisruptionRecoveryEngine
from app.services.ai_engine import GeminiAIEngine
from app.services.transport_adapters import TrainServiceAdapter, BusServiceAdapter, FlightServiceAdapter, DEMO_MODE
from app.services.location_resolver import LocationResolver
from app.services.firebase_auth import get_current_user_from_firebase, FirebaseTokenVerifier

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TravelShield AI — Multimodal Disruption Recovery Engine",
    description="Dynamic AI Engine with Firebase Auth Email Verification & disruption recovery.",
    version="2.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_engine = GeminiAIEngine()
train_adapter = TrainServiceAdapter()
bus_adapter = BusServiceAdapter()
flight_adapter = FlightServiceAdapter()

# Pydantic Request Schemas
class DisruptionSimulateRequest(BaseModel):
    trip_id: int
    itinerary_item_id: int
    delay_minutes: int = 240
    disruption_type: str = "delay"
    description: Optional[str] = None

class ApplyPlanRequest(BaseModel):
    trip_id: int
    plan_id: int

class ChatRequest(BaseModel):
    trip_id: int
    user_message: str

class UserPreferenceRequest(BaseModel):
    trip_id: int
    preference: str

class SearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: Optional[str] = None
    passengers: int = 1
    transport_type: str = "all"
    sort_by: str = "cheapest"

class FirebaseAuthSyncRequest(BaseModel):
    token: str

# Seed Main Demo Scenario (Mumbai -> Pune -> Goa)
def seed_demo_data(db: Session) -> Trip:
    user = db.query(User).filter(User.email == "rahul@travelshield.ai").first()
    if not user:
        user = User(
            name="Rahul Sharma",
            email="rahul@travelshield.ai",
            preference=PreferenceTier.BALANCED.value,
            max_transfers=2
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    existing_trip = db.query(Trip).filter(Trip.user_id == user.id, Trip.title == "Mumbai → Pune → Goa Beach Getaway").first()
    if existing_trip:
        db.delete(existing_trip)
        db.commit()

    now = datetime.datetime.now().replace(microsecond=0)
    trip = Trip(
        user_id=user.id,
        title="Mumbai → Pune → Goa Beach Getaway",
        origin="Mumbai",
        destination="Goa",
        start_date=now.replace(hour=16, minute=10),
        end_date=now + datetime.timedelta(days=4),
        status="active"
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    leg1_dep = now.replace(hour=16, minute=10)
    leg1_arr = now.replace(hour=19, minute=30)
    item1 = ItineraryItem(
        trip_id=trip.id,
        sequence_order=1,
        item_type=ItemType.TRANSPORT.value,
        title="Train: Mumbai Central to Pune Junction",
        origin="Mumbai",
        destination="Pune",
        scheduled_departure=leg1_dep,
        scheduled_arrival=leg1_arr,
        estimated_departure=leg1_dep,
        estimated_arrival=leg1_arr,
        status=ItemStatus.CONFIRMED.value,
        price=420.0,
        notes="Deccan Queen Express (12123)"
    )
    db.add(item1)
    db.commit()
    db.refresh(item1)

    db.add(TransportDetail(
        itinerary_item_id=item1.id,
        transport_type=TransportType.TRAIN.value,
        carrier_name="Indian Railways",
        vehicle_number="12123",
        platform_or_gate="Platform 4",
        origin_station="Mumbai Central (MMCT)",
        dest_station="Pune Junction (PUNE)"
    ))
    db.add(Booking(
        itinerary_item_id=item1.id,
        booking_reference="PNR-8492019382",
        provider="IRCTC",
        seat_or_room="Coach C2, Seat 44"
    ))

    leg2_dep = now.replace(hour=20, minute=0)
    leg2_arr = (now + datetime.timedelta(days=1)).replace(hour=6, minute=30)
    item2 = ItineraryItem(
        trip_id=trip.id,
        sequence_order=2,
        item_type=ItemType.TRANSPORT.value,
        title="Bus: Pune to Goa (Panjim)",
        origin="Pune",
        destination="Goa",
        scheduled_departure=leg2_dep,
        scheduled_arrival=leg2_arr,
        estimated_departure=leg2_dep,
        estimated_arrival=leg2_arr,
        status=ItemStatus.CONFIRMED.value,
        price=1100.0,
        notes="IntrCity SmartBus Volvo A/C Sleeper"
    )
    db.add(item2)
    db.commit()
    db.refresh(item2)

    db.add(TransportDetail(
        itinerary_item_id=item2.id,
        transport_type=TransportType.BUS.value,
        carrier_name="IntrCity SmartBus",
        vehicle_number="MH12-SB-901",
        platform_or_gate="Bay 3, Swargate",
        origin_station="Swargate Bus Terminal, Pune",
        dest_station="Mapusa Bus Stand, Goa"
    ))
    db.add(Booking(
        itinerary_item_id=item2.id,
        booking_reference="BUS-IC-992018",
        provider="RedBus",
        seat_or_room="Lower Berth L12"
    ))

    item3 = ItineraryItem(
        trip_id=trip.id,
        sequence_order=3,
        item_type=ItemType.HOTEL.value,
        title="Hotel: Taj Fort Aguada Resort, Goa",
        origin="Goa",
        destination="Goa",
        scheduled_departure=leg2_arr,
        scheduled_arrival=(now + datetime.timedelta(days=4)).replace(hour=11, minute=0),
        estimated_departure=leg2_arr,
        estimated_arrival=(now + datetime.timedelta(days=4)).replace(hour=11, minute=0),
        status=ItemStatus.CONFIRMED.value,
        price=12500.0,
        notes="Luxury Sea Facing Suite. Guaranteed Early Check-in."
    )
    db.add(item3)
    db.commit()
    db.refresh(item3)

    db.add(Booking(
        itinerary_item_id=item3.id,
        booking_reference="HTL-TAJ-98210",
        provider="Booking.com",
        seat_or_room="Room 304 - Ocean Suite"
    ))

    item4 = ItineraryItem(
        trip_id=trip.id,
        sequence_order=4,
        item_type=ItemType.ACTIVITY.value,
        title="Activity: Grand Island Scuba Diving & Boat Safari",
        origin="Goa",
        destination="Goa",
        scheduled_departure=(now + datetime.timedelta(days=1)).replace(hour=7, minute=30),
        scheduled_arrival=(now + datetime.timedelta(days=1)).replace(hour=13, minute=0),
        estimated_departure=(now + datetime.timedelta(days=1)).replace(hour=7, minute=30),
        estimated_arrival=(now + datetime.timedelta(days=1)).replace(hour=13, minute=0),
        status=ItemStatus.CONFIRMED.value,
        price=3500.0,
        notes="Pick up at 07:30 AM from Hotel."
    )
    db.add(item4)
    db.commit()
    db.refresh(item4)

    db.add(Booking(
        itinerary_item_id=item4.id,
        booking_reference="ACT-GOA-77312",
        provider="Thrillophilia",
        seat_or_room="Pass #2"
    ))

    db.commit()
    return trip

# API Routes
@app.get("/api/seed")
def seed_endpoint(db: Session = Depends(get_db)):
    trip = seed_demo_data(db)
    return {"message": "Demo data seeded successfully", "trip_id": trip.id}

@app.post("/api/auth/me")
def firebase_auth_sync(req: FirebaseAuthSyncRequest, db: Session = Depends(get_db)):
    """Sync Firebase Authenticated user details & email verification status into backend"""
    claims = FirebaseTokenVerifier.verify_id_token(req.token)
    email = claims["email"]
    name = claims["name"]

    user = db.query(User).filter((User.email == email) | (User.name == name)).first()
    if not user:
        user = User(
            name=name,
            email=email,
            preference=PreferenceTier.BALANCED.value,
            max_transfers=2
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "status": "authenticated",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "email_verified": claims.get("email_verified", True),
        "preference": user.preference,
        "firebase_claims": claims
    }

@app.get("/api/disruptions/dashboard-analytics")
def get_dashboard_analytics(db: Session = Depends(get_db)):
    engine = DisruptionRecoveryEngine(db)
    return engine.get_dashboard_analytics()

@app.get("/api/stations/autocomplete")
def station_autocomplete(query: str = Query(..., min_length=1)):
    results = LocationResolver.autocomplete(query)
    return {"query": query, "results_count": len(results), "suggestions": results}

@app.post("/api/search")
def multi_modal_search(req: SearchRequest):
    t_date = datetime.date.today()
    if req.travel_date:
        try:
            t_date = datetime.datetime.strptime(req.travel_date, "%Y-%m-%d").date()
        except Exception:
            pass

    flights, trains, buses = [], [], []

    if req.transport_type in ["all", "flight"]:
        flights = flight_adapter.search_routes(req.origin, req.destination, t_date)

    if req.transport_type in ["all", "train"]:
        trains = train_adapter.search_routes(req.origin, req.destination, t_date)

    if req.transport_type in ["all", "bus"]:
        buses = bus_adapter.search_routes(req.origin, req.destination, t_date)

    all_results = flights + trains + buses

    if req.sort_by == "cheapest":
        all_results.sort(key=lambda x: x.get("price", 999999))
    elif req.sort_by == "fastest":
        all_results.sort(key=lambda x: x.get("duration_minutes", 999999))
    elif req.sort_by == "earliest":
        all_results.sort(key=lambda x: x.get("departure_time", "23:59"))
    elif req.sort_by == "direct":
        all_results = [r for r in all_results if r.get("stops", 0) == 0]

    return {
        "origin": req.origin,
        "destination": req.destination,
        "travel_date": t_date.isoformat(),
        "passengers": req.passengers,
        "demo_mode": DEMO_MODE,
        "counts": {
            "all": len(all_results),
            "flights": len(flights),
            "trains": len(trains),
            "buses": len(buses)
        },
        "results": all_results,
        "flights": flights,
        "trains": trains,
        "buses": buses
    }

@app.get("/api/trips")
def list_trips(db: Session = Depends(get_db)):
    trips = db.query(Trip).all()
    if not trips:
        seed_demo_data(db)
        trips = db.query(Trip).all()
    return trips

@app.get("/api/trips/{trip_id}")
def get_trip_detail(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    items_data = []
    for item in trip.itinerary_items:
        t_detail = None
        if item.transport_detail:
            t_detail = {
                "transport_type": item.transport_detail.transport_type,
                "carrier_name": item.transport_detail.carrier_name,
                "vehicle_number": item.transport_detail.vehicle_number,
                "platform_or_gate": item.transport_detail.platform_or_gate,
                "origin_station": item.transport_detail.origin_station,
                "dest_station": item.transport_detail.dest_station,
            }
        booking_data = []
        for b in item.bookings:
            booking_data.append({
                "booking_reference": b.booking_reference,
                "provider": b.provider,
                "seat_or_room": b.seat_or_room,
                "status": b.status
            })
        items_data.append({
            "id": item.id,
            "sequence_order": item.sequence_order,
            "item_type": item.item_type,
            "title": item.title,
            "origin": item.origin,
            "destination": item.destination,
            "scheduled_departure": item.scheduled_departure.isoformat() if item.scheduled_departure else None,
            "scheduled_arrival": item.scheduled_arrival.isoformat() if item.scheduled_arrival else None,
            "estimated_departure": item.estimated_departure.isoformat() if item.estimated_departure else None,
            "estimated_arrival": item.estimated_arrival.isoformat() if item.estimated_arrival else None,
            "status": item.status,
            "price": item.price,
            "notes": item.notes,
            "transport_detail": t_detail,
            "bookings": booking_data
        })

    disruptions_data = []
    for d in trip.disruptions:
        disruptions_data.append({
            "id": d.id,
            "itinerary_item_id": d.itinerary_item_id,
            "transport_type": d.transport_type,
            "disruption_type": d.disruption_type,
            "delay_minutes": d.delay_minutes,
            "description": d.description,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat()
        })

    plans_data = []
    for p in trip.recovery_plans:
        plans_data.append({
            "id": p.id,
            "title": p.title,
            "badge": p.badge,
            "description": p.description,
            "total_cost_diff": p.total_cost_diff,
            "total_delay_minutes": p.total_delay_minutes,
            "transfers_count": p.transfers_count,
            "feasibility_score": p.feasibility_score,
            "itinerary_preservation_score": p.itinerary_preservation_score,
            "overall_score": p.overall_score,
            "is_recommended": p.is_recommended,
            "recovery_actions": p.recovery_actions_json,
            "ai_explanation": p.ai_explanation
        })

    user_data = None
    if trip.user:
        user_data = {
            "name": trip.user.name,
            "preference": trip.user.preference
        }

    return {
        "id": trip.id,
        "title": trip.title,
        "origin": trip.origin,
        "destination": trip.destination,
        "status": trip.status,
        "user": user_data,
        "itinerary_items": items_data,
        "disruptions": disruptions_data,
        "recovery_plans": plans_data
    }

@app.post("/api/disruptions/simulate")
def simulate_disruption(
    req: DisruptionSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_firebase)
):
    trip = db.query(Trip).filter(Trip.id == req.trip_id).first()
    item = db.query(ItineraryItem).filter(ItineraryItem.id == req.itinerary_item_id).first()

    if not trip or not item:
        raise HTTPException(status_code=404, detail="Trip or Itinerary item not found")

    desc = req.description or f"{item.title} affected by {req.disruption_type.upper()} ({req.delay_minutes} mins)"
    disruption = Disruption(
        trip_id=req.trip_id,
        itinerary_item_id=req.itinerary_item_id,
        transport_type=item.transport_detail.transport_type if item.transport_detail else TransportType.TRAIN.value,
        disruption_type=req.disruption_type,
        delay_minutes=req.delay_minutes,
        description=desc,
        is_active=True
    )
    db.add(disruption)
    trip.status = "disrupted"
    db.commit()
    db.refresh(disruption)

    engine = DisruptionRecoveryEngine(db)
    impact = engine.analyze_disruption_impact(req.trip_id, req.itinerary_item_id, req.delay_minutes, req.disruption_type)
    plans = engine.generate_recovery_plans(req.trip_id, disruption.id)
    plans = ai_engine.generate_plan_explanations(trip, disruption, plans, impact)
    db.commit()

    return {
        "message": "Disruption simulated and recovery options generated",
        "disruption_id": disruption.id,
        "impact_analysis": impact,
        "recovery_plans_count": len(plans),
        "authenticated_user": current_user.name
    }

@app.post("/api/recovery/apply")
def apply_recovery_plan(
    req: ApplyPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_firebase)
):
    engine = DisruptionRecoveryEngine(db)
    try:
        updated_trip = engine.apply_recovery_plan(req.trip_id, req.plan_id)
        return {
            "message": "Recovery plan successfully applied and itinerary updated",
            "status": updated_trip.status,
            "authenticated_user": current_user.name
        }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

@app.post("/api/user/preference")
def update_user_preference(
    req: UserPreferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_firebase)
):
    trip = db.query(Trip).filter(Trip.id == req.trip_id).first()
    if not trip or not trip.user:
        raise HTTPException(status_code=404, detail="Trip or User not found")

    if req.preference not in ["budget", "balanced", "speed"]:
        raise HTTPException(status_code=400, detail="Invalid preference tier")

    trip.user.preference = req.preference
    db.commit()

    if trip.disruptions:
        disruption = trip.disruptions[-1]
        engine = DisruptionRecoveryEngine(db)
        plans = engine.generate_recovery_plans(trip.id, disruption.id)
        ai_engine.generate_plan_explanations(trip, disruption, plans, {})
        db.commit()

    return {"message": f"Preference updated to {req.preference.upper()}", "preference": req.preference}

@app.get("/api/segments/{item_id}/status")
def get_segment_status(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Segment not found")

    live_status = {"status": item.status, "delay_minutes": 0, "message": "On Schedule"}
    if item.transport_detail:
        ttype = item.transport_detail.transport_type
        vnum = item.transport_detail.vehicle_number
        today = datetime.date.today()
        if ttype == TransportType.TRAIN.value:
            live_status = train_adapter.get_live_status(vnum, today)
        elif ttype == TransportType.BUS.value:
            live_status = bus_adapter.get_live_status(vnum, today)
        elif ttype == TransportType.FLIGHT.value:
            live_status = flight_adapter.get_live_status(vnum, today)

    return {
        "item_id": item.id,
        "title": item.title,
        "item_type": item.item_type,
        "current_status": item.status,
        "live_status_check": live_status,
        "scheduled_departure": item.scheduled_departure.isoformat() if item.scheduled_departure else None,
        "scheduled_arrival": item.scheduled_arrival.isoformat() if item.scheduled_arrival else None,
        "estimated_arrival": item.estimated_arrival.isoformat() if item.estimated_arrival else None,
    }

@app.post("/api/ai/chat")
def ai_chat(req: ChatRequest, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == req.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    disruption = trip.disruptions[0] if trip.disruptions else None
    plans = trip.recovery_plans or []

    answer = ai_engine.answer_user_question(trip, disruption, plans, req.user_message)
    return {"reply": answer}

# Serve static frontend files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
