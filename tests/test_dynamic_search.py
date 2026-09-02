import pytest
import datetime
from app.services.location_resolver import LocationResolver
from app.services.transport_adapters import TrainServiceAdapter, BusServiceAdapter, FlightServiceAdapter

def test_location_resolver_autocomplete():
    # Test Autocomplete for Mumbai, Delhi, Bengaluru, Hyderabad
    res_bom = LocationResolver.autocomplete("Mumbai")
    assert len(res_bom) >= 1
    codes = [item["code"] for item in res_bom]
    assert "BOM" in codes or "CSMT" in codes or "MMCT" in codes

    res_blr = LocationResolver.autocomplete("BLR")
    assert len(res_blr) >= 1
    assert res_blr[0]["code"] == "BLR"

def test_location_resolver_codes():
    # Flight IATA Code resolution
    assert LocationResolver.get_iata_code("Mumbai") == "BOM"
    assert LocationResolver.get_iata_code("Delhi") == "DEL"
    assert LocationResolver.get_iata_code("Bengaluru") == "BLR"
    assert LocationResolver.get_iata_code("Hyderabad") == "HYD"

    # Railway Station Code resolution
    assert LocationResolver.get_station_code("Mumbai") == "CSMT"
    assert LocationResolver.get_station_code("Delhi") == "NDLS"
    assert LocationResolver.get_station_code("Bengaluru") == "SBC"
    assert LocationResolver.get_station_code("Hyderabad") == "SC"

def test_dynamic_multi_route_search():
    today = datetime.date.today()
    flight_adapter = FlightServiceAdapter()
    train_adapter = TrainServiceAdapter()
    bus_adapter = BusServiceAdapter()

    # Route 1: Bengaluru -> Hyderabad
    flights_blr = flight_adapter.search_routes("Bengaluru", "Hyderabad", today)
    trains_blr = train_adapter.search_routes("Bengaluru", "Hyderabad", today)
    buses_blr = bus_adapter.search_routes("Bengaluru", "Hyderabad", today)

    assert len(flights_blr) >= 1
    assert flights_blr[0]["origin"] == "Bengaluru (BLR)"
    assert flights_blr[0]["destination"] == "Hyderabad (HYD)"

    assert len(trains_blr) >= 1
    assert trains_blr[0]["origin"] == "Bengaluru"
    assert trains_blr[0]["destination"] == "Hyderabad"

    assert len(buses_blr) >= 1
    assert buses_blr[0]["origin"] == "Bengaluru"
    assert buses_blr[0]["destination"] == "Hyderabad"

    # Route 2: Mumbai -> Delhi
    flights_del = flight_adapter.search_routes("Mumbai", "Delhi", today)
    assert len(flights_del) >= 1
    assert "DEL" in flights_del[0]["destination"]
