"""Conservative scalar parsing: ambiguous values stay unevaluable."""

import re
from datetime import date, datetime

import pandas as pd

MISSING = {"", "nan", "none", "null", "na", "n/a", "-"}


def text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def parse_number(value: object, decimal: str = "auto") -> tuple[float | None, str, str]:
    raw = text(value)
    if raw.lower() in MISSING:
        return None, "missing", "Missing reading"
    if raw.upper() in {"ND", "BDL", "LOD", "TIDAK TERDETEKSI"}:
        return None, "censored", "Detection-limit code; no numeric substitution"
    if re.match(r"^(<=|>=|<|>|≤|≥|~)", raw):
        return None, "censored", "Qualified reading; no numeric substitution"
    s = raw.replace("−", "-")
    if decimal in {".", ","}:
        other = "," if decimal == "." else "."
        # Thousands groups must be well formed before removing separators.
        integer = s.split(decimal)[0]
        if other in integer and not re.fullmatch(
            r"[+-]?\d{1,3}(" + re.escape(other) + r"\d{3})+", integer
        ):
            return None, "invalid", "Malformed thousands grouping"
        s = s.replace(other, "").replace(decimal, ".")
    elif "," in s or "." in s:
        if "," in s and "." in s:
            return None, "ambiguous", "Mixed separators; select decimal convention"
        sep = "," if "," in s else "."
        if re.fullmatch(r"[+-]?\d{1,3}" + re.escape(sep) + r"\d{3}", s):
            return None, "ambiguous", "Decimal/thousands ambiguity; select convention"
        s = s.replace(",", ".")
    try:
        number = float(s)
        if not pd.notna(number) or abs(number) == float("inf"):
            raise ValueError
        return number, "exact", ""
    except (ValueError, OverflowError):
        return None, "invalid", "Unrecognized numeric reading"


def parse_date(value: object, order: str = "auto") -> tuple[pd.Timestamp, str]:
    raw = text(value)
    if not raw:
        return pd.NaT, "Missing date"
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return pd.Timestamp(value).tz_localize(None).normalize(), ""
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
    if order != "auto":
        formats += ["%d/%m/%Y", "%d-%m-%Y"] if order == "dayfirst" else ["%m/%d/%Y", "%m-%d-%Y"]
    else:
        match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
        if match:
            a, b, _ = map(int, match.groups())
            if a <= 12 and b <= 12 and a != b:
                return pd.NaT, "Ambiguous date; choose day-first or month-first"
            formats += ["%d/%m/%Y", "%d-%m-%Y"] if a > 12 else ["%m/%d/%Y", "%m-%d-%Y"]
    for fmt in formats:
        try:
            return pd.Timestamp(datetime.strptime(raw, fmt)), ""
        except ValueError:
            continue
    return pd.NaT, "Unrecognized date; use ISO YYYY-MM-DD or select date order"


def normalize_unit(value: object) -> str:
    raw = text(value)
    aliases = {
        "mg/l": "mg/L",
        "mg/liter": "mg/L",
        "µg/l": "µg/L",
        "ug/l": "µg/L",
        "μg/l": "µg/L",
        "ph": "pH",
        "-": "",
        "1": "dimensionless",
    }
    return aliases.get(raw.lower(), raw)
