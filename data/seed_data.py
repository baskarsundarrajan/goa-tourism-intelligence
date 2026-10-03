"""
seed_data.py  —  curated, DATED, sourced knowledge base for Goa tourism.

This is the reproducible "hybrid sourcing" SEED (and fallback). The live data agent
(tools.py) may top this up with WebSearch; whatever it cannot verify live falls back
to this block. Everything is stamped `AS_OF` and carries a `confidence`, because
tourism figures move and several values here are PLANNING ESTIMATES synthesised from
public knowledge, NOT official statistics.

REFRESH, don't trust blindly: update the entries + AS_OF from primary sources — the
Economic Survey of Goa, the Department of Tourism (Govt of Goa) statistics handbook,
Goa Tourism (https://www.goa-tourism.com), and TTAG. Treat press/aggregator values as
indicative. Carrying capacities below are management planning figures (daily comfort
thresholds), not legally fixed limits.

confidence: high (official/primary), medium (press/established knowledge),
            low (planning estimate / illustrative).
"""

from __future__ import annotations

# Date this knowledge base is treated as current to. Update when you refresh it.
AS_OF = "2026-10-03"

STATE = "Goa"
DISCLAIMER = (
    "Figures are a curated planning knowledge base as of " + AS_OF + ", synthesised "
    "from public knowledge for decision-support. They are NOT official statistics. "
    "Carrying capacities are daily management thresholds, not legal limits. Verify "
    "against the Economic Survey of Goa and the Department of Tourism before use."
)

SOURCES = [
    "https://www.goa-tourism.com/  (Goa Tourism, Dept of Tourism, Govt of Goa)",
    "Economic Survey of Goa / Goa Tourism Statistics handbook (annual)",
    "Travel & Tourism Association of Goa (TTAG) industry briefings",
    "Goa State Pollution Control Board — beach/coastal environmental reports",
    "Drishti Marine (state beach-lifeguard agency) deployment norms",
    "Press: Times of India (Goa), The Navhind Times, Herald (O Heraldo)",
]

# ---------------------------------------------------------------------------
# 1. Districts / zones
# ---------------------------------------------------------------------------
DISTRICTS = [
    {"name": "North Goa", "zone": "north", "hq": "Mapusa / Panaji",
     "note": "Beach-tourism core (Candolim–Baga–Calangute–Anjuna–Vagator), nightlife, "
             "markets, most commercial pressure and overtourism hotspots."},
    {"name": "South Goa", "zone": "south", "hq": "Margao",
     "note": "Quieter, higher-end & eco beaches (Palolem, Agonda, Colva, Benaulim), "
             "turtle-nesting coast, more capacity headroom, growing hinterland/eco tourism."},
]

# ---------------------------------------------------------------------------
# 2. Monthly demand / seasonality  (relative indices 0-100; occupancy % )
#    month: 1-12. domestic_idx & foreign_idx are relative demand indices.
# ---------------------------------------------------------------------------
MONTHLY_DEMAND = [
    {"month": 1,  "month_name": "January",   "season": "peak",      "domestic_idx": 90, "foreign_idx": 95, "occupancy_pct": 82, "note": "Post-New-Year peak; charters at full tilt; North Goa saturated."},
    {"month": 2,  "month_name": "February",  "season": "peak",      "domestic_idx": 85, "foreign_idx": 92, "occupancy_pct": 80, "note": "Carnival month; cultural tourism surge; pleasant weather."},
    {"month": 3,  "month_name": "March",     "season": "shoulder",  "domestic_idx": 70, "foreign_idx": 65, "occupancy_pct": 62, "note": "Shigmo (spring festival); foreign season winding down; warming."},
    {"month": 4,  "month_name": "April",     "season": "shoulder",  "domestic_idx": 60, "foreign_idx": 30, "occupancy_pct": 50, "note": "Hot; domestic long-weekend & wedding traffic; foreigners largely gone."},
    {"month": 5,  "month_name": "May",       "season": "shoulder",  "domestic_idx": 65, "foreign_idx": 20, "occupancy_pct": 52, "note": "Summer-holiday domestic families; hot & humid; pre-monsoon."},
    {"month": 6,  "month_name": "June",      "season": "monsoon",   "domestic_idx": 35, "foreign_idx": 12, "occupancy_pct": 32, "note": "Monsoon onset; Sao Joao; many shacks dismantled; water-sports ban begins."},
    {"month": 7,  "month_name": "July",      "season": "monsoon",   "domestic_idx": 30, "foreign_idx": 10, "occupancy_pct": 30, "note": "Deep monsoon; lush interior/waterfall tourism; sea rough, red-flag beaches."},
    {"month": 8,  "month_name": "August",    "season": "monsoon",   "domestic_idx": 40, "foreign_idx": 12, "occupancy_pct": 38, "note": "Monsoon; Bonderam, Ganesh Chaturthi; Dudhsagar at full flow (restricted)."},
    {"month": 9,  "month_name": "September",  "season": "monsoon",   "domestic_idx": 38, "foreign_idx": 15, "occupancy_pct": 36, "note": "Late monsoon; shoulder recovery begins; MICE/weddings pick up."},
    {"month": 10, "month_name": "October",   "season": "shoulder",  "domestic_idx": 60, "foreign_idx": 55, "occupancy_pct": 58, "note": "Season reopens; shacks re-erected; water sports resume; weather clears."},
    {"month": 11, "month_name": "November",  "season": "peak",      "domestic_idx": 82, "foreign_idx": 85, "occupancy_pct": 75, "note": "IFFI (film festival); charter season starts; strong build-up to Dec."},
    {"month": 12, "month_name": "December",  "season": "peak",      "domestic_idx": 100,"foreign_idx": 100,"occupancy_pct": 92, "note": "Absolute peak: Christmas, New Year, Sunburn, St Francis Xavier feast; gridlock risk."},
]

# ---------------------------------------------------------------------------
# 3. Sites (beaches, heritage, nature) with carrying capacity & sensitivity.
#    carrying_capacity_daily = comfortable daily management threshold (visitors).
#    peak_footfall_daily     = typical observed peak-day footfall.
#    sensitivity: low | medium | high  (ecological/heritage fragility)
# ---------------------------------------------------------------------------
SITES = [
    {"name": "Calangute Beach",        "district": "North Goa", "zone": "north", "type": "beach",     "carrying_capacity_daily": 18000, "peak_footfall_daily": 26000, "sensitivity": "medium", "note": "'Queen of beaches'; most crowded; severe parking/sanitation load at peak."},
    {"name": "Baga Beach",             "district": "North Goa", "zone": "north", "type": "beach",     "carrying_capacity_daily": 15000, "peak_footfall_daily": 23000, "sensitivity": "medium", "note": "Nightlife & water-sports hub; chronic over-capacity and traffic in Dec–Jan."},
    {"name": "Anjuna Beach",           "district": "North Goa", "zone": "north", "type": "beach",     "carrying_capacity_daily": 10000, "peak_footfall_daily": 12500, "sensitivity": "medium", "note": "Flea market, trance/party heritage; cliff erosion concerns."},
    {"name": "Vagator & Chapora",      "district": "North Goa", "zone": "north", "type": "beach",     "carrying_capacity_daily": 8000,  "peak_footfall_daily": 11000, "sensitivity": "medium", "note": "Sunburn festival vicinity; December crowd spikes."},
    {"name": "Morjim Beach",           "district": "North Goa", "zone": "north", "type": "beach",     "carrying_capacity_daily": 4000,  "peak_footfall_daily": 5200,  "sensitivity": "high",   "note": "Olive Ridley turtle nesting (Nov–Mar); noise/light pollution a protected-species risk."},
    {"name": "Palolem Beach",          "district": "South Goa", "zone": "south", "type": "beach",     "carrying_capacity_daily": 8000,  "peak_footfall_daily": 11000, "sensitivity": "high",   "note": "Iconic crescent; silent-disco & kayaking; dolphin trips; crowding degrades the cove."},
    {"name": "Agonda Beach",           "district": "South Goa", "zone": "south", "type": "beach",     "carrying_capacity_daily": 3000,  "peak_footfall_daily": 3200,  "sensitivity": "high",   "note": "Turtle nesting; deliberately low-key eco profile — must stay within capacity."},
    {"name": "Colva Beach",            "district": "South Goa", "zone": "south", "type": "beach",     "carrying_capacity_daily": 12000, "peak_footfall_daily": 14000, "sensitivity": "medium", "note": "Main South-Goa domestic beach; good headroom vs North Goa."},
    {"name": "Galgibaga (Turtle) Beach","district": "South Goa","zone": "south", "type": "beach",     "carrying_capacity_daily": 1500,  "peak_footfall_daily": 1800,  "sensitivity": "high",   "note": "Protected Olive Ridley nesting; strictly low-footfall; vehicles/light restricted."},
    {"name": "Dudhsagar Falls",        "district": "South Goa", "zone": "interior","type": "nature",  "carrying_capacity_daily": 2000,  "peak_footfall_daily": 3500,  "sensitivity": "high",   "note": "Inside Bhagwan Mahaveer Sanctuary; jeep-safari bottleneck; fragile ecosystem."},
    {"name": "Basilica of Bom Jesus & Old Goa", "district": "North Goa", "zone": "north", "type": "heritage", "carrying_capacity_daily": 6000, "peak_footfall_daily": 9000, "sensitivity": "high", "note": "UNESCO World Heritage; St Francis Xavier feast (Dec) & Exposition years draw huge crowds."},
    {"name": "Fort Aguada",            "district": "North Goa", "zone": "north", "type": "heritage", "carrying_capacity_daily": 5000,  "peak_footfall_daily": 7000,  "sensitivity": "medium", "note": "17th-c. Portuguese fort & lighthouse; parking & crowd pinch at sunset."},
    {"name": "Fontainhas (Panaji Latin Quarter)", "district": "North Goa", "zone": "north", "type": "heritage", "carrying_capacity_daily": 3000, "peak_footfall_daily": 3600, "sensitivity": "high", "note": "Living heritage neighbourhood; over-tourism & short-let pressure on residents."},
    {"name": "Divar & Chorao (Salim Ali Bird Sanctuary)", "district": "North Goa", "zone": "interior", "type": "nature", "carrying_capacity_daily": 1200, "peak_footfall_daily": 1000, "sensitivity": "high", "note": "Mangrove birding island; ferry-access; strong eco-/slow-tourism potential with headroom."},
]

# ---------------------------------------------------------------------------
# 4. Attractions / experiences for itinerary building.
#    duration_hr: typical visit length; best_season: peak|shoulder|monsoon|any
# ---------------------------------------------------------------------------
ATTRACTIONS = [
    {"name": "Calangute–Baga water sports",    "zone": "north", "type": "beach",     "duration_hr": 3, "best_season": "peak",     "tags": "beach,adventure,family"},
    {"name": "Anjuna Flea Market",             "zone": "north", "type": "market",    "duration_hr": 2, "best_season": "peak",     "tags": "shopping,culture"},
    {"name": "Saturday Night Market, Arpora",  "zone": "north", "type": "market",    "duration_hr": 3, "best_season": "peak",     "tags": "shopping,food,nightlife"},
    {"name": "Fort Aguada & sunset",           "zone": "north", "type": "heritage",  "duration_hr": 2, "best_season": "any",      "tags": "heritage,views,family"},
    {"name": "Old Goa churches (Bom Jesus/Se)","zone": "north", "type": "heritage",  "duration_hr": 3, "best_season": "any",      "tags": "heritage,culture,pilgrimage"},
    {"name": "Fontainhas heritage walk",       "zone": "north", "type": "heritage",  "duration_hr": 2, "best_season": "any",      "tags": "heritage,culture,walk"},
    {"name": "Mandovi river cruise",           "zone": "north", "type": "leisure",   "duration_hr": 2, "best_season": "any",      "tags": "leisure,culture,family"},
    {"name": "Panaji casinos & nightlife",     "zone": "north", "type": "nightlife", "duration_hr": 4, "best_season": "peak",     "tags": "nightlife,entertainment"},
    {"name": "Spice plantation tour",          "zone": "interior","type": "nature",  "duration_hr": 3, "best_season": "any",      "tags": "nature,food,family"},
    {"name": "Dudhsagar Falls jeep safari",    "zone": "interior","type": "nature",  "duration_hr": 5, "best_season": "monsoon",  "tags": "nature,adventure"},
    {"name": "Divar island slow-cycling",      "zone": "interior","type": "nature",  "duration_hr": 4, "best_season": "shoulder", "tags": "nature,eco,slow"},
    {"name": "Salim Ali bird sanctuary, Chorao","zone": "interior","type": "nature", "duration_hr": 3, "best_season": "monsoon",  "tags": "nature,eco,birding"},
    {"name": "Palolem beach & kayaking",       "zone": "south", "type": "beach",     "duration_hr": 4, "best_season": "peak",     "tags": "beach,adventure,scenic"},
    {"name": "Agonda quiet beach day",         "zone": "south", "type": "beach",     "duration_hr": 4, "best_season": "shoulder", "tags": "beach,eco,wellness"},
    {"name": "Cabo de Rama fort",              "zone": "south", "type": "heritage",  "duration_hr": 2, "best_season": "any",      "tags": "heritage,views,offbeat"},
    {"name": "Butterfly beach boat trip",      "zone": "south", "type": "nature",    "duration_hr": 3, "best_season": "peak",     "tags": "nature,scenic,offbeat"},
    {"name": "Margao market & Latin heritage", "zone": "south", "type": "heritage",  "duration_hr": 2, "best_season": "any",      "tags": "culture,shopping,food"},
    {"name": "Netravali / hinterland eco-trail","zone": "interior","type": "nature", "duration_hr": 5, "best_season": "monsoon",  "tags": "nature,eco,adventure"},
]

# ---------------------------------------------------------------------------
# 5. Local businesses (sample registry) for discovery & ecosystem analysis.
#    rating 0-5; price_band 1-3 ($,$$,$$$); capacity = daily guests served.
#    local_owned: community/Goan MSME ownership; registered: formally licensed.
# ---------------------------------------------------------------------------
BUSINESSES = [
    {"name": "Souza Lobo (Calangute)",         "district": "North Goa", "category": "local_cuisine",    "rating": 4.4, "price_band": 2, "capacity": 250, "local_owned": 1, "registered": 1},
    {"name": "Britto's (Baga)",                "district": "North Goa", "category": "beach_shack",      "rating": 4.1, "price_band": 2, "capacity": 300, "local_owned": 1, "registered": 1},
    {"name": "Thalassa (Vagator)",             "district": "North Goa", "category": "local_cuisine",    "rating": 4.3, "price_band": 3, "capacity": 220, "local_owned": 0, "registered": 1},
    {"name": "Anjuna Homestay Collective",     "district": "North Goa", "category": "homestay",         "rating": 4.2, "price_band": 1, "capacity": 40,  "local_owned": 1, "registered": 1},
    {"name": "Atlantis Water Sports (Baga)",   "district": "North Goa", "category": "water_sports",     "rating": 3.9, "price_band": 2, "capacity": 180, "local_owned": 1, "registered": 1},
    {"name": "GTDC Guided Heritage Tours",     "district": "North Goa", "category": "guided_tours",     "rating": 4.0, "price_band": 1, "capacity": 120, "local_owned": 1, "registered": 1},
    {"name": "Mapusa Friday Market handicraft","district": "North Goa", "category": "handicraft",       "rating": 4.1, "price_band": 1, "capacity": 500, "local_owned": 1, "registered": 0},
    {"name": "Panaji Ayurveda & Yoga Kendra",  "district": "North Goa", "category": "ayurveda_wellness","rating": 4.3, "price_band": 2, "capacity": 60,  "local_owned": 1, "registered": 1},
    {"name": "Palolem Eco Huts",               "district": "South Goa", "category": "eco_stay",         "rating": 4.4, "price_band": 2, "capacity": 70,  "local_owned": 1, "registered": 1},
    {"name": "Agonda Turtle-Friendly Homestay","district": "South Goa", "category": "homestay",         "rating": 4.5, "price_band": 2, "capacity": 30,  "local_owned": 1, "registered": 1},
    {"name": "Colva Beach Shack Assoc.",       "district": "South Goa", "category": "beach_shack",      "rating": 3.8, "price_band": 1, "capacity": 260, "local_owned": 1, "registered": 1},
    {"name": "Fisherman's Wharf (Cavelossim)", "district": "South Goa", "category": "local_cuisine",    "rating": 4.2, "price_band": 3, "capacity": 200, "local_owned": 1, "registered": 1},
    {"name": "South Goa Spice & Farm Tours",   "district": "South Goa", "category": "guided_tours",     "rating": 4.1, "price_band": 1, "capacity": 90,  "local_owned": 1, "registered": 1},
    {"name": "Benaulim Ayurveda Retreat",      "district": "South Goa", "category": "ayurveda_wellness","rating": 4.4, "price_band": 3, "capacity": 50,  "local_owned": 0, "registered": 1},
    {"name": "Netravali Community Eco-Trek",   "district": "South Goa", "category": "eco_stay",         "rating": 4.3, "price_band": 1, "capacity": 40,  "local_owned": 1, "registered": 0},
    {"name": "Cabo de Rama Handloom Co-op",    "district": "South Goa", "category": "handicraft",       "rating": 4.0, "price_band": 1, "capacity": 120, "local_owned": 1, "registered": 0},
]

# "Demand" weight per category — relative tourist demand (0-100), for supply-gap analysis.
CATEGORY_DEMAND = {
    "beach_shack": 95, "local_cuisine": 90, "water_sports": 80, "homestay": 75,
    "guided_tours": 60, "ayurveda_wellness": 65, "handicraft": 55, "eco_stay": 70,
}

# ---------------------------------------------------------------------------
# 6. Festivals & events calendar (crowd-coordination planning).
#    scale: minor|medium|major ; crowd_est = typical peak-day attendance.
# ---------------------------------------------------------------------------
FESTIVALS = [
    {"name": "Goa Carnival",                 "month": 2,  "district": "Statewide (Panaji float parade)", "zone": "north", "scale": "major",  "duration_days": 4,  "type": "cultural",  "crowd_est": 120000, "note": "Float parades (Panaji, Margao, Vasco, Mapusa); King Momo; huge street crowds."},
    {"name": "Shigmo (Shigmotsav)",          "month": 3,  "district": "Statewide",                        "zone": "both",  "scale": "major",  "duration_days": 14, "type": "cultural",  "crowd_est": 80000,  "note": "Spring/harvest festival; parades of floats & folk troupes across towns."},
    {"name": "Sao Joao (feast of St John)",  "month": 6,  "district": "North Goa (Siolim/Bardez)",        "zone": "north", "scale": "medium", "duration_days": 1,  "type": "religious", "crowd_est": 25000,  "note": "Monsoon well-jumping festival; boats & revelry; alcohol-safety & water-safety load."},
    {"name": "Bonderam (Divar flag festival)","month": 8, "district": "Divar Island",                     "zone": "interior","scale":"medium", "duration_days": 1,  "type": "cultural",  "crowd_est": 15000,  "note": "Mock-fight flag festival; ferry-access island — transport bottleneck."},
    {"name": "Ganesh Chaturthi (Chavath)",   "month": 9,  "district": "Statewide",                        "zone": "both",  "scale": "major",  "duration_days": 10, "type": "religious", "crowd_est": 60000,  "note": "Biggest Hindu festival in Goa; idol immersions — water-body & crowd management."},
    {"name": "IFFI (Intl Film Festival of India)","month":11,"district":"Panaji",                         "zone": "north", "scale": "major",  "duration_days": 9,  "type": "cultural",  "crowd_est": 40000,  "note": "National film festival; delegates, VIP security, venue logistics in the capital."},
    {"name": "Feast of St Francis Xavier",   "month": 12, "district": "Old Goa",                           "zone": "north", "scale": "major",  "duration_days": 9,  "type": "religious", "crowd_est": 150000, "note": "9-day novena at Old Goa; Exposition years (decennial) draw millions — extreme crowd load."},
    {"name": "Sunburn Festival (EDM)",       "month": 12, "district": "North Goa (Vagator area)",         "zone": "north", "scale": "major",  "duration_days": 3,  "type": "music",     "crowd_est": 110000, "note": "Asia's largest EDM festival; traffic, noise, drug-enforcement & medical load."},
    {"name": "Serendipity Arts Festival",    "month": 12, "district": "Panaji",                            "zone": "north", "scale": "medium", "duration_days": 8,  "type": "arts",      "crowd_est": 35000,  "note": "Multidisciplinary arts festival along the Mandovi; venue & footfall spread."},
    {"name": "Christmas & New Year",         "month": 12, "district": "Statewide",                         "zone": "both",  "scale": "major",  "duration_days": 10, "type": "tourism",   "crowd_est": 200000, "note": "Peak tourist season climax; beaches, parties, churches — statewide gridlock risk."},
    {"name": "Goa Liberation Day",           "month": 12, "district": "Statewide",                         "zone": "both",  "scale": "minor",  "duration_days": 1,  "type": "civic",     "crowd_est": 10000,  "note": "19 Dec state holiday; official functions & local gatherings."},
]
