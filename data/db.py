"""
db.py  —  builds and queries the Goa tourism SQLite database from the curated seed.

The database (goa_tourism.db) is a REPRODUCIBLE local store. It is (re)built
deterministically from data/seed_data.py, so deleting the file and rebuilding always
yields the same state. Query helpers return plain dicts/lists so the deterministic
analyzers (domains.py) and the LangChain evidence tools (tools.py) consume them
identically — whether the figures came from here or were refreshed from the web.

Build:   python -m data.db            (rebuilds and prints a summary)
Use:     from data import db; db.ensure(); rows = db.sites(zone="north")
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from . import seed_data as S

DB_PATH = Path(__file__).resolve().parent / "goa_tourism.db"

_SCHEMA = """
DROP TABLE IF EXISTS districts;
DROP TABLE IF EXISTS monthly_demand;
DROP TABLE IF EXISTS sites;
DROP TABLE IF EXISTS attractions;
DROP TABLE IF EXISTS businesses;
DROP TABLE IF EXISTS festivals;

CREATE TABLE districts(
    name TEXT PRIMARY KEY, zone TEXT, hq TEXT, note TEXT);

CREATE TABLE monthly_demand(
    month INTEGER PRIMARY KEY, month_name TEXT, season TEXT,
    domestic_idx INTEGER, foreign_idx INTEGER, occupancy_pct INTEGER, note TEXT);

CREATE TABLE sites(
    name TEXT PRIMARY KEY, district TEXT, zone TEXT, type TEXT,
    carrying_capacity_daily INTEGER, peak_footfall_daily INTEGER,
    sensitivity TEXT, note TEXT);

CREATE TABLE attractions(
    name TEXT PRIMARY KEY, zone TEXT, type TEXT, duration_hr INTEGER,
    best_season TEXT, tags TEXT);

CREATE TABLE businesses(
    name TEXT PRIMARY KEY, district TEXT, category TEXT, rating REAL,
    price_band INTEGER, capacity INTEGER, local_owned INTEGER, registered INTEGER);

CREATE TABLE festivals(
    name TEXT PRIMARY KEY, month INTEGER, district TEXT, zone TEXT, scale TEXT,
    duration_days INTEGER, type TEXT, crowd_est INTEGER, note TEXT);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def build(force: bool = True) -> str:
    """(Re)build the database from the seed. Returns a one-line summary."""
    conn = connect()
    try:
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO districts VALUES(:name,:zone,:hq,:note)", S.DISTRICTS)
        conn.executemany(
            "INSERT INTO monthly_demand VALUES("
            ":month,:month_name,:season,:domestic_idx,:foreign_idx,:occupancy_pct,:note)",
            S.MONTHLY_DEMAND)
        conn.executemany(
            "INSERT INTO sites VALUES("
            ":name,:district,:zone,:type,:carrying_capacity_daily,"
            ":peak_footfall_daily,:sensitivity,:note)", S.SITES)
        conn.executemany(
            "INSERT INTO attractions VALUES("
            ":name,:zone,:type,:duration_hr,:best_season,:tags)", S.ATTRACTIONS)
        conn.executemany(
            "INSERT INTO businesses VALUES("
            ":name,:district,:category,:rating,:price_band,:capacity,"
            ":local_owned,:registered)", S.BUSINESSES)
        conn.executemany(
            "INSERT INTO festivals VALUES("
            ":name,:month,:district,:zone,:scale,:duration_days,:type,"
            ":crowd_est,:note)", S.FESTIVALS)
        conn.commit()
        n = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("districts", "monthly_demand", "sites", "attractions",
                       "businesses", "festivals")}
    finally:
        conn.close()
    return (f"Built {DB_PATH.name}: " +
            ", ".join(f"{k}={v}" for k, v in n.items()))


def ensure() -> None:
    """Build the DB if it does not yet exist."""
    if not DB_PATH.exists() or os.path.getsize(DB_PATH) == 0:
        build()


# ---------------------------------------------------------------------------
# Query helpers (return plain dicts / lists of dicts)
# ---------------------------------------------------------------------------
def _rows(sql: str, params: tuple = ()) -> list[dict]:
    ensure()
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def month_demand(month: int) -> dict | None:
    r = _rows("SELECT * FROM monthly_demand WHERE month=?", (int(month),))
    return r[0] if r else None


def all_months() -> list[dict]:
    return _rows("SELECT * FROM monthly_demand ORDER BY month")


def districts() -> list[dict]:
    return _rows("SELECT * FROM districts")


def sites(zone: str | None = None, type: str | None = None,
          sensitivity: str | None = None) -> list[dict]:
    sql, p = "SELECT * FROM sites WHERE 1=1", []
    if zone:
        sql += " AND zone=?"; p.append(zone)
    if type:
        sql += " AND type=?"; p.append(type)
    if sensitivity:
        sql += " AND sensitivity=?"; p.append(sensitivity)
    return _rows(sql + " ORDER BY peak_footfall_daily DESC", tuple(p))


def site(name: str) -> dict | None:
    r = _rows("SELECT * FROM sites WHERE name=?", (name,))
    return r[0] if r else None


def attractions(zone: str | None = None, season: str | None = None) -> list[dict]:
    sql, p = "SELECT * FROM attractions WHERE 1=1", []
    if zone:
        sql += " AND zone=?"; p.append(zone)
    return _rows(sql + " ORDER BY name", tuple(p))


def businesses(district: str | None = None, category: str | None = None) -> list[dict]:
    sql, p = "SELECT * FROM businesses WHERE 1=1", []
    if district:
        sql += " AND district=?"; p.append(district)
    if category:
        sql += " AND category=?"; p.append(category)
    return _rows(sql + " ORDER BY rating DESC", tuple(p))


def festivals(month: int | None = None) -> list[dict]:
    if month is None:
        return _rows("SELECT * FROM festivals ORDER BY month")
    return _rows("SELECT * FROM festivals WHERE month=? ORDER BY crowd_est DESC",
                 (int(month),))


if __name__ == "__main__":
    print(build())
    print("AS_OF:", S.AS_OF)
