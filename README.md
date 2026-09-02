# TravelShield AI — Multimodal Travel Disruption Recovery Engine

TravelShield AI is an intelligent, agentic travel recovery platform that understands how travel disruptions (delays, cancellations, schedule shifts, missed connections) cause chain reactions across multi-leg journeys (Flights, Trains, Buses, Hotels, Activities) anywhere in India and automatically generates, ranks, and applies optimal recovery plans.

---

## Key Features

- **Dynamic Indian Route Search**:
  - Search any origin & destination pair in India across **Flights**, **Trains**, and **Buses** without hardcoded routes.
  - Station & Airport Autocomplete with IATA/Station Code resolver (`AutoCompleteStation` / `StationCodeOrName`).
  - Unified results dashboard with category tabs (`[ ALL ] [ ✈ FLIGHTS ] [ 🚆 TRAINS ] [ 🚌 BUSES ]`) and sorting filters (`Cheapest`, `Fastest`, `Earliest`, `Direct`).
- **Disruption Recovery Engine**:
  - Handles delays, cancellations, expected arrival shifts, and missed connections.
  - Evaluates minimum connection buffers, hotel check-in delays, and missed activities.
  - Multi-objective scoring algorithm tailored to traveler preference tiers (`Budget`, `Balanced`, `Speed`).
  - **Gemini AI Engine**: Generates synthesized trade-off explanations and powers interactive travel assistant chat.
- **Firebase Authentication & Authorization**:
  - Email/Password login & registration.
  - **Automatic Email Verification Link** with unverified status banner & resend triggers.
  - Google Sign-In & Anonymous Guest access.
  - Backend JWT ID Token verification middleware.
- **Modern Travel Management Dashboard**:
  - 4 KPI metric cards (Total Bookings, Pending Issues, Active Customers, Total Revenue/Saved).
  - Monthly revenue & recovery trend bar chart.
  - Color-coded live activity feed.
  - Dedicated Disruption Recovery Center.

---

## Tech Stack

- **Backend**: FastAPI (Python 3.13), SQLAlchemy, Pydantic, Uvicorn, Pytest
- **AI Engine**: Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-pro`)
- **Authentication**: Firebase Authentication & Authorization (Web JS SDK v10)
- **External Transport APIs**:
  - AOPAY Flight API (`/v2/flights/search`)
  - AOPAY Bus API (`/v2/bus/search`)
  - Indian Rail API (`TrainBetweenStation`, live disruption telemetry)
- **Frontend**: Vanilla HTML5, Modern CSS Design System (TripAero light/navy theme), Vanilla JS SPA

---

## Quickstart

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone <YOUR_REPOSITORY_URL>
cd TravelShield
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```

### 3. Run Automated Tests
```bash
python -m pytest
```

### 4. Start Local Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## License
MIT License
