"""
Location Resolver & Autocomplete Engine for Indian Transport Hubs.
Resolves user text input into:
- Railway Stations with IRCTC Station Codes (CSMT, NDLS, PUNE, etc.)
- Airports with IATA Codes (BOM, DEL, PNQ, BLR, GOI, GOX, etc.)
- Bus Terminals & Hubs (Swargate, Mapusa, Borivali, Majestic, etc.)
"""

from typing import List, Dict, Any, Optional

INDIAN_HUB_DATABASE = [
    # Mumbai
    {"name": "Mumbai (Chhatrapati Shivaji Maharaj International Airport)", "city": "Mumbai", "code": "BOM", "type": "airport", "state": "Maharashtra"},
    {"name": "Chhatrapati Shivaji Maharaj Terminus (CSMT)", "city": "Mumbai", "code": "CSMT", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Mumbai Central (MMCT)", "city": "Mumbai", "code": "MMCT", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Lokmanya Tilak Terminus (LTT)", "city": "Mumbai", "code": "LTT", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Borivali Station & Bus Terminal", "city": "Mumbai", "code": "BVI", "type": "bus_station", "state": "Maharashtra"},
    {"name": "Thane Station", "city": "Mumbai", "code": "TNA", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Panvel Junction", "city": "Mumbai", "code": "PNVL", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Mumbai", "city": "Mumbai", "code": "BOM", "type": "city", "state": "Maharashtra"},

    # Pune
    {"name": "Pune International Airport (PNQ)", "city": "Pune", "code": "PNQ", "type": "airport", "state": "Maharashtra"},
    {"name": "Pune Junction (PUNE)", "city": "Pune", "code": "PUNE", "type": "railway_station", "state": "Maharashtra"},
    {"name": "Swargate Intercity Bus Terminal", "city": "Pune", "code": "SWG", "type": "bus_station", "state": "Maharashtra"},
    {"name": "Shivajinagar Bus & Rail Hub", "city": "Pune", "code": "SVJR", "type": "bus_station", "state": "Maharashtra"},
    {"name": "Pune", "city": "Pune", "code": "PNQ", "type": "city", "state": "Maharashtra"},

    # Goa
    {"name": "Goa Dabolim Airport (GOI)", "city": "Goa", "code": "GOI", "type": "airport", "state": "Goa"},
    {"name": "Manohar International Airport Mopa (GOX)", "city": "Goa", "code": "GOX", "type": "airport", "state": "Goa"},
    {"name": "Madgaon Junction (MAO)", "city": "Goa", "code": "MAO", "type": "railway_station", "state": "Goa"},
    {"name": "Thivim Railway Station (THVM)", "city": "Goa", "code": "THVM", "type": "railway_station", "state": "Goa"},
    {"name": "Vasco da Gama (VSG)", "city": "Goa", "code": "VSG", "type": "railway_station", "state": "Goa"},
    {"name": "Panaji Central Bus Stand", "city": "Goa", "code": "PAN", "type": "bus_station", "state": "Goa"},
    {"name": "Mapusa Interstate Bus Stand", "city": "Goa", "code": "MAP", "type": "bus_station", "state": "Goa"},
    {"name": "Goa", "city": "Goa", "code": "GOI", "type": "city", "state": "Goa"},

    # Delhi
    {"name": "Indira Gandhi International Airport (DEL)", "city": "Delhi", "code": "DEL", "type": "airport", "state": "Delhi"},
    {"name": "New Delhi Railway Station (NDLS)", "city": "Delhi", "code": "NDLS", "type": "railway_station", "state": "Delhi"},
    {"name": "Hazrat Nizamuddin (NZM)", "city": "Delhi", "code": "NZM", "type": "railway_station", "state": "Delhi"},
    {"name": "Anand Vihar ISBT & Rail Terminal", "city": "Delhi", "code": "ANVT", "type": "bus_station", "state": "Delhi"},
    {"name": "Kashmere Gate ISBT", "city": "Delhi", "code": "ISBT", "type": "bus_station", "state": "Delhi"},
    {"name": "Delhi", "city": "Delhi", "code": "DEL", "type": "city", "state": "Delhi"},

    # Bengaluru
    {"name": "Kempegowda International Airport (BLR)", "city": "Bengaluru", "code": "BLR", "type": "airport", "state": "Karnataka"},
    {"name": "KSR Bengaluru City Junction (SBC)", "city": "Bengaluru", "code": "SBC", "type": "railway_station", "state": "Karnataka"},
    {"name": "Yesvantpur Junction (YPR)", "city": "Bengaluru", "code": "YPR", "type": "railway_station", "state": "Karnataka"},
    {"name": "Majestic KSRTC Intercity Bus Station", "city": "Bengaluru", "code": "MAJ", "type": "bus_station", "state": "Karnataka"},
    {"name": "Bengaluru", "city": "Bengaluru", "code": "BLR", "type": "city", "state": "Karnataka"},

    # Hyderabad
    {"name": "Rajiv Gandhi International Airport (HYD)", "city": "Hyderabad", "code": "HYD", "type": "airport", "state": "Telangana"},
    {"name": "Secunderabad Junction (SC)", "city": "Hyderabad", "code": "SC", "type": "railway_station", "state": "Telangana"},
    {"name": "Hyderabad Deccan Nampally (HYB)", "city": "Hyderabad", "code": "HYB", "type": "railway_station", "state": "Telangana"},
    {"name": "MGBS Central Bus Station", "city": "Hyderabad", "code": "MGBS", "type": "bus_station", "state": "Telangana"},
    {"name": "Hyderabad", "city": "Hyderabad", "code": "HYD", "type": "city", "state": "Telangana"},

    # Chennai
    {"name": "Chennai International Airport (MAA)", "city": "Chennai", "code": "MAA", "type": "airport", "state": "Tamil Nadu"},
    {"name": "Puratchi Thalaivar MGR Central (MAS)", "city": "Chennai", "code": "MAS", "type": "railway_station", "state": "Tamil Nadu"},
    {"name": "Chennai Egmore (MS)", "city": "Chennai", "code": "MS", "type": "railway_station", "state": "Tamil Nadu"},
    {"name": "CMBT Koyambedu Bus Terminal", "city": "Chennai", "code": "CMBT", "type": "bus_station", "state": "Tamil Nadu"},
    {"name": "Chennai", "city": "Chennai", "code": "MAA", "type": "city", "state": "Tamil Nadu"},

    # Kolkata
    {"name": "Netaji Subhash Chandra Bose Airport (CCU)", "city": "Kolkata", "code": "CCU", "type": "airport", "state": "West Bengal"},
    {"name": "Howrah Junction (HWH)", "city": "Kolkata", "code": "HWH", "type": "railway_station", "state": "West Bengal"},
    {"name": "Sealdah (SDAH)", "city": "Kolkata", "code": "SDAH", "type": "railway_station", "state": "West Bengal"},
    {"name": "Esplanade Bus Terminus", "city": "Kolkata", "code": "ESP", "type": "bus_station", "state": "West Bengal"},
    {"name": "Kolkata", "city": "Kolkata", "code": "CCU", "type": "city", "state": "West Bengal"},

    # Ahmedabad
    {"name": "Sardar Vallabhbhai Patel Airport (AMD)", "city": "Ahmedabad", "code": "AMD", "type": "airport", "state": "Gujarat"},
    {"name": "Ahmedabad Junction (ADI)", "city": "Ahmedabad", "code": "ADI", "type": "railway_station", "state": "Gujarat"},
    {"name": "Geeta Mandir Central Bus Stand", "city": "Ahmedabad", "code": "GMD", "type": "bus_station", "state": "Gujarat"},
    {"name": "Ahmedabad", "city": "Ahmedabad", "code": "AMD", "type": "city", "state": "Gujarat"},

    # Jaipur
    {"name": "Jaipur International Airport (JAI)", "city": "Jaipur", "code": "JAI", "type": "airport", "state": "Rajasthan"},
    {"name": "Jaipur Junction (JP)", "city": "Jaipur", "code": "JP", "type": "railway_station", "state": "Rajasthan"},
    {"name": "Sindhi Camp Central Bus Stand", "city": "Jaipur", "code": "SCMP", "type": "bus_station", "state": "Rajasthan"},
    {"name": "Jaipur", "city": "Jaipur", "code": "JAI", "type": "city", "state": "Rajasthan"},
]


class LocationResolver:
    @staticmethod
    def autocomplete(query: str, mode: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Returns matching locations filtered by transport mode."""
        q = query.lower().strip() if query else ""
        type_filters = {
            "train": ["railway_station", "city"],
            "flight": ["airport", "city"],
            "bus": ["bus_station", "city"],
            "all": ["airport", "railway_station", "bus_station", "city"]
        }
        allowed_types = type_filters.get(mode.lower(), type_filters["all"])

        matches = []
        for hub in INDIAN_HUB_DATABASE:
            if hub["type"] not in allowed_types:
                continue
            if not q or (
                q in hub["name"].lower() or 
                q in hub["city"].lower() or 
                q == hub["code"].lower()
            ):
                matches.append(hub)
                if len(matches) >= limit:
                    break
        return matches

    @staticmethod
    def get_iata_code(location_str: str) -> str:
        loc = location_str.lower()
        if "bom" in loc or "mumbai" in loc: return "BOM"
        if "del" in loc or "delhi" in loc: return "DEL"
        if "blr" in loc or "bengaluru" in loc or "bangalore" in loc: return "BLR"
        if "hyd" in loc or "hyderabad" in loc: return "HYD"
        if "maa" in loc or "chennai" in loc: return "MAA"
        if "ccu" in loc or "kolkata" in loc: return "CCU"
        if "pnq" in loc or "pune" in loc: return "PNQ"
        if "gox" in loc or "mopa" in loc: return "GOX"
        if "goi" in loc or "goa" in loc: return "GOI"
        if "amd" in loc or "ahmedabad" in loc: return "AMD"
        if "jai" in loc or "jaipur" in loc: return "JAI"
        return "BOM"

    @staticmethod
    def get_station_code(location_str: str) -> str:
        loc = location_str.lower()
        if "csmt" in loc: return "CSMT"
        if "mmct" in loc or "mumbai central" in loc: return "MMCT"
        if "ltt" in loc: return "LTT"
        if "mumbai" in loc: return "CSMT"
        if "pune" in loc: return "PUNE"
        if "ndls" in loc or "new delhi" in loc or "delhi" in loc: return "NDLS"
        if "nzm" in loc or "nizamuddin" in loc: return "NZM"
        if "sbc" in loc or "bengaluru" in loc: return "SBC"
        if "ypr" in loc or "yesvantpur" in loc: return "YPR"
        if "sc" in loc or "secunderabad" in loc or "hyderabad" in loc: return "SC"
        if "hyb" in loc: return "HYB"
        if "mas" in loc or "chennai" in loc: return "MAS"
        if "hwh" in loc or "howrah" in loc or "kolkata" in loc: return "HWH"
        if "sdah" in loc or "sealdah" in loc: return "SDAH"
        if "mao" in loc or "madgaon" in loc or "goa" in loc: return "MAO"
        if "thvm" in loc or "thivim" in loc: return "THVM"
        if "vsg" in loc or "vasco" in loc: return "VSG"
        if "adi" in loc or "ahmedabad" in loc: return "ADI"
        if "jp" in loc or "jaipur" in loc: return "JP"
        return "CSMT"

    @staticmethod
    def get_city_name(location_str: str) -> str:
        loc = location_str.lower()
        for city in ["Mumbai", "Pune", "Goa", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Jaipur"]:
            if city.lower() in loc:
                return city
        for hub in INDIAN_HUB_DATABASE:
            if hub["code"].lower() in loc:
                return hub["city"]
        return location_str.split()[0].replace(",", "").capitalize()
