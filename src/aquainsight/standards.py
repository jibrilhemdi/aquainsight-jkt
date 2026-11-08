"""Inclusive reference comparisons; never substitute detection limits."""

from pathlib import Path

import pandas as pd
import yaml

CONFIG = Path(__file__).resolve().parents[2] / "config" / "standards.yaml"


def load_standards() -> dict:
    return yaml.safe_load(CONFIG.read_text())


def compare(df: pd.DataFrame, reference_class: int, ph_applicable: bool = False) -> pd.DataFrame:
    if reference_class not in (1, 2, 3, 4):
        raise ValueError("Reference class must be 1–4")
    config = load_standards()
    rows = []
    for _, row in df.iterrows():
        rule = config["rules"].get(row.parameter_code)
        status, reason, limit, kind, unit = (
            "not_evaluable",
            "No verified rule for this parameter and chemical basis",
            "",
            "",
            "",
        )
        blocker = ""
        if rule:
            limit = rule["limits"][reference_class - 1]
            kind, unit = rule["kind"], rule["unit"]
        compatible = row.unit_normalized == unit or (
            row.parameter_code == "pH" and row.unit_normalized == "dimensionless"
        )
        value = row.value_numeric
        if row.qualifier != "exact" or pd.isna(value):
            blocker, reason = (
                "reading_unusable",
                "Missing, invalid, ambiguous or qualified reading; no numeric comparison",
            )
        elif not row.unit_normalized:
            blocker, reason = (
                "unit_missing",
                "Source does not provide a measurement unit; no concentration unit is inferred",
            )
        elif not rule:
            chemical = any(
                term in row.parameter_original_name.lower()
                for term in ["nitrat", "nitrate", "fosfat", "phosphate"]
            ) or row.parameter_code in {"NO3", "Total P", "PO4-P"}
            blocker = "chemical_basis_unknown" if chemical else "rule_not_configured"
            reason = (
                "Chemical basis cannot be matched to a verified rule"
                if chemical
                else "This parameter has no rule configured in the app's verified reference subset"
            )
        elif not compatible and not (unit == "mg/L" and row.unit_normalized == "µg/L"):
            blocker, reason = "unit_mismatch", "Incompatible unit/basis; no safe comparison"
        elif row.parameter_code == "pH" and not ph_applicable:
            blocker, reason = (
                "ph_context",
                "pH applicability unconfirmed: natural peat-water exception",
            )
        elif value < 0 and row.parameter_code != "pH":
            blocker, reason = "negative_reading", "Negative concentration is not safely evaluable"
        else:
            converted = value / 1000 if row.unit_normalized == "µg/L" else value
            within = (
                (limit[0] <= converted <= limit[1])
                if kind == "range"
                else (converted >= limit if kind == "minimum" else converted <= limit)
            )
            status = "within_reference" if within else "outside_reference"
            reason = f"Inclusive {kind} comparison" + (
                "; µg/L converted to mg/L" if row.unit_normalized == "µg/L" else ""
            )
        rows.append(
            {
                "reference_class": reference_class,
                "reference_status": status,
                "reference_reason": reason,
                "reference_blocker": blocker,
                "reference_limit": str(limit),
                "reference_kind": kind,
                "reference_unit": unit,
                "reference_source": config["source_url"] if rule else "",
                "reference_entry": rule["table_entry"] if rule else "",
            }
        )
    extra = pd.DataFrame(
        rows,
        index=df.index,
        columns=[
            "reference_class",
            "reference_status",
            "reference_reason",
            "reference_blocker",
            "reference_limit",
            "reference_kind",
            "reference_unit",
            "reference_source",
            "reference_entry",
        ],
    )
    result = pd.concat([df.copy(), extra], axis=1)
    result.attrs = dict(df.attrs)
    return result
