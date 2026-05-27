import re
from difflib import SequenceMatcher

import pandas as pd


MIN_FUZZY_SCORE = 0.86


def map_column_roles(df: pd.DataFrame, config: dict) -> dict[str, str]:
    """Map canonical column roles to actual DataFrame column names."""
    roles = config.get("columns", {}).get("roles", {})
    if not isinstance(roles, dict):
        return {}

    normalized_columns = {
        _normalize_name(column): column
        for column in df.columns
    }

    mapped = {}
    for role, settings in roles.items():
        aliases = _role_aliases(role, settings)
        match = _find_column_match(aliases, normalized_columns)
        if match:
            mapped[role] = match

    return mapped


def _role_aliases(role: str, settings) -> list[str]:
    aliases = [role]
    if isinstance(settings, dict):
        configured = settings.get("aliases", [])
        if isinstance(configured, list):
            aliases.extend(str(alias) for alias in configured)
    return [_normalize_name(alias) for alias in aliases]


def _find_column_match(aliases: list[str], normalized_columns: dict[str, str]) -> str | None:
    for alias in aliases:
        if alias in normalized_columns:
            return normalized_columns[alias]

    best_column = None
    best_score = 0.0
    for alias in aliases:
        for normalized_column, original_column in normalized_columns.items():
            score = SequenceMatcher(None, alias, normalized_column).ratio()
            if score > best_score:
                best_score = score
                best_column = original_column

    return best_column if best_score >= MIN_FUZZY_SCORE else None


def _normalize_name(name: str) -> str:
    normalized = str(name).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return re.sub(r"_+", "_", normalized).strip("_")
