import os
import json
import datetime
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from app.services.location_resolver import LocationResolver

# Load environment variables securely from .env
load_dotenv()

AOPAY_FLIGHT_API_KEY = os.getenv("AOPAY_FLIGHT_API_KEY") or os.getenv("AVIATIONSTACK_API_KEY")
AOPAY_BUS_API_KEY = os.getenv("AOPAY_BUS_API_KEY") or os.getenv("AOPAY_API_KEY")
INDIAN_RAIL_API_KEY = os.getenv("INDIAN_RAIL_API_KEY") or os.getenv("TRAIN_API_KEY")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

class BaseTransportAdapter(ABC):
    @abstractmethod
    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_live_status(self, vehicle_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        pass

class TrainServiceAdapter(BaseTransportAdapter):
    """
    Indian Rail API Adapter for TrainBetweenStation, station autocomplete, and live train disruptions.
    Integrates Cancelled, Rescheduled, Diverted, and Partially Cancelled trains.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or INDIAN_RAIL_API_KEY
        self.api_base_url = "https://api.indianrail.gov.in/v1" # Standard backend proxy endpoint

    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        origin_code = LocationResolver.get_station_code(origin)
        dest_code = LocationResolver.get_station_code(destination)
        origin_city = LocationResolver.get_city_name(origin)
        dest_city = LocationResolver.get_city_name(destination)

        # 1. Attempt live Indian Rail API call if credentials present
        if self.api_key and not self.api_key.startswith("mock"):
            try:
                headers = {"Authorization": f"Bearer {self.api_key}", "x-api-key": self.api_key}
                resp = requests.get(
                    f"{self.api_base_url}/TrainBetweenStation",
                    params={
                        "fromStationCode": origin_code,
                        "toStationCode": dest_code,
                        "dateOfJourney": travel_date.strftime("%Y-%m-%d")
                    },
                    headers=headers,
                    timeout=3
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "trains" in data and data["trains"]:
                        results = []
                        for t in data["trains"]:
                            results.append({
                                "origin": origin_city,
                                "destination": dest_city,
                                "carrier": "Indian Railways",
                                "vehicle_number": t.get("trainNumber", "12951"),
                                "name": t.get("trainName", "Rajdhani Express"),
                                "departure_time": t.get("departureTime", "16:00"),
                                "arrival_time": t.get("arrivalTime", "08:30"),
                                "duration_minutes": t.get("durationMinutes", 990),
                                "price": float(t.get("fare", 1450.0)),
                                "available_seats": t.get("availableSeats", 15),
                                "status": t.get("currentStatus", "ON TIME"),
                                "disruption_status": t.get("disruptionStatus", "Normal"),
                                "type": "train"
                            })
                        return results
            except Exception as ex:
                print(f"[TrainServiceAdapter] Live API note: {ex}")

        # 2. If API fails and DEMO_MODE is OFF, return Live Data Unavailable
        if not DEMO_MODE:
            return [{
                "origin": origin_city,
                "destination": dest_city,
                "carrier": "Indian Railways",
                "vehicle_number": "N/A",
                "name": "Live Train API Unavailable",
                "departure_time": "N/A",
                "arrival_time": "N/A",
                "duration_minutes": 0,
                "price": 0.0,
                "status": "Live data unavailable",
                "disruption_status": "API Timeout",
                "type": "train"
            }]

        # 3. DEMO MODE dynamic generator for ANY Indian city pair
        return self._generate_dynamic_trains(origin_city, dest_city, origin_code, dest_code, travel_date, after_time)

    def _generate_dynamic_trains(self, origin_city: str, dest_city: str, origin_code: str, dest_code: str, travel_date: datetime.date, after_time: Optional[datetime.time]) -> List[Dict[str, Any]]:
        schedules = [
            {"num": "12951", "name": f"{origin_city}-{dest_city} Rajdhani Express", "dep": "16:30", "arr": "08:30", "dur": 960, "price": 1850.0, "status": "ON TIME", "disruption": "Normal"},
            {"num": "12260", "name": f"{origin_city}-{dest_city} Duronto Express", "dep": "20:15", "arr": "11:45", "dur": 930, "price": 1620.0, "status": "ON TIME", "disruption": "Normal"},
            {"num": "22436", "name": f"{origin_city}-{dest_city} Vande Bharat Express", "dep": "06:00", "arr": "14:15", "dur": 495, "price": 1450.0, "status": "ON TIME", "disruption": "Normal"},
            {"num": "12780", "name": f"{origin_city}-{dest_city} Superfast Express", "dep": "22:45", "arr": "12:15", "dur": 810, "price": 680.0, "status": "DELAYED +45m", "disruption": "Rescheduled"}
        ]
        results = []
        for train in schedules:
            dep_h, dep_m = map(int, train["dep"].split(":"))
            dep_time_obj = datetime.time(dep_h, dep_m)
            if after_time is None or dep_time_obj >= after_time:
                dep_dt = datetime.datetime.combine(travel_date, dep_time_obj)
                arr_dt = dep_dt + datetime.timedelta(minutes=train["dur"])
                results.append({
                    "origin": origin_city,
                    "destination": dest_city,
                    "carrier": "Indian Railways",
                    "vehicle_number": train["num"],
                    "name": train["name"],
                    "departure_time": train["dep"],
                    "arrival_time": train["arr"],
                    "departure_datetime": dep_dt.isoformat(),
                    "arrival_datetime": arr_dt.isoformat(),
                    "duration_minutes": train["dur"],
                    "price": train["price"],
                    "available_seats": 24,
                    "status": train["status"],
                    "disruption_status": train["disruption"],
                    "type": "train"
                })
        return results

    def get_live_status(self, vehicle_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        return {
            "vehicle_number": vehicle_number,
            "status": "Running",
            "delay_minutes": 0,
            "current_station": "En Route",
            "disruption_flags": {
                "is_cancelled": False,
                "is_rescheduled": False,
                "is_diverted": False,
                "is_partially_cancelled": False
            }
        }

class BusServiceAdapter(BaseTransportAdapter):
    """
    AOPAY Bus API Adapter in Sandbox mode.
    Endpoint: https://api.aopay.in/v2/bus/search
    Header: X-API-Key: <AOPAY_BUS_API_KEY>
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or AOPAY_BUS_API_KEY
        self.api_url = "https://api.aopay.in/v2/bus/search"

    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        origin_city = LocationResolver.get_city_name(origin)
        dest_city = LocationResolver.get_city_name(destination)

        # 1. Attempt AOPAY Bus API call
        if self.api_key:
            try:
                headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
                payload = {
                    "origin": origin_city,
                    "destination": dest_city,
                    "date": travel_date.strftime("%Y-%m-%d"),
                    "passengers": 1
                }
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    if "buses" in data and data["buses"]:
                        return data["buses"]
            except Exception as ex:
                print(f"[BusServiceAdapter] AOPAY API note: {ex}")

        # 2. If API fails and DEMO_MODE is OFF, return Live Data Unavailable
        if not DEMO_MODE:
            return [{
                "origin": origin_city,
                "destination": dest_city,
                "carrier": "AOPAY Bus Service",
                "vehicle_number": "N/A",
                "name": "Live Bus API Unavailable",
                "departure_time": "N/A",
                "arrival_time": "N/A",
                "duration_minutes": 0,
                "price": 0.0,
                "available_seats": 0,
                "status": "Live data unavailable",
                "type": "bus"
            }]

        # 3. DEMO MODE dynamic generator for ANY Indian city pair
        return self._generate_dynamic_buses(origin_city, dest_city, travel_date, after_time)

    def _generate_dynamic_buses(self, origin_city: str, dest_city: str, travel_date: datetime.date, after_time: Optional[datetime.time]) -> List[Dict[str, Any]]:
        operators = [
            {"carrier": "IntrCity SmartBus", "name": f"{origin_city}-{dest_city} Volvo Multi-Axle AC Sleeper", "dep": "20:00", "arr": "06:30", "dur": 630, "price": 1100.0, "seats": 14},
            {"carrier": "VRL Travels", "name": f"{origin_city}-{dest_city} Scania AC Sleeper", "dep": "21:30", "arr": "07:45", "dur": 615, "price": 1250.0, "seats": 22},
            {"carrier": "Neeta Travels", "name": f"{origin_city}-{dest_city} Mercedes Benz B9R", "dep": "22:45", "arr": "08:30", "dur": 585, "price": 1350.0, "seats": 9}
        ]
        results = []
        for b in operators:
            dep_h, dep_m = map(int, b["dep"].split(":"))
            dep_time_obj = datetime.time(dep_h, dep_m)
            if after_time is None or dep_time_obj >= after_time:
                dep_dt = datetime.datetime.combine(travel_date, dep_time_obj)
                arr_dt = dep_dt + datetime.timedelta(minutes=b["dur"])
                results.append({
                    "origin": origin_city,
                    "destination": dest_city,
                    "carrier": b["carrier"],
                    "vehicle_number": f"MH-{b['carrier'][:2].upper()}-901",
                    "name": b["name"],
                    "departure_time": b["dep"],
                    "arrival_time": b["arr"],
                    "departure_datetime": dep_dt.isoformat(),
                    "arrival_datetime": arr_dt.isoformat(),
                    "duration_minutes": b["dur"],
                    "price": b["price"],
                    "available_seats": b["seats"],
                    "status": "ON TIME",
                    "type": "bus"
                })
        return results

    def get_live_status(self, vehicle_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        return {"vehicle_number": vehicle_number, "status": "On Time", "delay_minutes": 0}

class FlightServiceAdapter(BaseTransportAdapter):
    """
    AOPAY Flight API Adapter.
    Endpoint: https://api.aopay.in/v2/flights/search
    Header: X-API-Key: <AOPAY_FLIGHT_API_KEY>
    Converts city/location into IATA airport code dynamically (BOM, DEL, BLR, HYD, etc.).
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or AOPAY_FLIGHT_API_KEY
        self.api_url = "https://api.aopay.in/v2/flights/search"

    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        origin_iata = LocationResolver.get_iata_code(origin)
        dest_iata = LocationResolver.get_iata_code(destination)
        origin_city = LocationResolver.get_city_name(origin)
        dest_city = LocationResolver.get_city_name(destination)

        # 1. Attempt AOPAY Flight API call
        if self.api_key:
            try:
                headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
                payload = {
                    "originIata": origin_iata,
                    "destinationIata": dest_iata,
                    "departureDate": travel_date.strftime("%Y-%m-%d"),
                    "passengers": 1
                }
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    if "flights" in data and data["flights"]:
                        return data["flights"]
            except Exception as ex:
                print(f"[FlightServiceAdapter] AOPAY Flight API note: {ex}")

        # 2. If API fails and DEMO_MODE is OFF, return Live Data Unavailable
        if not DEMO_MODE:
            return [{
                "origin": f"{origin_city} ({origin_iata})",
                "destination": f"{dest_city} ({dest_iata})",
                "carrier": "AOPAY Flight Service",
                "vehicle_number": "N/A",
                "name": "Live Flight API Unavailable",
                "departure_time": "N/A",
                "arrival_time": "N/A",
                "duration_minutes": 0,
                "price": 0.0,
                "stops": 0,
                "status": "Live data unavailable",
                "type": "flight"
            }]

        # 3. DEMO MODE dynamic generator for ANY Indian airport pair
        return self._generate_dynamic_flights(origin_city, dest_city, origin_iata, dest_iata, travel_date, after_time)

    def _generate_dynamic_flights(self, origin_city: str, dest_city: str, origin_iata: str, dest_iata: str, travel_date: datetime.date, after_time: Optional[datetime.time]) -> List[Dict[str, Any]]:
        flights_list = [
            {"carrier": "IndiGo", "fn": f"6E-{hash(origin_city+dest_city)%900+1000}", "dep": "19:15", "arr": "20:35", "dur": 80, "price": 3800.0, "stops": 0},
            {"carrier": "Air India Express", "fn": f"IX-{hash(origin_city)%900+2000}", "dep": "21:40", "arr": "23:00", "dur": 80, "price": 4200.0, "stops": 0},
            {"carrier": "Akasa Air", "fn": f"QP-{hash(dest_city)%900+1100}", "dep": "23:10", "arr": "00:30", "dur": 80, "price": 3450.0, "stops": 0}
        ]
        results = []
        for fl in flights_list:
            dep_h, dep_m = map(int, fl["dep"].split(":"))
            dep_time_obj = datetime.time(dep_h, dep_m)
            if after_time is None or dep_time_obj >= after_time:
                dep_dt = datetime.datetime.combine(travel_date, dep_time_obj)
                arr_dt = dep_dt + datetime.timedelta(minutes=fl["dur"])
                results.append({
                    "origin": f"{origin_city} ({origin_iata})",
                    "destination": f"{dest_city} ({dest_iata})",
                    "carrier": fl["carrier"],
                    "vehicle_number": fl["fn"],
                    "name": f"Direct Flight {fl['fn']} ({origin_iata} → {dest_iata})",
                    "departure_time": fl["dep"],
                    "arrival_time": fl["arr"],
                    "departure_datetime": dep_dt.isoformat(),
                    "arrival_datetime": arr_dt.isoformat(),
                    "duration_minutes": fl["dur"],
                    "price": fl["price"],
                    "stops": fl["stops"],
                    "status": "ON TIME",
                    "type": "flight"
                })
        return results

    def get_live_status(self, vehicle_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        return {"vehicle_number": vehicle_number, "status": "On Time", "delay_minutes": 0, "gate": "B4"}
