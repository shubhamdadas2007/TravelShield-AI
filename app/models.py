import enum
import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class PreferenceTier(str, enum.Enum):
    BUDGET = "budget"
    BALANCED = "balanced"
    SPEED = "speed"

class TransportType(str, enum.Enum):
    TRAIN = "train"
    BUS = "bus"
    FLIGHT = "flight"

class ItemType(str, enum.Enum):
    TRANSPORT = "transport"
    HOTEL = "hotel"
    ACTIVITY = "activity"

class ItemStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    DELAYED = "delayed"
    MISSED_CONNECTION = "missed_connection"
    CANCELLED = "cancelled"
    AFFECTED = "affected"
    RESOLVED = "resolved"

class DisruptionType(str, enum.Enum):
    DELAY = "delay"
    CANCELLATION = "cancellation"
    EXPECTED_ARRIVAL_CHANGE = "expected_arrival_change"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    preference = Column(String(20), default=PreferenceTier.BALANCED.value)
    max_transfers = Column(Integer, default=2)
    budget_limit = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    origin = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="active") # active, disrupted, recovered
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="trips")
    itinerary_items = relationship("ItineraryItem", back_populates="trip", order_by="ItineraryItem.sequence_order", cascade="all, delete-orphan")
    disruptions = relationship("Disruption", back_populates="trip", cascade="all, delete-orphan")
    recovery_plans = relationship("RecoveryPlan", back_populates="trip", cascade="all, delete-orphan")

class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    item_type = Column(String(20), nullable=False) # transport, hotel, activity
    title = Column(String(200), nullable=False)
    origin = Column(String(100), nullable=True)
    destination = Column(String(100), nullable=True)
    scheduled_departure = Column(DateTime, nullable=True)
    scheduled_arrival = Column(DateTime, nullable=True)
    estimated_departure = Column(DateTime, nullable=True)
    estimated_arrival = Column(DateTime, nullable=True)
    status = Column(String(30), default=ItemStatus.SCHEDULED.value)
    price = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    trip = relationship("Trip", back_populates="itinerary_items")
    bookings = relationship("Booking", back_populates="itinerary_item", cascade="all, delete-orphan")
    transport_detail = relationship("TransportDetail", back_populates="itinerary_item", uselist=False, cascade="all, delete-orphan")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_item_id = Column(Integer, ForeignKey("itinerary_items.id"), nullable=False)
    booking_reference = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=False)
    seat_or_room = Column(String(50), nullable=True)
    status = Column(String(30), default="confirmed")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    itinerary_item = relationship("ItineraryItem", back_populates="bookings")

class TransportDetail(Base):
    __tablename__ = "transport_details"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_item_id = Column(Integer, ForeignKey("itinerary_items.id"), nullable=False)
    transport_type = Column(String(20), nullable=False) # train, bus, flight
    carrier_name = Column(String(100), nullable=False)
    vehicle_number = Column(String(50), nullable=False) # Train # / Bus # / Flight #
    platform_or_gate = Column(String(50), nullable=True)
    origin_station = Column(String(100), nullable=False)
    dest_station = Column(String(100), nullable=False)

    itinerary_item = relationship("ItineraryItem", back_populates="transport_detail")

class Disruption(Base):
    __tablename__ = "disruptions"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    itinerary_item_id = Column(Integer, ForeignKey("itinerary_items.id"), nullable=False)
    transport_type = Column(String(20), nullable=False)
    disruption_type = Column(String(30), nullable=False) # delay, cancellation
    delay_minutes = Column(Integer, default=0)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    trip = relationship("Trip", back_populates="disruptions")
    itinerary_item = relationship("ItineraryItem")

class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    disruption_id = Column(Integer, ForeignKey("disruptions.id"), nullable=False)
    title = Column(String(150), nullable=False)
    badge = Column(String(50), nullable=True) # e.g. "Recommended", "Budget Choice", "Fastest"
    description = Column(Text, nullable=False)
    total_cost_diff = Column(Float, default=0.0) # + or - ₹ amount
    total_delay_minutes = Column(Integer, default=0) # net delay to final destination
    transfers_count = Column(Integer, default=0)
    feasibility_score = Column(Float, default=100.0) # 0-100
    itinerary_preservation_score = Column(Float, default=100.0) # 0-100
    overall_score = Column(Float, default=90.0) # 0-100
    is_recommended = Column(Boolean, default=False)
    recovery_actions_json = Column(JSON, nullable=False) # array of actions to apply
    ai_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    trip = relationship("Trip", back_populates="recovery_plans")
    disruption = relationship("Disruption")
