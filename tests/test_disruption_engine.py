import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Trip, ItineraryItem, ItemStatus, ItemType, TransportType, Disruption, RecoveryPlan
from app.main import seed_demo_data
from app.services.disruption_engine import DisruptionRecoveryEngine

@pytest.fixture
def db_session():
    # In-memory SQLite for rapid unit tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_seed_demo_data(db_session):
    trip = seed_demo_data(db_session)
    assert trip.id is not None
    assert trip.origin == "Mumbai"
    assert trip.destination == "Goa"
    assert len(trip.itinerary_items) == 4

def test_analyze_disruption_missed_connection(db_session):
    trip = seed_demo_data(db_session)
    engine = DisruptionRecoveryEngine(db_session)

    leg1 = trip.itinerary_items[0]
    
    # 4-hour (240 minutes) train delay on Mumbai -> Pune leg
    impact = engine.analyze_disruption_impact(trip.id, leg1.id, delay_minutes=240)

    assert impact["delay_minutes"] == 240
    assert len(impact["missed_connections"]) >= 1
    
    missed_conn = impact["missed_connections"][0]
    assert missed_conn["item_id"] == trip.itinerary_items[1].id
    assert "Train → Bus" in missed_conn["connection_type"]
    assert trip.itinerary_items[1].status == ItemStatus.MISSED_CONNECTION.value

def test_generate_and_apply_recovery_plan(db_session):
    trip = seed_demo_data(db_session)
    engine = DisruptionRecoveryEngine(db_session)
    leg1 = trip.itinerary_items[0]

    # 1. Simulate 4h delay
    engine.analyze_disruption_impact(trip.id, leg1.id, delay_minutes=240)

    # Create disruption record
    disruption = Disruption(
        trip_id=trip.id,
        itinerary_item_id=leg1.id,
        transport_type=TransportType.TRAIN.value,
        disruption_type="delay",
        delay_minutes=240,
        description="4-hour train delay"
    )
    db_session.add(disruption)
    db_session.commit()

    # 2. Generate Recovery Plans
    plans = engine.generate_recovery_plans(trip.id, disruption.id)
    assert len(plans) >= 2

    # Check top plan
    plan_a = plans[0]
    assert plan_a.overall_score > 0
    assert len(plan_a.recovery_actions_json) >= 1

    # 3. Apply Recovery Plan
    updated_trip = engine.apply_recovery_plan(trip.id, plan_a.id)
    assert updated_trip.status == "recovered"
    
    # Verify Pune -> Goa bus is updated to confirmed with new schedule
    leg2 = updated_trip.itinerary_items[1]
    assert leg2.status == ItemStatus.CONFIRMED.value
