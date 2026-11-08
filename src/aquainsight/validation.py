"""Diagnostics are separate from retained source and normalized records."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class Dataset:
    original: pd.DataFrame
    observations: pd.DataFrame
    rejected: pd.DataFrame
    quality: dict
    metadata: dict


def coordinate_pair(lat: object, lon: object) -> tuple[float | None, float | None, str]:
    try:
        a, b = float(lat), float(lon)
        if -90 <= a <= 90 and -180 <= b <= 180:
            return a, b, ""
    except (ValueError, TypeError):
        pass
    if not str(lat).strip() and not str(lon).strip():
        return None, None, ""
    return None, None, "Invalid or incomplete coordinate pair; map excluded"
