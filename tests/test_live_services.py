import os
import datetime
import pytest
from app.services.transport_adapters import (
    TrainServiceAdapter, FlightServiceAdapter, BusServiceAdapter
)
from app.services.location_resolver import LocationResolver
from app.services.disruption_engine import DisruptionRecoveryEngine

def test_location_autocomplete_modes():
    # Train mode should return railway stations
    train_hubs = LocationResolver.autocomplete("CSMT", mode="train")
    assert any(h["code"] == "CSMT" for h in train_hubs)

    # Flight mode should return airports
    airports = LocationResolver.autocomplete("BOM", mode="flight")
    assert any(h["code"] == "BOM" for h in airports)

    # Bus mode should return bus stations
    buses = LocationResolver.autocomplete("Swargate", mode="bus")
    assert any("Swargate" in h["name"] for h in buses)

    # All mode returns multi-modal hubs
    all_hubs = LocationResolver.autocomplete("Mumbai", mode="all")
    types = {h["type"] for h in all_hubs}
    assert "airport" in types or "railway_station" in types

def test_disruption_severity_levels():
    # Minor delay < 30m -> LOW
    assert DisruptionRecoveryEngine.calculate_disruption_severity(15, has_missed_connection=False, is_cancelled=False) == "LOW"

    # Delay 30-90m -> MEDIUM
    assert DisruptionRecoveryEngine.calculate_disruption_severity(45, has_missed_connection=False, is_cancelled=False) == "MEDIUM"

    # Delay >= 90m or missed connection -> HIGH
    assert DisruptionRecoveryEngine.calculate_disruption_severity(105, has_missed_connection=False, is_cancelled=False) == "HIGH"
    assert DisruptionRecoveryEngine.calculate_disruption_severity(30, has_missed_connection=True, is_cancelled=False) == "HIGH"

    # Cancellation or 3h+ delay with missed connection -> CRITICAL
    assert DisruptionRecoveryEngine.calculate_disruption_severity(0, has_missed_connection=False, is_cancelled=True) == "CRITICAL"
    assert DisruptionRecoveryEngine.calculate_disruption_severity(240, has_missed_connection=True, is_cancelled=False) == "CRITICAL"

def test_weighted_recovery_score_formula():
    class DummyEngine(DisruptionRecoveryEngine):
        def __init__(self):
            pass

    engine = DummyEngine()
    # Perfect score: 0 cost diff, 0 delay, 0 transfers, high feasibility
    scores = engine._calculate_scores(
        cost_diff=0.0,
        delay_minutes=0,
        transfers=0,
        feasibility=100.0,
        preservation=100.0,
        pref_tier="balanced",
        travel_duration_minutes=60
    )
    assert 90.0 <= scores["overall"] <= 100.0
    assert "arrival_score" in scores
    assert "reliability_score" in scores
    assert "duration_score" in scores
    assert "cost_score" in scores
    assert "transfer_score" in scores

    # Custom weights support
    custom_weights = {"arrival": 0.50, "reliability": 0.20, "duration": 0.10, "cost": 0.10, "transfers": 0.10}
    custom_scores = engine._calculate_scores(
        cost_diff=500.0,
        delay_minutes=120,
        transfers=1,
        feasibility=90.0,
        custom_weights=custom_weights
    )
    assert 0.0 <= custom_scores["overall"] <= 100.0

def test_train_adapter_fallback():
    adapter = TrainServiceAdapter(api_key="mock_invalid_key")
    status = adapter.get_live_status("12127", datetime.date.today())
    assert "status" in status
    assert "vehicle_number" in status
    assert status["vehicle_number"] == "12127"

def test_flight_adapter_fallback():
    adapter = FlightServiceAdapter(api_key="mock_invalid_key")
    status = adapter.get_live_status("AI-882", datetime.date.today())
    assert "status" in status
    assert "vehicle_number" in status
    assert status["vehicle_number"] == "AI-882"

def test_bus_adapter_fallback():
    adapter = BusServiceAdapter(api_key="mock_invalid_key")
    buses = adapter.search_routes("Pune", "Goa", datetime.date.today())
    assert len(buses) > 0
    assert "price" in buses[0]

def test_no_api_keys_in_frontend():
    # Strict security test: ensure real keys never leaked into user-facing frontend files
    forbidden_keys = [
        "2a3ac8e567msh59bb938d3fdc859p1a44f6jsn4152686cf1da", # RapidAPI key
        "66ffbf6a7c0fc63a1a593ed8cf28df31"                     # Aviationstack key
    ]
    frontend_files = ["index.html", "static/index.html", "static/js/app.js"]
    for fname in frontend_files:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for key in forbidden_keys:
                    assert key not in content, f"CRITICAL SECURITY FAILURE: API Key found in {fname}!"
