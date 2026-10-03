"""
domains.py  —  the five Goa-tourism task domains, each with a deterministic analyzer.

Each domain exposes:
  * metadata (key, title, icon, blurb) and an `inputs` form schema for the GUI,
  * `analyze(params) -> engine.Result`  — the keyless, reproducible core that reads
    the seeded database and produces a scored verdict + manpower/resource plan,
  * `dims` (the weighted dimensions) and `subagents` (slices the deep-agent delegates
    to in the agentic path).

The analyzers are the single source of truth for every number the system reports; the
LLM layer only narrates and orchestrates on top of them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import engine
from data import db, seed_data as S

NORTH_SHARE = 0.62        # share of statewide tourist load carried by North Goa
SOUTH_SHARE = 0.38
PEAK_DAILY_STATE = 360000  # planning estimate of peak-day tourist presence (statewide)

SEASON_LABEL = {"peak": "peak season", "shoulder": "shoulder season",
                "monsoon": "monsoon / low season"}


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------
def season_of(month: int) -> str:
    m = db.month_demand(int(month)) or {}
    return m.get("season", "shoulder")


def composite_demand(m: dict) -> int:
    """Blend domestic & foreign demand indices into one 0-100 pressure index."""
    return round(0.55 * m["domestic_idx"] + 0.45 * m["foreign_idx"])


def _finding(topic, value, detail, conf="medium"):
    return {"topic": topic, "value": value, "detail": detail,
            "source": "Goa tourism knowledge base (seed_data.py)", "confidence": conf}


# ---------------------------------------------------------------------------
# Domain descriptor
# ---------------------------------------------------------------------------
@dataclass
class Domain:
    key: str
    title: str
    icon: str
    blurb: str
    dims: list[engine.Dim]
    inputs: list[dict]
    analyze: Callable[[dict], engine.Result]
    subagents: list[dict] = field(default_factory=list)


# ===========================================================================
# 1. SEASONAL DEMAND PLANNING
# ===========================================================================
_SEASONAL_DIMS = [
    engine.Dim("demand_absorption", "Accommodation & Demand Absorption", 0.30),
    engine.Dim("manpower_adequacy", "Safety & Service Manpower Adequacy", 0.25),
    engine.Dim("infrastructure_load", "Transport / Sanitation Headroom", 0.20),
    engine.Dim("revenue_distribution", "Geographic Revenue Spread", 0.15),
    engine.Dim("resilience", "Weather & Over-tourism Resilience", 0.10),
]


def analyze_seasonal(params: dict) -> engine.Result:
    month = int(params.get("month") or 12)
    zone = (params.get("zone") or "both").lower()
    m = db.month_demand(month)
    season = m["season"]
    cd = composite_demand(m)
    occ = m["occupancy_pct"]

    share = 1.0 if zone == "both" else (NORTH_SHARE if zone == "north" else SOUTH_SHARE)
    footfall = round(PEAK_DAILY_STATE * cd / 100 * share)

    demand_absorption = engine.clamp(100 - (occ - 50) * 1.6)
    manpower_adequacy = engine.clamp(100 - max(0, cd - 55) * 1.4)
    infrastructure_load = engine.clamp(100 - (0.5 * cd + 0.5 * occ - 40) * 1.3)
    revenue_distribution = engine.clamp(
        100 - (NORTH_SHARE * 100 - 50) * 2 + (12 if zone == "south" else 0))
    resilience = engine.clamp(85 - max(0, cd - 50) * 0.9 - (12 if season == "monsoon" else 0))

    dims = [
        engine.DimScore("demand_absorption", _SEASONAL_DIMS[0].name, 0.30, demand_absorption,
                        f"Hotel occupancy ~{occ}% in {m['month_name']}; "
                        f"{'little headroom — promote homestays/South Goa & staggered stays'
                           if occ > 80 else 'workable headroom for additional arrivals'}."),
        engine.DimScore("manpower_adequacy", _SEASONAL_DIMS[1].name, 0.25, manpower_adequacy,
                        f"Composite demand index {cd}/100; "
                        f"{'surge deployment needed above the shoulder-season baseline'
                           if cd > 55 else 'baseline deployment broadly sufficient'}."),
        engine.DimScore("infrastructure_load", _SEASONAL_DIMS[2].name, 0.20, infrastructure_load,
                        f"Combined demand+occupancy load; transport, parking and sanitation "
                        f"{'under strain' if infrastructure_load < 55 else 'within tolerance'}."),
        engine.DimScore("revenue_distribution", _SEASONAL_DIMS[3].name, 0.15, revenue_distribution,
                        f"~{int(NORTH_SHARE*100)}% of load concentrates in North Goa; "
                        f"spreading demand to South Goa & the hinterland improves balance."),
        engine.DimScore("resilience", _SEASONAL_DIMS[4].name, 0.10, resilience,
                        f"{SEASON_LABEL[season].title()}: "
                        f"{'monsoon weather risk but low crowds' if season=='monsoon'
                           else 'little slack to absorb shocks at this demand level'}."),
    ]
    base = engine.weighted_index(dims)
    gates = [
        (occ >= 90 and cd >= 90, engine.Gate(
            "saturation_gate",
            f"Accommodation ~{occ}% occupied at demand {cd}/100 — the destination is "
            f"effectively saturated; unmanaged arrivals risk gridlock and service failure.",
            52, "Activate a peak-season management plan: park-and-ride, timed beach access "
                "at hotspots, demand diversion to South Goa/hinterland, and surge staffing.")),
    ]
    idx, fired = engine.apply_gates(base, gates)
    band = engine.band_for(idx)

    manpower = engine.plan_manpower(footfall)
    resources = engine.plan_resources(footfall)

    recs = [
        f"Deploy a seasonal surge of ~{engine.total_headcount(manpower):,} field staff "
        f"across tourism police, Drishti lifeguards, sanitation and traffic for {m['month_name']}.",
        "Stand up park-and-ride shuttles at Calangute/Baga/Anjuna to cut private-vehicle "
        "congestion on the North-Goa beach belt.",
    ]
    if occ > 80:
        recs.append("Incentivise registered homestays and South-Goa/hinterland stays to relieve "
                    "North-Goa accommodation saturation and spread visitor spend.")
    if season == "monsoon":
        recs.append("Promote monsoon & hinterland products (Dudhsagar, spice farms, birding, "
                    "wellness) to smooth the demand trough and sustain off-season livelihoods.")
    else:
        recs.append("Pre-position a unified traffic plan and real-time beach-occupancy signage "
                    "ahead of weekend and festival peaks.")

    risks = [
        {"risk": "Beach & road overcrowding at North-Goa hotspots", "likelihood": "H" if cd > 80 else "M",
         "impact": "H", "mitigation": "Timed access, park-and-ride, live occupancy dashboards"},
        {"risk": "Sanitation & solid-waste overload", "likelihood": "H" if occ > 80 else "M",
         "impact": "M", "mitigation": "Surge sanitation crews, extra bins & daily lifting"},
        {"risk": "Water-safety incidents at peak footfall", "likelihood": "M", "impact": "H",
         "mitigation": "Full Drishti lifeguard deployment, flag discipline, patrols"},
    ]
    findings = [
        _finding(f"{m['month_name']} demand", f"domestic {m['domestic_idx']}/100, foreign "
                 f"{m['foreign_idx']}/100 ({SEASON_LABEL[season]})", m["note"], "medium"),
        _finding("Hotel occupancy", f"~{occ}%", "Headroom shrinks sharply in Dec–Jan; shoulder "
                 "and monsoon months carry spare capacity.", "low"),
        _finding("Projected daily footfall",
                 f"~{footfall:,} visitors/day ({'statewide' if zone=='both' else zone+' Goa'})",
                 "Planning estimate scaled from the demand index; drives the manpower & "
                 "resource deployment below.", "low"),
    ]

    return engine.Result(
        domain="seasonal", title=DOMAINS_META["seasonal"]["title"], icon=DOMAINS_META["seasonal"]["icon"],
        scenario=f"{m['month_name']} ({SEASON_LABEL[season]}) — "
                 f"{'statewide' if zone=='both' else zone.title()+' Goa'}",
        index=idx, base_index=base, band=band, dimensions=dims,
        headline=f"{m['month_name']}: demand {cd}/100, ~{footfall:,} visitors/day — {band.label}",
        findings=findings, manpower=manpower, resources=resources, recommendations=recs,
        risks=risks, gates_fired=fired,
        extra={"composite_demand": cd, "occupancy_pct": occ, "season": season,
               "projected_daily_footfall": footfall,
               "total_recommended_headcount": engine.total_headcount(manpower)},
        params={"month": month, "zone": zone}, as_of=S.AS_OF)


# ===========================================================================
# 2. ITINERARY / ROUTE RECOMMENDATION
# ===========================================================================
_ITIN_DIMS = [
    engine.Dim("experience_coverage", "Interest Coverage", 0.30),
    engine.Dim("travel_efficiency", "Travel Efficiency (low transfers)", 0.25),
    engine.Dim("sustainability_fit", "Sustainability Fit (avoids over-capacity)", 0.25),
    engine.Dim("seasonal_suitability", "Seasonal Suitability", 0.20),
]
_PACE_SLOTS = {"relaxed": 2, "balanced": 3, "packed": 4}


def analyze_itinerary(params: dict) -> engine.Result:
    days = max(1, min(14, int(params.get("days") or 3)))
    zone_pref = (params.get("zone") or "both").lower()
    interests = params.get("interests") or ["beach", "heritage", "nature"]
    if isinstance(interests, str):
        interests = [x.strip() for x in interests.split(",") if x.strip()]
    month = int(params.get("month") or 12)
    pace = (params.get("pace") or "balanced").lower()
    season = season_of(month)
    per_day = _PACE_SLOTS.get(pace, 3)
    slots = days * per_day

    atts = db.attractions()
    scored = []
    for a in atts:
        tagset = set(a["tags"].split(","))
        match = len(tagset & set(interests))
        off_zone = (zone_pref in ("north", "south") and a["zone"] not in (zone_pref, "interior"))
        season_fit = 1 if a["best_season"] in (season, "any") else 0
        over_cap = 1 if (season == "peak" and "beach" in tagset and a["zone"] == "north") else 0
        score = match * 3 + season_fit * 2 - (2 if off_zone else 0) - over_cap
        scored.append({"a": a, "score": score, "over_cap": over_cap,
                       "season_fit": season_fit, "match": match, "tags": tagset})
    scored.sort(key=lambda x: -x["score"])
    picked = scored[:slots]

    # cluster by zone to reduce transfers, then lay out day by day
    byzone: dict[str, list] = {}
    for p in picked:
        byzone.setdefault(p["a"]["zone"], []).append(p)
    flat = [p for z in byzone for p in byzone[z]]
    day_plan = []
    for d in range(days):
        chunk = flat[d * per_day:(d + 1) * per_day]
        if not chunk:
            break
        day_plan.append({
            "day": d + 1, "zone": chunk[0]["a"]["zone"],
            "items": [{"name": c["a"]["name"], "type": c["a"]["type"],
                       "duration_hr": c["a"]["duration_hr"], "zone": c["a"]["zone"],
                       "over_capacity": bool(c["over_cap"])} for c in chunk]})

    zones_seq = [d["zone"] for d in day_plan]
    switches = sum(1 for i in range(1, len(zones_seq)) if zones_seq[i] != zones_seq[i - 1])
    covered = set().union(*[p["tags"] for p in picked]) & set(interests) if picked else set()

    experience_coverage = engine.clamp(100 * len(covered) / max(1, len(interests)))
    travel_efficiency = engine.clamp(100 - switches * 15)
    overcap_n = sum(1 for p in picked if p["over_cap"])
    sustainability_fit = engine.clamp(100 - overcap_n * 20)
    seasonal_suitability = engine.clamp(100 * sum(p["season_fit"] for p in picked) / max(1, len(picked)))

    dims = [
        engine.DimScore("experience_coverage", _ITIN_DIMS[0].name, 0.30, experience_coverage,
                        f"Covers {len(covered)}/{len(interests)} requested interests "
                        f"({', '.join(sorted(covered)) or 'none'})."),
        engine.DimScore("travel_efficiency", _ITIN_DIMS[1].name, 0.25, travel_efficiency,
                        f"{switches} inter-zone transfer(s) across {len(day_plan)} day(s); "
                        f"itinerary clustered by area to minimise travel."),
        engine.DimScore("sustainability_fit", _ITIN_DIMS[2].name, 0.25, sustainability_fit,
                        f"{overcap_n} stop(s) fall on over-capacity North-Goa beaches in "
                        f"{SEASON_LABEL[season]}; "
                        f"{'rebalance toward South Goa/hinterland' if overcap_n else 'low over-tourism exposure'}."),
        engine.DimScore("seasonal_suitability", _ITIN_DIMS[3].name, 0.20, seasonal_suitability,
                        f"{int(seasonal_suitability)}% of stops are in-season for "
                        f"{SEASON_LABEL[season]}."),
    ]
    base = engine.weighted_index(dims)
    idx, fired = engine.apply_gates(base, [])
    band = engine.band_for(idx)

    # route-support (government enablement, not a mass deployment)
    manpower = [
        {"role": "Certified Local Guides", "basis": f"~2 per day × {days} day(s)",
         "recommended": days * 2, "note": "Prefer trained Goan/community guides on the route"},
        {"role": "Tourist Facilitators (route help desks)", "basis": "≥1 per zone cluster",
         "recommended": max(2, len(set(zones_seq))), "note": "Multilingual assistance at hubs"},
    ]
    resources = [
        {"item": "Wayfinding Signage (route sets)", "basis": "1 set per stop",
         "recommended": len(picked), "note": "Bilingual + QR to live info"},
        {"item": "EV / Shuttle Links (route)", "basis": "1 per inter-zone leg",
         "recommended": max(1, switches), "note": "Low-carbon transfers between zones"},
    ]
    recs = [
        f"Package this {days}-day {pace} route and publish it on the official Goa Tourism app "
        f"with live site-occupancy and transport links.",
    ]
    if overcap_n:
        recs.append("Rebalance the beach legs toward South-Goa/hinterland alternatives during "
                    "peak season to ease pressure on Calangute/Baga/Anjuna.")
    if len(covered) < len(interests):
        missing = set(interests) - covered
        recs.append(f"Develop/curate products for under-served interests: {', '.join(sorted(missing))}.")
    recs.append("Deploy certified local guides and bilingual wayfinding signage along the route "
                "to raise quality and spread spend to communities.")

    risks = [
        {"risk": "Peak-season congestion on popular beach legs",
         "likelihood": "H" if overcap_n else "M", "impact": "M",
         "mitigation": "Timed visits, South-Goa alternatives, shuttle links"},
        {"risk": "Weather disruption to monsoon/outdoor stops", "likelihood": "M",
         "impact": "M", "mitigation": "Flexible indoor/heritage fallbacks per day"},
    ]
    findings = [
        _finding("Season", SEASON_LABEL[season], f"Month {month}; attraction selection weighted "
                 "to in-season, interest-matched stops.", "medium"),
        _finding("Requested interests", ", ".join(interests), "Used to score and select stops.", "high"),
    ]

    return engine.Result(
        domain="itinerary", title=DOMAINS_META["itinerary"]["title"], icon=DOMAINS_META["itinerary"]["icon"],
        scenario=f"{days}-day {pace} route · {SEASON_LABEL[season]} · "
                 f"{'any zone' if zone_pref=='both' else zone_pref.title()+' Goa'}",
        index=idx, base_index=base, band=band, dimensions=dims,
        headline=f"{days}-day route covering {len(covered)}/{len(interests)} interests — {band.label}",
        findings=findings, manpower=manpower, resources=resources, recommendations=recs,
        risks=risks, gates_fired=fired,
        extra={"itinerary": day_plan, "interests": interests, "pace": pace,
               "season": season, "transfers": switches, "stops": len(picked)},
        params={"days": days, "zone": zone_pref, "interests": interests,
                "month": month, "pace": pace}, as_of=S.AS_OF)


# ===========================================================================
# 3. LOCAL BUSINESS DISCOVERY
# ===========================================================================
_BUSINESS_DIMS = [
    engine.Dim("supply_adequacy", "Supply Adequacy vs Demand", 0.30),
    engine.Dim("quality_standard", "Quality & Rating Standard", 0.25),
    engine.Dim("local_participation", "Local / Community Participation", 0.25),
    engine.Dim("formalization", "Formalisation (licensed share)", 0.20),
]
_CATEGORY_LABEL = {
    "beach_shack": "Beach shacks", "local_cuisine": "Local cuisine / restaurants",
    "water_sports": "Water sports", "homestay": "Homestays",
    "guided_tours": "Guided tours", "ayurveda_wellness": "Ayurveda & wellness",
    "handicraft": "Handicraft & markets", "eco_stay": "Eco-stays",
}


def analyze_business(params: dict) -> engine.Result:
    district = params.get("district") or "North Goa"
    category = (params.get("category") or "homestay").lower()
    biz = db.businesses(district=district, category=category)
    demand = S.CATEGORY_DEMAND.get(category, 60)
    n = len(biz)

    expected_min = max(2, round(demand / 15))      # demand-implied minimum operators
    supply_adequacy = engine.clamp(100 * n / expected_min)
    avg_rating = round(sum(b["rating"] for b in biz) / n, 2) if n else 0.0
    quality_standard = engine.clamp(avg_rating / 5 * 100)
    local_share = (sum(b["local_owned"] for b in biz) / n) if n else 0.0
    local_participation = engine.clamp(local_share * 100)
    reg_share = (sum(b["registered"] for b in biz) / n) if n else 0.0
    formalization = engine.clamp(reg_share * 100)

    dims = [
        engine.DimScore("supply_adequacy", _BUSINESS_DIMS[0].name, 0.30, supply_adequacy,
                        f"{n} listed {_CATEGORY_LABEL.get(category, category)} operator(s) in "
                        f"{district} vs demand index {demand}/100 "
                        f"(target ≥{expected_min})."),
        engine.DimScore("quality_standard", _BUSINESS_DIMS[1].name, 0.25, quality_standard,
                        f"Average rating {avg_rating}/5 across listed operators."),
        engine.DimScore("local_participation", _BUSINESS_DIMS[2].name, 0.25, local_participation,
                        f"{int(local_share*100)}% are locally / community owned."),
        engine.DimScore("formalization", _BUSINESS_DIMS[3].name, 0.20, formalization,
                        f"{int(reg_share*100)}% are formally registered / licensed."),
    ]
    base = engine.weighted_index(dims)
    gates = [
        (n > 0 and reg_share < 0.4, engine.Gate(
            "informality_gate",
            f"Only {int(reg_share*100)}% of listed {_CATEGORY_LABEL.get(category, category)} "
            f"operators are registered — informality means revenue leakage, weak safety/"
            f"consumer standards and no data for planning.",
            55, "Run a registration & licensing drive (single-window + QR listing) and tie "
                "benefits/placement to compliance.")),
    ]
    idx, fired = engine.apply_gates(base, gates)
    band = engine.band_for(idx)

    gap = max(0, expected_min - n)
    manpower = [
        {"role": "Tourism-Dept Business Facilitators", "basis": "single-window support",
         "recommended": max(2, math.ceil(expected_min / 3)),
         "note": "Licensing, grievance & scheme linkage"},
        {"role": "Skilling / Quality Trainers", "basis": "hospitality & safety training",
         "recommended": max(1, math.ceil(n / 4) + gap),
         "note": "Service, hygiene & multilingual standards"},
        {"role": "Inspectors (safety/standards)", "basis": "periodic audit",
         "recommended": max(1, math.ceil(n / 6)),
         "note": "Fire/food/water-sport safety compliance"},
    ]
    resources = [
        {"item": "Registration / Licensing Camps", "basis": "formalisation drive",
         "recommended": 2 if reg_share < 0.6 else 1, "note": "Single-window, time-bound"},
        {"item": "Skilling Seats (per cycle)", "basis": f"all {n} + {gap} new operators",
         "recommended": (n + gap) * 10, "note": "GITHM / hospitality institutes"},
        {"item": "MSME Credit / Subsidy Linkages", "basis": "per operator",
         "recommended": n + gap, "note": "Mudra/MSME & tourism-incentive schemes"},
    ]
    recs = []
    if gap:
        recs.append(f"Incentivise ~{gap} additional licensed {_CATEGORY_LABEL.get(category, category)} "
                    f"operator(s) in {district} to meet demand; prioritise local MSMEs.")
    else:
        recs.append(f"Supply of {_CATEGORY_LABEL.get(category, category)} in {district} broadly "
                    f"meets demand; focus on quality, formalisation and spreading benefits.")
    if reg_share < 0.6:
        recs.append("Launch a single-window registration & QR-listing drive to formalise operators "
                    "and capture planning data.")
    if local_share < 0.7:
        recs.append("Weight licences, placement and incentives toward Goan / community-owned "
                    "operators to retain tourism value locally.")
    recs.append("Publish a verified operator directory on the official Goa Tourism app with "
                "ratings, safety status and booking links.")

    risks = [
        {"risk": "Unlicensed operators & safety non-compliance",
         "likelihood": "H" if reg_share < 0.5 else "M", "impact": "H",
         "mitigation": "Registration drive + safety inspections"},
        {"risk": "Value leakage to non-local operators",
         "likelihood": "M" if local_share < 0.7 else "L", "impact": "M",
         "mitigation": "Local-first licensing & community equity models"},
    ]
    findings = [_finding(b["name"], f"{_CATEGORY_LABEL.get(category, category)} · {b['rating']}/5",
                         f"{'Local' if b['local_owned'] else 'Non-local'} · "
                         f"{'registered' if b['registered'] else 'UNREGISTERED'} · "
                         f"capacity ~{b['capacity']}/day", "medium") for b in biz] or \
               [_finding("No listed operators", f"{_CATEGORY_LABEL.get(category, category)} in {district}",
                         "A supply gap — a clear opportunity to develop licensed local operators.", "low")]

    return engine.Result(
        domain="business", title=DOMAINS_META["business"]["title"], icon=DOMAINS_META["business"]["icon"],
        scenario=f"{_CATEGORY_LABEL.get(category, category)} · {district}",
        index=idx, base_index=base, band=band, dimensions=dims,
        headline=f"{n} {_CATEGORY_LABEL.get(category, category)} operator(s) in {district} — {band.label}",
        findings=findings, manpower=manpower, resources=resources, recommendations=recs,
        risks=risks, gates_fired=fired,
        extra={"count": n, "avg_rating": avg_rating, "local_share": round(local_share, 2),
               "registered_share": round(reg_share, 2), "demand_index": demand,
               "supply_gap": gap, "operators": biz},
        params={"district": district, "category": category}, as_of=S.AS_OF)


# ===========================================================================
# 4. SUSTAINABLE TOURISM MONITORING
# ===========================================================================
_SUSTAIN_DIMS = [
    engine.Dim("capacity_headroom", "Carrying-Capacity Headroom", 0.35),
    engine.Dim("waste_management", "Waste Management", 0.25),
    engine.Dim("water_sewage", "Water & Sewage", 0.20),
    engine.Dim("eco_protection", "Ecological / Heritage Protection", 0.20),
]
_SENS_FACTOR = {"low": 0, "medium": 20, "high": 40}


def analyze_sustainability(params: dict) -> engine.Result:
    name = params.get("site") or "Calangute Beach"
    month = int(params.get("month") or 12)
    s = db.site(name) or db.sites()[0]
    m = db.month_demand(month)
    cd = composite_demand(m)
    season = m["season"]
    projected = round(s["peak_footfall_daily"] * cd / 100)
    cap = s["carrying_capacity_daily"]
    util = projected / cap if cap else 0
    sens = s["sensitivity"]
    sens_pen = _SENS_FACTOR[sens]

    capacity_headroom = engine.clamp(100 - max(0, util - 0.6) * 160)
    waste_management = engine.clamp(85 - util * 20 - (15 if sens == "high" else 0))
    water_sewage = engine.clamp(85 - util * 22 - (10 if sens == "high" else 0))
    eco_protection = engine.clamp(100 - sens_pen - max(0, util - 0.7) * 120)

    dims = [
        engine.DimScore("capacity_headroom", _SUSTAIN_DIMS[0].name, 0.35, capacity_headroom,
                        f"Projected ~{projected:,}/day vs carrying capacity {cap:,} "
                        f"→ {int(util*100)}% utilisation in {m['month_name']}."),
        engine.DimScore("waste_management", _SUSTAIN_DIMS[1].name, 0.25, waste_management,
                        f"Solid-waste load scales with footfall; "
                        f"{'high-sensitivity site needs reinforced segregation & lifting' if sens=='high'
                           else 'standard servicing with peak surge'}."),
        engine.DimScore("water_sewage", _SUSTAIN_DIMS[2].name, 0.20, water_sewage,
                        "Sewage/greywater and freshwater demand rise with footfall; verify STP "
                        "headroom and prevent untreated discharge to the coast."),
        engine.DimScore("eco_protection", _SUSTAIN_DIMS[3].name, 0.20, eco_protection,
                        f"Sensitivity: {sens}. {s['note']}"),
    ]
    base = engine.weighted_index(dims)
    gates = [
        (util > 1.0 and sens == "high", engine.Gate(
            "overcap_high_sens",
            f"{name} is projected at {int(util*100)}% of carrying capacity — a HIGH-sensitivity "
            f"site run over capacity threatens its ecology/heritage.",
            40, "Cap daily entries at carrying capacity via timed/booked access; enforce "
                "noise/light/vehicle limits (turtle nesting Nov–Mar where applicable).")),
        (util > 1.2, engine.Gate(
            "overcap_severe",
            f"{name} is projected well over capacity ({int(util*100)}%) — overcrowding degrades "
            f"the asset and visitor experience.",
            45, "Introduce demand-management (caps, timed entry, diversion to alternatives) and "
                "surge sanitation/sewage capacity.")),
    ]
    idx, fired = engine.apply_gates(base, gates)
    band = engine.band_for(idx)

    is_beach = s["type"] == "beach"
    manpower = [
        {"role": "Eco-Wardens / Site Marshals", "basis": "1 per 1,500/day",
         "recommended": max(4, math.ceil(projected / 1500)),
         "note": "Enforce caps, zoning & protection rules"},
        {"role": "Sanitation Crew", "basis": "1 per 800/day",
         "recommended": max(6, math.ceil(projected / 800)), "note": "Segregated collection & lifting"},
        {"role": "CCTV / Monitoring Operators", "basis": "coverage shifts",
         "recommended": 4 if sens == "high" else 2, "note": "Footfall & violation monitoring"},
    ]
    if is_beach:
        manpower.insert(1, {"role": "Lifeguards (Drishti)", "basis": "1 per 500/day",
                            "recommended": max(8, math.ceil(projected / 500)),
                            "note": "Water-safety; essential at beach sites"})
    resources = [
        {"item": "Waste Bins (segregated)", "basis": "1 per 400/day",
         "recommended": max(12, math.ceil(projected / 400)), "note": "Daily lifting"},
        {"item": "Public Toilets (units)", "basis": "1 per 800/day",
         "recommended": max(6, math.ceil(projected / 800)), "note": "With greywater handling"},
        {"item": "STP / Sewage Capacity (check)", "basis": "verify headroom",
         "recommended": 1, "note": "Audit against projected load; no coastal discharge"},
        {"item": "Entry-Regulation / Booking System", "basis": "if over capacity",
         "recommended": 1 if util > 1.0 else 0, "note": "Timed/booked access to hold the cap"},
    ]
    recs = []
    if util > 1.0:
        recs.append(f"Cap {name} at its carrying capacity (~{cap:,}/day) using timed/booked entry; "
                    f"current projection is ~{projected:,}/day ({int(util*100)}%).")
    else:
        recs.append(f"{name} is within carrying capacity ({int(util*100)}%); sustain monitoring and "
                    f"keep servicing ahead of footfall.")
    recs.append(f"Deploy ~{engine.total_headcount(manpower):,} eco-wardens, sanitation and "
                f"monitoring staff and reinforce segregated-waste infrastructure.")
    if sens == "high":
        recs.append("Enforce ecological protections: night-light/noise limits, vehicle & plastic "
                    "bans, and a seasonal protection protocol (e.g. turtle nesting Nov–Mar).")
    recs.append("Publish a live carrying-capacity / crowd dashboard and link it to the visitor app "
                "to self-regulate demand.")

    risks = [
        {"risk": "Irreversible ecological/heritage degradation",
         "likelihood": "H" if (util > 1.0 and sens == "high") else "M", "impact": "H",
         "mitigation": "Hard caps, protection rules, restoration budget"},
        {"risk": "Untreated sewage / plastic reaching the coast",
         "likelihood": "M", "impact": "H", "mitigation": "STP audit, plastic ban, segregation"},
        {"risk": "Crowding degrades visitor experience & brand",
         "likelihood": "H" if util > 1.1 else "M", "impact": "M",
         "mitigation": "Demand diversion to alternatives, timed entry"},
    ]
    findings = [
        _finding(f"{name} carrying capacity", f"{cap:,}/day (sensitivity: {sens})", s["note"], "low"),
        _finding("Projected footfall", f"~{projected:,}/day in {m['month_name']} "
                 f"({int(util*100)}% of capacity)",
                 "Scaled from the month's demand index against the site's observed peak footfall.", "low"),
    ]

    return engine.Result(
        domain="sustainability", title=DOMAINS_META["sustainability"]["title"],
        icon=DOMAINS_META["sustainability"]["icon"],
        scenario=f"{name} · {m['month_name']} ({SEASON_LABEL[season]})",
        index=idx, base_index=base, band=band, dimensions=dims,
        headline=f"{name}: {int(util*100)}% of carrying capacity in {m['month_name']} — {band.label}",
        findings=findings, manpower=manpower, resources=resources, recommendations=recs,
        risks=risks, gates_fired=fired,
        extra={"site": name, "sensitivity": sens, "carrying_capacity": cap,
               "projected_footfall": projected, "utilisation_pct": round(util * 100, 1),
               "season": season, "type": s["type"]},
        params={"site": name, "month": month}, as_of=S.AS_OF)


# ===========================================================================
# 5. EVENT / FESTIVAL COORDINATION
# ===========================================================================
_EVENT_DIMS = [
    engine.Dim("crowd_safety", "Crowd-Safety Readiness", 0.30),
    engine.Dim("logistics_capacity", "Transport / Logistics Capacity", 0.25),
    engine.Dim("emergency_medical", "Emergency / Medical / Fire", 0.25),
    engine.Dim("sanitation_resources", "Sanitation Resources", 0.20),
]


def analyze_events(params: dict) -> engine.Result:
    month = int(params.get("month") or 12)
    m = db.month_demand(month)
    fests = db.festivals(month)
    majors = [f for f in fests if f["scale"] == "major"]
    n_major = len(majors)
    peak_single = max((f["crowd_est"] for f in fests), default=0)
    total_crowd = sum(f["crowd_est"] for f in fests)
    load = peak_single  # plan to the single largest event; concurrency adds overhead

    crowd_safety = engine.clamp(100 - peak_single / 3000 - max(0, n_major - 1) * 12)
    logistics_capacity = engine.clamp(100 - total_crowd / 6000 - max(0, n_major - 1) * 10)
    emergency_medical = engine.clamp(100 - peak_single / 3500 - max(0, n_major - 1) * 10)
    sanitation_resources = engine.clamp(100 - peak_single / 3200 - max(0, n_major - 1) * 8)

    dims = [
        engine.DimScore("crowd_safety", _EVENT_DIMS[0].name, 0.30, crowd_safety,
                        f"Largest event ~{peak_single:,}; {n_major} major event(s) this month — "
                        f"{'concurrent mega-events demand a unified command' if n_major>1
                           else 'single-event focus manageable with planning'}."),
        engine.DimScore("logistics_capacity", _EVENT_DIMS[1].name, 0.25, logistics_capacity,
                        f"Combined festival footfall ~{total_crowd:,}; transport, parking and "
                        f"diversions {'severely stretched' if logistics_capacity<50 else 'need surge planning'}."),
        engine.DimScore("emergency_medical", _EVENT_DIMS[2].name, 0.25, emergency_medical,
                        "Medical posts, ambulances and fire-safety must scale to the peak-event "
                        "crowd and venue density."),
        engine.DimScore("sanitation_resources", _EVENT_DIMS[3].name, 0.20, sanitation_resources,
                        "High-density crowds need portable toilets and intensive litter servicing."),
    ]
    base = engine.weighted_index(dims)
    gates = [
        (n_major >= 3 and crowd_safety < 50, engine.Gate(
            "concurrency_gate",
            f"{n_major} major events coincide in {m['month_name']} with low crowd-safety headroom "
            f"— a serious concurrent-load risk (traffic, policing, medical).",
            45, "Stand up a unified inter-agency command (Police, Tourism, Health, Fire, "
                "Transport, local bodies) with a shared calendar and surge rosters.")),
        (peak_single >= 150000, engine.Gate(
            "mega_event_gate",
            f"A mega-event (~{peak_single:,}) is scheduled — crowd loads at this scale exceed "
            f"routine arrangements.",
            50, "Activate a dedicated mega-event SOP: phased entry, hard crowd caps at venues, "
                "medical/fire NOCs, and real-time monitoring.")),
    ]
    idx, fired = engine.apply_gates(base, gates)
    band = engine.band_for(idx)

    manpower = engine.plan_manpower(load, event=True)
    resources = engine.plan_resources(load, event=True)

    recs = [
        f"Convene a unified event-coordination command for {m['month_name']} covering "
        f"{len(fests)} event(s) ({n_major} major); publish a shared calendar and surge rosters.",
        f"Deploy ~{engine.total_headcount(manpower):,} coordination personnel (police, marshals, "
        f"medical, fire, traffic, sanitation) sized to the ~{peak_single:,}-crowd peak event.",
    ]
    names = {f["name"] for f in fests}
    if any("Sunburn" in x for x in names):
        recs.append("Sunburn: enforce drug-interdiction, noise norms, dedicated medical/ambulance "
                    "cover and traffic diversions around the North-Goa venue.")
    if any("Sao Joao" in x for x in names):
        recs.append("Sao Joao: prioritise water-safety (well/river) and alcohol-related-harm "
                    "prevention with lifeguards and patrols.")
    if any("Francis Xavier" in x for x in names):
        recs.append("St Francis Xavier feast (Old Goa): phased pilgrim flow, heritage-site crowd "
                    "caps, sanitation and medical posts along the novena route.")
    if any("Carnival" in x for x in names) or any("Shigmo" in x for x in names):
        recs.append("Parade events: barricaded float routes, spectator zoning, and traffic "
                    "diversions in Panaji/Margao/Vasco/Mapusa.")

    risks = [
        {"risk": "Crowd crush / stampede at a peak venue", "likelihood": "M",
         "impact": "H", "mitigation": "Phased entry, caps, barricading, marshals, CCTV"},
        {"risk": "Traffic gridlock across concurrent events",
         "likelihood": "H" if n_major > 1 else "M", "impact": "M",
         "mitigation": "Park-and-ride, diversions, shared calendar"},
        {"risk": "Medical/fire emergency outstripping on-site capacity",
         "likelihood": "M", "impact": "H", "mitigation": "On-site posts, ambulances, fire NOCs"},
    ]
    findings = [_finding(f["name"], f"~{f['crowd_est']:,} peak · {f['scale']} · {f['type']}",
                         f"{f['district']} · {f['duration_days']} day(s) · {f['note']}", "medium")
                for f in fests] or \
               [_finding("No major festivals", m["month_name"],
                         "A quieter month — a window for maintenance, training and off-season "
                         "product development.", "medium")]

    return engine.Result(
        domain="events", title=DOMAINS_META["events"]["title"], icon=DOMAINS_META["events"]["icon"],
        scenario=f"{m['month_name']} — {len(fests)} event(s), {n_major} major",
        index=idx, base_index=base, band=band, dimensions=dims,
        headline=f"{m['month_name']}: {n_major} major event(s), peak ~{peak_single:,} — {band.label}",
        findings=findings, manpower=manpower, resources=resources, recommendations=recs,
        risks=risks, gates_fired=fired,
        extra={"events": fests, "n_major": n_major, "peak_single": peak_single,
               "total_crowd": total_crowd,
               "total_recommended_headcount": engine.total_headcount(manpower)},
        params={"month": month}, as_of=S.AS_OF)


# ===========================================================================
# Domain registry + metadata
# ===========================================================================
_MONTH_OPTS = [{"value": m["month"], "label": m["month_name"]} for m in S.MONTHLY_DEMAND]
_SITE_OPTS = [{"value": s["name"], "label": s["name"]} for s in S.SITES]
_CATEGORY_OPTS = [{"value": k, "label": v} for k, v in _CATEGORY_LABEL.items()]
_INTEREST_OPTS = ["beach", "heritage", "nature", "nightlife", "wellness",
                  "adventure", "family", "culture", "food", "eco", "shopping"]

DOMAINS_META = {
    "seasonal": {"title": "Seasonal Demand Planning", "icon": "📈"},
    "itinerary": {"title": "Itinerary & Route Recommendation", "icon": "🗺️"},
    "business": {"title": "Local Business Discovery", "icon": "🏪"},
    "sustainability": {"title": "Sustainable Tourism Monitoring", "icon": "🌿"},
    "events": {"title": "Event & Festival Coordination", "icon": "🎉"},
}

DOMAINS: dict[str, Domain] = {
    "seasonal": Domain(
        "seasonal", DOMAINS_META["seasonal"]["title"], DOMAINS_META["seasonal"]["icon"],
        "Project month-by-month demand and the manpower, accommodation and infrastructure "
        "needed to absorb it sustainably.", _SEASONAL_DIMS,
        [{"name": "month", "label": "Month", "type": "select", "options": _MONTH_OPTS, "default": 12},
         {"name": "zone", "label": "Zone", "type": "select",
          "options": [{"value": "both", "label": "Statewide"},
                      {"value": "north", "label": "North Goa"},
                      {"value": "south", "label": "South Goa"}], "default": "both"}],
        analyze_seasonal,
        subagents=[
            {"name": "demand_analyst", "focus": "demand & accommodation",
             "dims": ["demand_absorption", "revenue_distribution"],
             "desc": "Projects arrivals, occupancy and geographic spread for the month."},
            {"name": "capacity_analyst", "focus": "manpower & infrastructure",
             "dims": ["manpower_adequacy", "infrastructure_load", "resilience"],
             "desc": "Assesses safety/service manpower and transport/sanitation headroom."},
        ]),
    "itinerary": Domain(
        "itinerary", DOMAINS_META["itinerary"]["title"], DOMAINS_META["itinerary"]["icon"],
        "Build an interest-matched, low-carbon day-by-day route that avoids over-capacity "
        "hotspots and spreads visitors across Goa.", _ITIN_DIMS,
        [{"name": "days", "label": "Days", "type": "number", "default": 3, "min": 1, "max": 14},
         {"name": "zone", "label": "Preferred area", "type": "select",
          "options": [{"value": "both", "label": "Anywhere"},
                      {"value": "north", "label": "North Goa"},
                      {"value": "south", "label": "South Goa"}], "default": "both"},
         {"name": "month", "label": "Month of travel", "type": "select", "options": _MONTH_OPTS, "default": 12},
         {"name": "pace", "label": "Pace", "type": "select",
          "options": [{"value": "relaxed", "label": "Relaxed (2/day)"},
                      {"value": "balanced", "label": "Balanced (3/day)"},
                      {"value": "packed", "label": "Packed (4/day)"}], "default": "balanced"},
         {"name": "interests", "label": "Interests", "type": "multiselect",
          "options": _INTEREST_OPTS, "default": ["beach", "heritage", "nature"]}],
        analyze_itinerary,
        subagents=[
            {"name": "route_planner", "focus": "routing & efficiency",
             "dims": ["travel_efficiency", "seasonal_suitability"],
             "desc": "Sequences and clusters stops to minimise transfers and fit the season."},
            {"name": "experience_curator", "focus": "interests & sustainability",
             "dims": ["experience_coverage", "sustainability_fit"],
             "desc": "Matches stops to interests and avoids over-capacity hotspots."},
        ]),
    "business": Domain(
        "business", DOMAINS_META["business"]["title"], DOMAINS_META["business"]["icon"],
        "Discover local operators by district & category, score the ecosystem (supply, "
        "quality, local share, formalisation) and plan MSME support.", _BUSINESS_DIMS,
        [{"name": "district", "label": "District", "type": "select",
          "options": [{"value": "North Goa", "label": "North Goa"},
                      {"value": "South Goa", "label": "South Goa"}], "default": "North Goa"},
         {"name": "category", "label": "Category", "type": "select",
          "options": _CATEGORY_OPTS, "default": "homestay"}],
        analyze_business,
        subagents=[
            {"name": "market_scout", "focus": "supply & demand",
             "dims": ["supply_adequacy", "quality_standard"],
             "desc": "Discovers operators and scores supply adequacy and quality."},
            {"name": "inclusion_analyst", "focus": "local share & formalisation",
             "dims": ["local_participation", "formalization"],
             "desc": "Assesses community ownership and licensing/formalisation."},
        ]),
    "sustainability": Domain(
        "sustainability", DOMAINS_META["sustainability"]["title"], DOMAINS_META["sustainability"]["icon"],
        "Monitor a site against its carrying capacity for a given month and plan the "
        "protection, sanitation and demand-management it needs.", _SUSTAIN_DIMS,
        [{"name": "site", "label": "Site", "type": "select", "options": _SITE_OPTS,
          "default": "Calangute Beach"},
         {"name": "month", "label": "Month", "type": "select", "options": _MONTH_OPTS, "default": 12}],
        analyze_sustainability,
        subagents=[
            {"name": "capacity_monitor", "focus": "carrying capacity",
             "dims": ["capacity_headroom", "eco_protection"],
             "desc": "Computes utilisation vs carrying capacity and ecological risk."},
            {"name": "environment_analyst", "focus": "waste & water",
             "dims": ["waste_management", "water_sewage"],
             "desc": "Assesses waste, sewage and freshwater stress."},
        ]),
    "events": Domain(
        "events", DOMAINS_META["events"]["title"], DOMAINS_META["events"]["icon"],
        "Coordinate the month's festivals & events — crowd safety, logistics, medical/fire "
        "and sanitation — with sized inter-agency deployment.", _EVENT_DIMS,
        [{"name": "month", "label": "Month", "type": "select", "options": _MONTH_OPTS, "default": 12}],
        analyze_events,
        subagents=[
            {"name": "crowd_safety_lead", "focus": "crowd safety & medical",
             "dims": ["crowd_safety", "emergency_medical"],
             "desc": "Plans crowd-safety, medical and fire readiness for peak events."},
            {"name": "logistics_lead", "focus": "logistics & sanitation",
             "dims": ["logistics_capacity", "sanitation_resources"],
             "desc": "Plans transport, parking and sanitation for the event load."},
        ]),
}


def analyze(domain_key: str, params: dict) -> dict:
    """Public entry point used by the GUI/CLI: returns a result dict."""
    d = DOMAINS[domain_key]
    return d.analyze(params or {}).to_dict()


def rubric(domain_key: str) -> dict:
    d = DOMAINS[domain_key]
    return {"key": d.key, "title": d.title, "icon": d.icon, "blurb": d.blurb,
            "inputs": d.inputs,
            "dimensions": [{"key": x.key, "name": x.name, "weight": x.weight} for x in d.dims],
            "subagents": d.subagents}
