"""UE5 → clean Python dict normalization helpers."""
import re
from typing import Any


def resolve_ref(value: Any) -> str | None:
    """{ ObjectName, ObjectPath } → asset_id string, or None if not a ref."""
    if isinstance(value, dict) and "ObjectName" in value and "ObjectPath" in value:
        return value["ObjectName"].split("'")[0]
    return None


def resolve_tag(value: Any) -> str | None:
    """{ TagName: 'X.Y.Z' } → 'X.Y.Z', or None if not a tag."""
    if isinstance(value, dict) and "TagName" in value:
        return value["TagName"]
    return None


def resolve_text(value: Any) -> str | None:
    """{ LocalizedString: '...' } → display string, or None if not a text."""
    if isinstance(value, dict) and "LocalizedString" in value:
        return value["LocalizedString"]
    return None


def camel_to_snake(key: str) -> str:
    """'MoveSpeedBase' → 'move_speed_base'"""
    s1 = re.sub(r"([A-Z])([A-Z][a-z])", r"\1_\2", key)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    s3 = re.sub(r"([A-Z])([A-Z])", r"\1_\2", s2)
    return s3.lower()


def clean_flags(flags: str | None) -> list[str]:
    """'RF_Public | RF_Standalone' → ['Public', 'Standalone']"""
    if not flags:
        return []
    parts = [p.strip() for p in flags.split("|")]
    return [p.removeprefix("RF_") for p in parts if p]


def flatten(value: Any) -> Any:
    """Recursively resolve UE5 nested structs to clean Python values."""
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return [flatten(item) for item in value]

    if isinstance(value, dict):
        # Try known UE5 patterns first (most specific to least)
        ref = resolve_ref(value)
        if ref is not None:
            return ref

        tag = resolve_tag(value)
        if tag is not None:
            return tag

        text = resolve_text(value)
        if text is not None:
            return text

        # Generic nested struct: recurse with snake_case keys
        return {camel_to_snake(k): flatten(v) for k, v in value.items()}

    return value
