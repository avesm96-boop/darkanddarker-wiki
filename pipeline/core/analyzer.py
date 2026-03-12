"""Derived field calculators and analysis note helpers."""


def dps(damage: float, speed: float) -> float:
    """Compute DPS = damage / attack_interval. speed=0 → 0.0."""
    if speed == 0:
        return 0.0
    return round(damage / speed, 4)


def drop_rate_pct(weight: float, total: float) -> float:
    """Compute drop rate as percentage. total=0 → 0.0."""
    if total == 0:
        return 0.0
    return round((weight / total) * 100, 4)


def speed_at_base(multiplier: float, base: float = 300) -> float:
    """Compute effective speed = base * multiplier."""
    return round(base * multiplier, 4)


def add_notes(data: dict, notes: list[str]) -> dict:
    """Inject or append to _analysis_notes list in data. Returns data."""
    existing = data.get("_analysis_notes", [])
    data["_analysis_notes"] = existing + list(notes)
    return data


def add_formula(data: dict, name: str, expression: str,
                confidence: str, caveats: list[str]) -> dict:
    """Inject or append a formula entry into _formulas list. Returns data."""
    entry = {
        "name": name,
        "expression": expression,
        "confidence": confidence,
        "caveats": list(caveats),
    }
    data.setdefault("_formulas", []).append(entry)
    return data
