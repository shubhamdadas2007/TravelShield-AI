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

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST_TRAIN = os.getenv("RAPIDAPI_HOST_TRAIN", "indian-railway-irctc.p.rapidapi.com")
RAPIDAPI_HOST_FLIGHT = os.getenv("RAPIDAPI_HOST_FLIGHT", "aerodatabox.p.rapidapi.com")
RAPIDAPI_HOST_WEATHER = os.getenv("RAPIDAPI_HOST_WEATHER", "weather-api167.p.rapidapi.com")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
AOPAY_BUS_API_KEY = os.getenv("AOPAY_BUS_API_KEY")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Cache dictionary to prevent hammering external APIs unnecessarily
API_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes cache

def _get_from_cache(cache_key: str) -> Optional[Any]:
    if cache_key in API_CACHE:
        entry = API_CACHE[cache_key]
        if (datetime.datetime.now() - entry["timestamp"]).total_seconds() < CACHE_TTL_SECONDS:
            return entry["data"]
    return None

def _save_to_cache(cache_key: str, data: Any):
    API_CACHE[cache_key] = {
        "timestamp": datetime.datetime.now(),
        "data": data
    }


class BaseTransportAdapter(ABC):
    @abstractmethod
    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_live_status(self, vehicle_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        pass


class TrainServiceAdapter(BaseTransportAdapter):
    """
    Production-grade Indian Railway IRCTC API Adapter via RapidAPI.
    Supports:
    - Train live running status
    - Train search between stations
    - Train schedule and delay metrics
    - Graceful degradation when offline or unconfigured
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or RAPIDAPI_KEY
        self.api_host = RAPIDAPI_HOST_TRAIN
        self.base_url = f"https://{self.api_host}"

    def get_live_status(self, train_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        """
        Queries Indian Railway IRCTC live running status for a given train number and departure date.
        Endpoint: /api/trains/v1/train/status
        """
        clean_num = train_number.strip()
        date_str = travel_date.strftime("%Y%m%d")
        cache_key = f"train_status_{clean_num}_{date_str}"

        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # 1. Attempt live RapidAPI request if key is present
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                url = f"{self.base_url}/api/trains/v1/train/status"
                params = {
                    "departure_date": date_str,
                    "isH5": "true",
                    "client": "web",
                    "deviceIdentifier": "Mozilla Firefox-138.0.0.0",
                    "train_number": clean_num
                }
                headers = {
                    "Content-Type": "application/json",
                    "x-rapid-api": "rapid-api-database",
                    "x-rapidapi-host": self.api_host,
                    "x-rapidapi-key": self.api_key
                }
                resp = requests.get(url, params=params, headers=headers, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    # Parse standard IRCTC payload
                    status_info = self._parse_irctc_live_response(data, clean_num, travel_date)
                    _save_to_cache(cache_key, status_info)
                    return status_info
                elif resp.status_code in [401, 403]:
                    print(f"[TrainServiceAdapter] RapidAPI auth error {resp.status_code}")
                elif resp.status_code == 429:
                    print(f"[TrainServiceAdapter] RapidAPI rate limit reached (429)")
            except Exception as ex:
                print(f"[TrainServiceAdapter] Live API call exception: {ex}")

        # 2. Check DEMO_MODE fallback
        if DEMO_MODE:
            demo_status = self._generate_demo_train_status(clean_num, travel_date)
            return demo_status

        # 3. Graceful fallback when API is unreachable and DEMO_MODE is false
        return {
            "vehicle_number": clean_num,
            "carrier": "Indian Railways",
            "name": f"Train {clean_num}",
            "status": "Live data currently unavailable",
            "is_live": False,
            "delay_minutes": 0,
            "current_station": "Telemetry Offline",
            "message": "Live railway API service is currently unavailable or unconfigured.",
            "data_source": "IRCTC RapidAPI (Offline)"
        }

    def _parse_irctc_live_response(self, data: Dict[str, Any], train_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        """Maps raw IRCTC RapidAPI JSON into standardized telemetry schema."""
        train_name = data.get("train_name") or data.get("name") or f"Train {train_number}"
        delay = data.get("delay_in_minutes") or data.get("delay") or 0
        current_stn = data.get("current_station_name") or data.get("station_name") or "En Route"
        is_terminated = data.get("is_terminated", False)
        is_cancelled = data.get("is_cancelled", False)

        status_str = "CANCELLED" if is_cancelled else ("ON TIME" if delay == 0 else f"DELAYED +{delay}m")
        return {
            "vehicle_number": train_number,
            "carrier": "Indian Railways",
            "name": train_name,
            "status": status_str,
            "is_live": True,
            "delay_minutes": int(delay),
            "current_station": current_stn,
            "is_terminated": is_terminated,
            "is_cancelled": is_cancelled,
            "data_source": "RapidAPI Indian Railways (Live)",
            "last_updated": datetime.datetime.now().strftime("%H:%M")
        }

    def _generate_demo_train_status(self, train_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        """Provides deterministic demo status for presentation purposes."""
        # 12127 Pragati Express has 240 mins delay in demo scenario
        if train_number in ["12127", "12123"]:
            return {
                "vehicle_number": train_number,
                "carrier": "Indian Railways",
                "name": "Pragati Superfast Express",
                "status": "DELAYED +240m",
                "is_live": False,
                "is_demo": True,
                "delay_minutes": 240,
                "current_station": "Karjat Junction (KJT)",
                "platform": "Platform 2",
                "disruption_cause": "Monsoon waterlogging at Bhor Ghat section",
                "data_source": "Deterministic Demo Scenario",
                "last_updated": datetime.datetime.now().strftime("%H:%M")
            }
        return {
            "vehicle_number": train_number,
            "carrier": "Indian Railways",
            "name": f"Express Train {train_number}",
            "status": "ON TIME",
            "is_live": False,
            "is_demo": True,
            "delay_minutes": 0,
            "current_station": "Kalyan Junction",
            "data_source": "Deterministic Demo Scenario",
            "last_updated": datetime.datetime.now().strftime("%H:%M")
        }

    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        """Searches available trains between origin and destination."""
        origin_code = LocationResolver.get_station_code(origin)
        dest_code = LocationResolver.get_station_code(destination)
        origin_city = LocationResolver.get_city_name(origin)
        dest_city = LocationResolver.get_city_name(destination)

        cache_key = f"trains_{origin_code}_{dest_code}_{travel_date.isoformat()}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # 1. Attempt live Indian Rail API call if credentials present
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                url = f"{self.base_url}/api/trains/v1/train/between-stations"
                headers = {
                    "x-rapid-api": "rapid-api-database",
                    "x-rapidapi-host": self.api_host,
                    "x-rapidapi-key": self.api_key
                }
                params = {
                    "fromStationCode": origin_code,
                    "toStationCode": dest_code,
                    "dateOfJourney": travel_date.strftime("%Y%m%d")
                }
                resp = requests.get(url, params=params, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    trains = data.get("data") or data.get("trains") or []
                    if trains:
                        results = []
                        for t in trains:
                            dep_t = str(t.get("departureTime") or t.get("departure_time") or "16:00")
                            arr_t = str(t.get("arrivalTime") or t.get("arrival_time") or "08:30")
                            try:
                                dep_h, dep_m = map(int, dep_t.split(":")[:2])
                                dep_dt = datetime.datetime.combine(travel_date, datetime.time(dep_h, dep_m))
                            except Exception:
                                dep_dt = datetime.datetime.combine(travel_date, datetime.time(16, 0))
                            arr_dt = dep_dt + datetime.timedelta(minutes=int(t.get("durationMinutes") or 480))

                            results.append({
                                "origin": origin_city,
                                "destination": dest_city,
                                "carrier": "Indian Railways",
                                "vehicle_number": str(t.get("trainNumber") or t.get("train_number") or "12951"),
                                "name": str(t.get("trainName") or t.get("train_name") or "Express"),
                                "departure_time": dep_t,
                                "arrival_time": arr_t,
                                "departure_datetime": dep_dt.isoformat(),
                                "arrival_datetime": arr_dt.isoformat(),
                                "duration_minutes": int(t.get("durationMinutes") or 480),
                                "price": float(t.get("fare") or 1250.0),
                                "status": "ON TIME",
                                "type": "train",
                                "data_source": "RapidAPI Indian Railways (Live)",
                                "is_live": True
                            })
                        _save_to_cache(cache_key, results)
                        return results
            except Exception as ex:
                print(f"[TrainServiceAdapter] Live search exception: {ex}")

        # 2. If DEMO_MODE is False and no live data returned
        if not DEMO_MODE:
            return [{
                "origin": origin_city,
                "destination": dest_city,
                "carrier": "Indian Railways",
                "vehicle_number": "N/A",
                "name": "Live Train Data Unavailable",
                "departure_time": "N/A",
                "arrival_time": "N/A",
                "duration_minutes": 0,
                "price": 0.0,
                "status": "Live data unavailable",
                "type": "train",
                "is_live": False,
                "data_source": "Indian Railways API"
            }]

        # 3. DEMO MODE dynamic generator
        return self._generate_dynamic_trains(origin_city, dest_city, origin_code, dest_code, travel_date, after_time)

    def _generate_dynamic_trains(self, origin_city: str, dest_city: str, origin_code: str, dest_code: str, travel_date: datetime.date, after_time: Optional[datetime.time]) -> List[Dict[str, Any]]:
        schedules = [
            {"num": "12127", "name": f"{origin_city}-{dest_city} Pragati Superfast", "dep": "06:30", "arr": "09:50", "dur": 200, "price": 420.0, "status": "DELAYED +240m"},
            {"num": "22119", "name": f"{origin_city}-{dest_city} Tejas Express", "dep": "14:10", "arr": "19:45", "dur": 335, "price": 1450.0, "status": "ON TIME"},
            {"num": "22436", "name": f"{origin_city}-{dest_city} Vande Bharat Express", "dep": "15:15", "arr": "20:30", "dur": 315, "price": 1620.0, "status": "ON TIME"},
            {"num": "12951", "name": f"{origin_city}-{dest_city} Rajdhani Express", "dep": "16:30", "arr": "08:30", "dur": 960, "price": 1850.0, "status": "ON TIME"}
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
                    "status": train["status"],
                    "type": "train",
                    "is_live": False,
                    "data_source": "Deterministic Demo Scenario"
                })
        return results


class FlightServiceAdapter(BaseTransportAdapter):
    """
    Flight API Adapter interfacing with AeroDataBox on RapidAPI and Aviationstack.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.rapidapi_key = api_key or RAPIDAPI_KEY
        self.aviationstack_key = AVIATIONSTACK_API_KEY
        self.rapidapi_host = RAPIDAPI_HOST_FLIGHT

    def get_live_status(self, flight_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        """Queries live flight tracking by flight number."""
        clean_fn = flight_number.strip().upper()
        date_str = travel_date.strftime("%Y-%m-%d")
        cache_key = f"flight_status_{clean_fn}_{date_str}"

        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # 1. Attempt AeroDataBox RapidAPI
        if self.rapidapi_key and not self.rapidapi_key.startswith("your_"):
            try:
                url = f"https://{self.rapidapi_host}/flights/number/{clean_fn}/{date_str}"
                headers = {
                    "x-rapidapi-host": self.rapidapi_host,
                    "x-rapidapi-key": self.rapidapi_key
                }
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        flight_item = data[0]
                        status = {
                            "vehicle_number": clean_fn,
                            "carrier": flight_item.get("airline", {}).get("name", "Airline"),
                            "name": f"Flight {clean_fn}",
                            "status": flight_item.get("status", "ON TIME").upper(),
                            "delay_minutes": flight_item.get("departure", {}).get("delay", 0) or 0,
                            "terminal": flight_item.get("departure", {}).get("terminal", "T1"),
                            "gate": flight_item.get("departure", {}).get("gate", "Gate B4"),
                            "is_live": True,
                            "data_source": "AeroDataBox RapidAPI (Live)",
                            "last_updated": datetime.datetime.now().strftime("%H:%M")
                        }
                        _save_to_cache(cache_key, status)
                        return status
            except Exception as ex:
                print(f"[FlightServiceAdapter] AeroDataBox API note: {ex}")

        # 2. Attempt Aviationstack fallback
        if self.aviationstack_key:
            try:
                url = "http://api.aviationstack.com/v1/flights"
                params = {"access_key": self.aviationstack_key, "flight_iata": clean_fn, "limit": 1}
                resp = requests.get(url, params=params, timeout=4)
                if resp.status_code == 200:
                    raw = resp.json()
                    flights = raw.get("data", [])
                    if flights:
                        f = flights[0]
                        status = {
                            "vehicle_number": clean_fn,
                            "carrier": f.get("airline", {}).get("name", "Airline"),
                            "name": f"Flight {clean_fn}",
                            "status": f.get("flight_status", "scheduled").upper(),
                            "delay_minutes": f.get("departure", {}).get("delay", 0) or 0,
                            "gate": f.get("departure", {}).get("gate", "Gate 3"),
                            "terminal": f.get("departure", {}).get("terminal", "T2"),
                            "is_live": True,
                            "data_source": "Aviationstack (Live)",
                            "last_updated": datetime.datetime.now().strftime("%H:%M")
                        }
                        _save_to_cache(cache_key, status)
                        return status
            except Exception as ex:
                print(f"[FlightServiceAdapter] Aviationstack note: {ex}")

        # 3. Check DEMO_MODE fallback
        if DEMO_MODE:
            return {
                "vehicle_number": clean_fn,
                "carrier": "Air India",
                "name": f"Flight {clean_fn} (Direct Express)",
                "status": "ON TIME",
                "delay_minutes": 0,
                "gate": "Gate 3",
                "terminal": "T1",
                "is_live": False,
                "is_demo": True,
                "data_source": "Deterministic Demo Scenario",
                "last_updated": datetime.datetime.now().strftime("%H:%M")
            }

        # 4. Graceful Fallback
        return {
            "vehicle_number": clean_fn,
            "carrier": "Commercial Carrier",
            "name": f"Flight {clean_fn}",
            "status": "Live flight data unavailable",
            "is_live": False,
            "delay_minutes": 0,
            "message": "Live flight tracking service is currently unreachable or unconfigured.",
            "data_source": "Flight API (Offline)"
        }

    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        origin_iata = LocationResolver.get_iata_code(origin)
        dest_iata = LocationResolver.get_iata_code(destination)
        origin_city = LocationResolver.get_city_name(origin)
        dest_city = LocationResolver.get_city_name(destination)

        # 1. Attempt Aviationstack live search
        if self.aviationstack_key:
            try:
                params = {
                    "access_key": self.aviationstack_key,
                    "dep_iata": origin_iata,
                    "arr_iata": dest_iata,
                    "limit": 5
                }
                resp = requests.get("http://api.aviationstack.com/v1/flights", params=params, timeout=4)
                if resp.status_code == 200:
                    raw = resp.json()
                    flights_data = raw.get("data", [])
                    if flights_data:
                        results = []
                        for f in flights_data:
                            airline_name = f.get("airline", {}).get("name") or "Domestic Carrier"
                            flight_num = f.get("flight", {}).get("iata") or "AI-882"
                            dep_raw = f.get("departure", {}).get("scheduled")
                            arr_raw = f.get("arrival", {}).get("scheduled")
                            try:
                                dep_dt = datetime.datetime.fromisoformat(dep_raw).replace(tzinfo=None)
                                arr_dt = datetime.datetime.fromisoformat(arr_raw).replace(tzinfo=None)
                            except Exception:
                                dep_dt = datetime.datetime.combine(travel_date, datetime.time(15, 10))
                                arr_dt = dep_dt + datetime.timedelta(minutes=65)
                            results.append({
                                "origin": f"{origin_city} ({origin_iata})",
                                "destination": f"{dest_city} ({dest_iata})",
                                "carrier": airline_name,
                                "vehicle_number": flight_num,
                                "name": f"{airline_name} {flight_num}",
                                "departure_time": dep_dt.strftime("%H:%M"),
                                "arrival_time": arr_dt.strftime("%H:%M"),
                                "departure_datetime": dep_dt.isoformat(),
                                "arrival_datetime": arr_dt.isoformat(),
                                "duration_minutes": int((arr_dt - dep_dt).total_seconds() / 60),
                                "price": 4800.0,
                                "status": f.get("flight_status", "ON TIME").upper(),
                                "type": "flight",
                                "is_live": True,
                                "data_source": "Aviationstack (Live)"
                            })
                        if results:
                            return results
            except Exception as ex:
                print(f"[FlightServiceAdapter] Flight search error: {ex}")

        # 2. Check DEMO_MODE
        if DEMO_MODE:
            return self._generate_dynamic_flights(origin_city, dest_city, origin_iata, dest_iata, travel_date, after_time)

        # 3. Graceful fallback
        return [{
            "origin": f"{origin_city} ({origin_iata})",
            "destination": f"{dest_city} ({dest_iata})",
            "carrier": "Commercial Carrier",
            "vehicle_number": "N/A",
            "name": "Live Flight API Unavailable",
            "departure_time": "N/A",
            "arrival_time": "N/A",
            "duration_minutes": 0,
            "price": 0.0,
            "status": "Live data unavailable",
            "type": "flight",
            "is_live": False,
            "data_source": "Flight API (Offline)"
        }]

    def _generate_dynamic_flights(self, origin_city: str, dest_city: str, origin_iata: str, dest_iata: str, travel_date: datetime.date, after_time: Optional[datetime.time]) -> List[Dict[str, Any]]:
        flights_list = [
            {"carrier": "Air India", "fn": "AI-882", "dep": "15:10", "arr": "16:15", "dur": 65, "price": 4900.0},
            {"carrier": "IndiGo", "fn": "6E-409", "dep": "15:45", "arr": "17:10", "dur": 85, "price": 4200.0},
            {"carrier": "Akasa Air", "fn": "QP-1322", "dep": "18:20", "arr": "19:40", "dur": 80, "price": 3800.0}
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
                    "status": "ON TIME",
                    "type": "flight",
                    "is_live": False,
                    "data_source": "Deterministic Demo Scenario"
                })
        return results


class BusServiceAdapter(BaseTransportAdapter):
    """
    Bus API Adapter interfacing with AOPAY Indian Bus Booking API.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or AOPAY_BUS_API_KEY
        self.api_url = "https://api.aopay.in/v2/bus/search"

    def search_routes(self, origin: str, destination: str, travel_date: datetime.date, after_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        origin_city = LocationResolver.get_city_name(origin)
        dest_city = LocationResolver.get_city_name(destination)

        # 1. Attempt AOPAY Bus API call if key is present
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
                payload = {
                    "origin": origin_city,
                    "destination": dest_city,
                    "date": travel_date.strftime("%Y-%m-%d"),
                    "passengers": 1
                }
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success" and "operators" in data:
                        operators = data.get("operators", ["KSRTC", "RedBus", "SRM"])
                        fare = 650.0
                        results = []
                        for idx, op in enumerate(operators):
                            dep_h = 19 + (idx % 4)
                            arr_h = (dep_h + 8) % 24
                            results.append({
                                "origin": origin_city,
                                "destination": dest_city,
                                "carrier": str(op),
                                "vehicle_number": f"MH-{str(op)[:3].upper()}-{100 + idx}",
                                "name": f"{op} AC Multi-Axle Sleeper",
                                "departure_time": f"{dep_h:02d}:30",
                                "arrival_time": f"{arr_h:02d}:15",
                                "departure_datetime": f"{travel_date.isoformat()}T{dep_h:02d}:30:00",
                                "arrival_datetime": f"{travel_date.isoformat()}T{arr_h:02d}:15:00",
                                "duration_minutes": 480,
                                "price": fare + (idx * 150),
                                "status": "ON TIME",
                                "type": "bus",
                                "is_live": True,
                                "data_source": "AOPAY Bus Booking API (Live)"
                            })
                        if results:
                            return results
            except Exception as ex:
                print(f"[BusServiceAdapter] AOPAY API note: {ex}")

        # 2. Check DEMO_MODE
        if DEMO_MODE:
            return self._generate_dynamic_buses(origin_city, dest_city, travel_date, after_time)

        # 3. Graceful fallback
        return [{
            "origin": origin_city,
            "destination": dest_city,
            "carrier": "Intercity Bus Operator",
            "vehicle_number": "N/A",
            "name": "Live bus data unavailable",
            "departure_time": "N/A",
            "arrival_time": "N/A",
            "duration_minutes": 0,
            "price": 0.0,
            "status": "Live bus data unavailable",
            "type": "bus",
            "is_live": False,
            "data_source": "AOPAY Bus API (Offline)"
        }]

    def _generate_dynamic_buses(self, origin_city: str, dest_city: str, travel_date: datetime.date, after_time: Optional[datetime.time]) -> List[Dict[str, Any]]:
        operators = [
            {"carrier": "IntrCity SmartBus", "name": f"{origin_city}-{dest_city} Volvo Multi-Axle Sleeper", "dep": "20:00", "arr": "06:30", "dur": 630, "price": 1100.0},
            {"carrier": "VRL Travels", "name": f"{origin_city}-{dest_city} Scania AC Sleeper", "dep": "21:30", "arr": "07:45", "dur": 615, "price": 1250.0},
            {"carrier": "Neeta Travels", "name": f"{origin_city}-{dest_city} Mercedes Benz B9R", "dep": "22:45", "arr": "08:30", "dur": 585, "price": 1350.0}
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
                    "status": "ON TIME",
                    "type": "bus",
                    "is_live": False,
                    "data_source": "Deterministic Demo Scenario"
                })
        return results

    def get_live_status(self, vehicle_number: str, travel_date: datetime.date) -> Dict[str, Any]:
        return {
            "vehicle_number": vehicle_number,
            "carrier": "Intercity Bus",
            "status": "On Time",
            "delay_minutes": 0,
            "is_live": False,
            "data_source": "Bus Telemetry"
        }
