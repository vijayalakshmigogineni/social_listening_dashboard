"""
Editable source units (subreddits, AAPC forums, Facebook groups, LinkedIn
query families, X accounts) for dashboard-started collection jobs.

A source_settings row overrides that source's in-code default list; deleting
it restores the default. Overrides are cached in-process (OVERRIDES) and
refreshed from the DB whenever the Data Collection page lists sources or a job
starts, so an edit made through another API instance is picked up too.

Validation is strict because every unit is passed to an existing collector
(and most cost Apify credits): known value shapes only, bounded counts, no
duplicates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import SourceSetting

MAX_UNITS = 30  # per source -- every unit is one actor run per sweep


@dataclass(frozen=True)
class UnitRule:
    # What a unit's value is, shown next to the input.
    value_label: str
    value_pattern: re.Pattern
    value_hint: str
    # Reddit/X derive the display name from the value ("r/x", "@x"); the
    # others carry their own short name.
    named: bool
    name_prefix: str = ""


NAME_PATTERN = re.compile(r"^[a-z0-9_]{2,60}$")

RULES: dict[str, UnitRule] = {
    "reddit": UnitRule("Subreddit", # Older subreddits exceed the current 21-char limit (Medicalbillingandcoding).
                       re.compile(r"^[A-Za-z0-9_]{2,50}$"),
                       "subreddit name without r/, e.g. MedicalCoding", named=False, name_prefix="r/"),
    "x": UnitRule("Account", re.compile(r"^[A-Za-z0-9_]{1,15}$"),
                  "handle without @, e.g. DrBruggeman", named=False, name_prefix="@"),
    "aapc": UnitRule("Forum RSS URL", re.compile(r"^https://www\.aapc\.com/discuss/forums/[A-Za-z0-9._/-]+$"),
                     "https://www.aapc.com/discuss/forums/<forum>/index.rss", named=True),
    "facebook": UnitRule("Group URL", re.compile(r"^https://(www\.)?facebook\.com/groups/[A-Za-z0-9._-]+/?$"),
                         "https://www.facebook.com/groups/<id or slug>", named=True),
    "linkedin": UnitRule("Search query", re.compile(r"^.{3,600}$", re.S),
                         "LinkedIn post search query (OR / quotes allowed)", named=True),
}

# source -> [{"name", "value"}]; replaced wholesale, so readers never see a
# half-updated list.
OVERRIDES: dict[str, list[dict[str, str]]] = {}


class InvalidUnits(ValueError):
    pass


def units_dict(source: str, units: list[dict[str, str]]) -> dict[str, str]:
    """{display name: value} -- the shape the adapters' units() return."""
    rule = RULES[source]
    if rule.named:
        return {u["name"]: u["value"] for u in units}
    return {f"{rule.name_prefix}{u['value']}": u["value"] for u in units}


def validate(source: str, units: list[dict]) -> list[dict[str, str]]:
    """Cleaned [{"name", "value"}] or InvalidUnits with a readable reason."""
    if source not in RULES:
        raise InvalidUnits(f"source {source!r} has no editable units")
    rule = RULES[source]
    if not units:
        raise InvalidUnits("keep at least one unit (or reset to the defaults)")
    if len(units) > MAX_UNITS:
        raise InvalidUnits(f"at most {MAX_UNITS} units per source")
    cleaned: list[dict[str, str]] = []
    seen_names: set[str] = set()
    seen_values: set[str] = set()
    for i, unit in enumerate(units, start=1):
        value = str(unit.get("value") or "").strip()
        if source in ("reddit", "x"):
            value = value.removeprefix("r/").removeprefix("@")
        if not rule.value_pattern.match(value):
            raise InvalidUnits(f"row {i}: {rule.value_label.lower()} must be {rule.value_hint}")
        name = str(unit.get("name") or "").strip().lower() if rule.named else value
        if rule.named and not NAME_PATTERN.match(name):
            raise InvalidUnits(f"row {i}: name must be 2-60 lowercase letters, digits or _")
        key = value.lower()
        if key in seen_values or name in seen_names:
            raise InvalidUnits(f"row {i}: duplicate {rule.value_label.lower()} or name")
        seen_values.add(key)
        seen_names.add(name)
        cleaned.append({"name": name, "value": value})
    return cleaned


def refresh(db: Session) -> None:
    global OVERRIDES
    OVERRIDES = {row.source: list(row.units) for row in db.query(SourceSetting).all()}


def save(db: Session, source: str, units: list[dict]) -> list[dict[str, str]]:
    cleaned = validate(source, units)
    row = db.get(SourceSetting, source)
    if row is None:
        db.add(SourceSetting(source=source, units=cleaned))
    else:
        row.units = cleaned
    db.commit()
    refresh(db)
    return cleaned


def reset(db: Session, source: str) -> None:
    row = db.get(SourceSetting, source)
    if row is not None:
        db.delete(row)
        db.commit()
    refresh(db)
