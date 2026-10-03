"""
engine.py  —  the deterministic core shared by all five Goa-tourism task domains.

Design philosophy (same ethos as a transparent rules engine): the LLM agents do NOT
invent the numbers. Each domain computes a fixed set of DIMENSIONS (0-100, higher =
better-prepared / more sustainable) from the seeded database; this module turns those
into a single **Preparedness Index** (0-100) and a verdict band using an explicit,
auditable rubric, and applies hard GATES that cap the verdict regardless of the
average (e.g. a high-sensitivity site run over carrying capacity cannot score "well
prepared", however good everything else is).

It also provides the MANPOWER and RESOURCE planners — the government deliverable —
which scale deployment from projected footfall using published PLANNING NORMS kept
here in the open so a policymaker can read and change them.

Everything here is pure Python and runs with no LLM and no API key.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Verdict bands on the 0-100 Preparedness Index (higher = better prepared)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Band:
    key: str
    label: str
    lo: int
    hi: int
    color: str
    headline: str


BANDS: list[Band] = [
    Band("green", "WELL-PREPARED — sustain current plan", 75, 100, "#3fb950",
         "The destination/plan is well-prepared and sustainable for this scenario; "
         "sustain current measures and monitor."),
    Band("amber", "MANAGEABLE — act on the gaps below", 58, 74, "#d29922",
         "Broadly manageable, but specific gaps need action before the scenario "
         "peaks; deploy the recommended manpower and resources."),
    Band("orange", "STRAINED — intervene now", 42, 57, "#db8b3a",
         "The scenario will strain capacity and services; targeted intervention and "
         "surge resourcing are required now."),
    Band("red", "CRITICAL — urgent action / cap demand", 0, 41, "#e06c6c",
         "Capacity and public-interest safeguards are breached for this scenario; "
         "urgent intervention, surge resourcing and demand-management are required."),
]


def band_for(index: float) -> Band:
    for b in BANDS:
        if b.lo <= index <= b.hi:
            return b
    return BANDS[-1]


# ---------------------------------------------------------------------------
# Dimension & gate specs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Dim:
    key: str
    name: str
    weight: float


@dataclass
class DimScore:
    key: str
    name: str
    weight: float
    score: float
    rationale: str = ""


@dataclass
class Gate:
    key: str
    description: str
    ceiling: int
    action: str


@dataclass
class Result:
    domain: str
    title: str
    icon: str
    scenario: str
    index: float
    base_index: float
    band: Band
    dimensions: list[DimScore]
    headline: str = ""
    findings: list[dict] = field(default_factory=list)
    manpower: list[dict] = field(default_factory=list)
    resources: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    gates_fired: list[dict] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    as_of: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "domain": self.domain, "title": self.title, "icon": self.icon,
            "scenario": self.scenario, "params": self.params,
            "index": round(self.index, 1), "base_index": round(self.base_index, 1),
            "band": {"key": self.band.key, "label": self.band.label,
                     "color": self.band.color, "headline": self.band.headline},
            "dimensions": [{"key": d.key, "name": d.name, "weight": d.weight,
                            "score": round(d.score, 1), "rationale": d.rationale}
                           for d in self.dimensions],
            "headline": self.headline,
            "findings": self.findings, "manpower": self.manpower,
            "resources": self.resources, "recommendations": self.recommendations,
            "risks": self.risks, "gates_fired": self.gates_fired,
            "extra": self.extra, "notes": self.notes, "as_of": self.as_of,
        }


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(x)))


def weighted_index(dims: list[DimScore]) -> float:
    wsum = sum(d.weight for d in dims) or 1.0
    return sum(d.score * d.weight for d in dims) / wsum


def apply_gates(base_index: float, gates: list[tuple[bool, Gate]]) -> tuple[float, list[dict]]:
    """Return (final_index, fired_gate_dicts). Each fired gate caps the index at its
    ceiling; the lowest ceiling wins."""
    ceiling = 100.0
    fired: list[dict] = []
    for is_fired, g in gates:
        if is_fired:
            fired.append({"key": g.key, "description": g.description,
                          "ceiling": g.ceiling, "action": g.action})
            ceiling = min(ceiling, g.ceiling)
    return min(base_index, ceiling), fired


# ---------------------------------------------------------------------------
# MANPOWER & RESOURCE PLANNERS (the government deliverable)
#
# Norms are "1 staffer / resource per N projected daily visitors", with a floor.
# These are OPEN, EDITABLE planning norms for decision-support — not statutory
# ratios. Tune them to Goa Police / Drishti Marine / Directorate of Tourism doctrine.
# ---------------------------------------------------------------------------

# (role, per_n_visitors, floor_count, note)
BASE_MANPOWER_NORMS = [
    ("Tourism Police",            2000, 6,  "Visitor safety, anti-touting, FIR/assistance"),
    ("Beach Lifeguards (Drishti)", 500, 8,  "Per active beach stretch; water-safety"),
    ("Sanitation Workers",        1000, 10, "Beach/public-area cleaning & waste collection"),
    ("Traffic Wardens",           2500, 4,  "Junction & parking management"),
    ("Tourist Facilitators",      3000, 3,  "Help desks, multilingual assistance"),
    ("Medical / First-Aid Staff", 5000, 2,  "First-aid posts & ambulance crew"),
]

BASE_RESOURCE_NORMS = [
    ("Public Toilets (units)",     1000, 4,  "Serviced daily"),
    ("Waste Bins (units)",          500, 12, "With segregation & daily lifting"),
    ("Shuttle / Mini-bus (fleet)", 3000, 2,  "Park-and-ride to cut private traffic"),
    ("Parking Slots",                20, 50, "Per 20 visitors (car-equivalent)"),
    ("Ambulances",                20000, 1,  "On-call emergency response"),
    ("Drinking-water Points",      1500, 3,  "Refill stations to cut plastic"),
]

# Event-density norms (crowds pack tighter than dispersed beach tourism).
EVENT_MANPOWER_NORMS = [
    ("Police & Crowd Control",    1000, 20, "Bandobast; crowd flow & law-and-order"),
    ("Crowd Marshals / Volunteers", 500, 30, "Queue & flow management at venues"),
    ("Medical / Ambulance Crew",  4000, 6,  "On-site medical posts + ambulances"),
    ("Fire & Rescue Staff",       8000, 4,  "Fire-safety at stages/pandals/venues"),
    ("Traffic Police",            2000, 12, "Diversions, parking, VIP movement"),
    ("Sanitation Crew",            800, 20, "High-density litter & toilet servicing"),
]

EVENT_RESOURCE_NORMS = [
    ("Portable Toilets (units)",   400, 20, "High-density event servicing"),
    ("Crowd Barricades (metres)",   50, 500,"Flow control & stage separation"),
    ("Ambulances",                8000, 3,  "On-site + evacuation"),
    ("PA / Announcement Points",  5000, 6,  "Crowd communication & lost-and-found"),
    ("Shuttle / Park-and-ride (fleet)", 2500, 6, "Reduce event-day gridlock"),
    ("CCTV / Watch Towers",       6000, 8,  "Surveillance & crowd monitoring"),
]


def plan(load: float, norms: list[tuple], kind: str = "role") -> list[dict]:
    """Scale a norm table from a projected daily load (footfall or crowd estimate)."""
    key = "role" if kind == "role" else "item"
    out = []
    for name, per_n, floor, note in norms:
        rec = max(floor, math.ceil(load / per_n)) if per_n else floor
        out.append({key: name, "basis": f"1 per {per_n:,} / day (min {floor})",
                    "recommended": int(rec), "note": note})
    return out


def plan_manpower(load: float, event: bool = False) -> list[dict]:
    return plan(load, EVENT_MANPOWER_NORMS if event else BASE_MANPOWER_NORMS, "role")


def plan_resources(load: float, event: bool = False) -> list[dict]:
    return plan(load, EVENT_RESOURCE_NORMS if event else BASE_RESOURCE_NORMS, "item")


def total_headcount(manpower: list[dict]) -> int:
    return sum(int(r["recommended"]) for r in manpower)
