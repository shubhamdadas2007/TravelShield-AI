"""
Location Resolver & Autocomplete Engine for Indian Transport Hubs.
Resolves user text input (e.g. 'Mumbai', 'Delhi', 'Bengaluru') into:
- Airport IATA Codes (for AOPAY Flight API /v2/flights/search)
- Railway Station Codes (for Indian Rail API TrainBetweenStation)
- Bus City Names (for AOPAY Bus API /v2/bus/search)
"""

from typing import List, Dict, Any, Optional

# Database of Indian commercial airports, major railway stations, and cities
INDIAN_HUB_DATABASE = [
    # Mumbai
    {"name": "Mumbai (Chhatrapati Shivaji Maharaj International Airport)", "city": "Mumbai", "code": "BOM", "type": "airport", "state": "Maharashtra"},
    {"name": "Mumbai CST (Chhatrapati Shivaji Maharaj Terminus)", "city": "Mumbai", "code": "CSMT", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Mumbai Central", "city": "Mumbai", "code": "MMCT", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Lokmanya Tilak Terminus", "city": "Mumbai", "code": "LTT", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Mumbai", "city": "Mumbai", "code": "BOM", "type": "city", "state": "Maharashtra"},

    # Delhi
    {"name": "Delhi (Indira Gandhi International Airport)", "city": "Delhi", "code": "DEL", "type": "airport", "state": "Delhi"},
    {"name": "New Delhi Railway Station", "city": "Delhi", "code": "NDLS", "type": "railway_station", "state": "Delhi"},
    {"name": "Hazrat Nizamuddin", "city": "Delhi", "code": "NZM", "type": "railway_station", "state": "Delhi"},
    {"name": "Old Delhi Junction", "city": "Delhi", "code": "DLI", "type": "railway_station", "state": "Delhi"},
    {"name": "Anand Vihar Terminal", "city": "Delhi", "code": "ANVT", "type": "railway_station", "state": "Delhi"},
    {"name": "Delhi", "city": "Delhi", "code": "DEL", "type": "city", "state": "Delhi"},

    # Bengaluru
    {"name": "Bengaluru (Kempegowda International Airport)", "city": "Bengaluru", "code": "BLR", "type": "airport", "state": "Karnataka"},
    {"name": "KSR Bengaluru City Junction", "city": "Bengaluru", "code": "SBC", "type": "railway_station", "state": "Karnataka"},
    {"name": "Yesvantpur Junction", "city": "Bengaluru", "code": "YPR", "type": "railway_station", "state": "Karnataka"},
    {"name": "Bengaluru", "city": "Bengaluru", "code": "BLR", "type": "city", "state": "Karnataka"},

    # Hyderabad
    {"name": "Hyderabad (Rajiv Gandhi International Airport)", "city": "Hyderabad", "code": "HYD", "type": "airport", "state": "Telangana"},
    {"name": "Secunderabad Junction", "city": "Hyderabad", "code": "SC", "type": "railway_station", "state": "Telangana"},
    {"name": "Hyderabad Deccan Nampally", "city": "Hyderabad", "code": "HYB", "type": "railway_station", "state": "Telangana"},
    {"name": "Kacheguda", "city": "Hyderabad", "code": "KCG", "type": "railway_station", "state": "Telangana"},
    {"name": "Hyderabad", "city": "Hyderabad", "code": "HYD", "type": "city", "state": "Telangana"},

    # Chennai
    {"name": "Chennai (Chennai International Airport)", "city": "Chennai", "code": "MAA", "type": "airport", "state": "Tamil Nadu"},
    {"name": "Puratchi Thalaivar Dr. M.G. Ramachandran Central (Chennai Central)", "city": "Chennai", "code": "MAS", "type": "railway_station", "state": "Tamil Nadu"},
    {"name": "Chennai Egmore", "city": "Chennai", "code": "MS", "type": "railway_station", "state": "Tamil Nadu"},
    {"name": "Chennai", "city": "Chennai", "code": "MAA", "type": "city", "state": "Tamil Nadu"},

    # Kolkata
    {"name": "Kolkata (Netaji Subhash Chandra Bose International Airport)", "city": "Kolkata", "code": "CCU", "type": "airport", "state": "West Bengal"},
    {"name": "Howrah Junction", "city": "Kolkata", "code": "HWH", "type": "railway_station", "state": "West Bengal"},
    {"name": "Sealdah", "city": "Kolkata", "code": "SDAH", "type": "railway_station", "state": "West Bengal"},
    {"name": "Kolkata Shalimar", "city": "Kolkata", "code": "SHM", "type": "railway_station", "state": "West Bengal"},
    {"name": "Kolkata", "city": "Kolkata", "code": "CCU", "type": "city", "state": "West Bengal"},

    # Pune
    {"name": "Pune (Pune International Airport)", "city": "Pune", "code": "PNQ", "type": "airport", "state": "Maharashtra"},
    {"name": "Pune Junction", "city": "Pune", "code": "PUNE", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Pune", "city": "Pune", "code": "PNQ", "type": "city", "state": "Maharashtra"},

    # Goa
    {"name": "Goa (Dabolim Airport)", "city": "Goa", "code": "GOI", "type": "airport", "state": "Goa"},
    {"name": "Goa (Manohar International Airport Mopa)", "city": "Goa", "code": "GOX", "type": "airport", "state": "Goa"},
    {"name": "Madgaon Junction", "city": "Goa", "code": "MAO", "type": "railway_station", "state": "Goa"},
    {"name": "Vasco da Gama", "city": "Goa", "code": "VSG", "type": "railway_station", "state": "Goa"},
    {"name": "Goa", "city": "Goa", "code": "GOI", "type": "city", "state": "Goa"},

    # Ahmedabad
    {"name": "Ahmedabad (Sardar Vallabhbhai Patel International Airport)", "city": "Ahmedabad", "code": "AMD", "type": "airport", "state": "Gujarat"},
    {"name": "Ahmedabad Junction (Kalupur)", "city": "Ahmedabad", "code": "ADI", "type": "railway_station", "state": "Gujarat"},
    {"name": "Ahmedabad", "city": "Ahmedabad", "code": "AMD", "type": "city", "state": "Gujarat"},

    # Jaipur
    {"name": "Jaipur (Jaipur International Airport)", "city": "Jaipur", "code": "JAI", "type": "airport", "state": "Rajasthan"},
    {"name": "Jaipur Junction", "city": "Jaipur", "code": "JP", "type": "railway_station", "state": "Rajasthan"},
    {"name": "Jaipur", "city": "Jaipur", "code": "JAI", "type": "city", "state": "Rajasthan"},

    # Kochi / Cochin
    {"name": "Kochi (Cochin International Airport)", "city": "Kochi", "code": "COK", "type": "airport", "state": "Kerala"},
    {"name": "Ernakulam Junction (South)", "city": "Kochi", "code": "ERS", "type": "railway_station", "state": "Kerala"},
    {"name": "Kochi", "city": "Kochi", "code": "COK", "type": "city", "state": "Kerala"},
]

class LocationResolver:
    @staticmethod
    def autocomplete(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) == 0:
            return INDIAN_HUB_DATABASE[:limit]

        q = query.lower().strip()
        matches = []
        for hub in INDIAN_HUB_DATABASE:
            if (q in hub["name"].lower() or 
                q in hub["city"].lower() or 
                q == hub["code"].lower()):
                matches.append(hub)
                if len(matches) >= limit:
                    break
        return matches

    @staticmethod
    def get_iata_code(location_str: str) -> str:
        """Resolves location string to IATA airport code for Flight APIs"""
        q = location_str.lower().strip()
        for hub in INDIAN_HUB_DATABASE:
            if hub["type"] == "airport" and (q in hub["city"].lower() or q in hub["name"].lower() or q == hub["code"].lower()):
                return hub["code"]
        
        # Default mapping fallbacks if unknown string
        if "delhi" in q: return "DEL"
        if "mumbai" in q: return "BOM"
        if "bengaluru" in q or "bangalore" in q: return "BLR"
        if "hyderabad" in q: return "HYD"
        if "chennai" in q: return "MAA"
        if "kolkata" in q: return "CCU"
        if "pune" in q: return "PNQ"
        if "goa" in q: return "GOI"
        if "ahmedabad" in q: return "AMD"
        if "jaipur" in q: return "JAI"
        return "BOM" # fallback

    @staticmethod
    def get_station_code(location_str: str) -> str:
        """Resolves location string to Railway Station Code for Indian Rail APIs"""
        q = location_str.lower().strip()
        for hub in INDIAN_HUB_DATABASE:
            if hub["type"] == "railway_station" and (q in hub["city"].lower() or q in hub["name"].lower() or q == hub["code"].lower()):
                return hub["code"]

        if "mumbai" in q: return "CSMT"
        if "delhi" in q: return "NDLS"
        if "bengaluru" in q or "bangalore" in q: return "SBC"
        if "hyderabad" in q: return "SC"
        if "chennai" in q: return "MAS"
        if "kolkata" in q: return "HWH"
        if "pune" in q: return "PUNE"
        if "goa" in q: return "MAO"
        if "ahmedabad" in q: return "ADI"
        if "jaipur" in q: return "JP"
        return "NDLS"

    @staticmethod
    def get_city_name(location_str: str) -> str:
        """Resolves location string to clean City Name for Bus APIs"""
        q = location_str.lower().strip()
        for hub in INDIAN_HUB_DATABASE:
            if q in hub["city"].lower() or q in hub["name"].lower() or q == hub["code"].lower():
                return hub["city"]
        return location_str.title().strip()
