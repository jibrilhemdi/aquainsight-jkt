"""Small, explicit chart summaries, always within one parameter and unit."""

import pandas as pd

PARAMETER_NAMES = {
    "BOD": "Biochemical oxygen demand",
    "COD": "Chemical oxygen demand",
    "DO": "Dissolved oxygen",
    "TSS": "Total suspended solids",
    "TDS": "Total dissolved solids",
    "pH": "Acidity / alkalinity",
}
BLOCKER_LABELS = {
    "unit_missing": "Unit absent from source",
    "unit_mismatch": "Unit cannot be matched safely",
    "chemical_basis_unknown": "Chemical basis not established",
    "rule_not_configured": "Reference rule not configured",
    "reading_unusable": "Missing or qualified reading",
    "ph_context": "pH applicability needs confirmation",
    "negative_reading": "Negative concentration",
}
STATUS_LABELS = {
    "within_reference": "Within reference",
    "outside_reference": "Outside reference",
    "not_evaluable": "Comparison unavailable",
}


def exact_readings(df: pd.DataFrame) -> pd.DataFrame:
    if df.parameter_code.nunique() > 1 or df.unit_normalized.nunique() > 1:
        raise ValueError("Choose one parameter and one unit before summarizing readings")
    return df.loc[df.qualifier.eq("exact") & df.value_numeric.notna()].copy()


def period_values(df: pd.DataFrame) -> pd.DataFrame:
    result = exact_readings(df)
    result["period_label"] = result.sample_date.dt.strftime("%Y-%m-%d").fillna("")
    monthly = result.sample_month.ne("") & result.sample_date.isna()
    result.loc[monthly, "period_label"] = result.loc[monthly, "sample_month"]
    return result.loc[result.period_label.ne("")]


def period_statistics(df: pd.DataFrame) -> pd.DataFrame:
    valid = period_values(df)
    return (
        valid.groupby("period_label", sort=True)
        .value_numeric.agg(
            n="count", median="median", q1=lambda x: x.quantile(0.25), q3=lambda x: x.quantile(0.75)
        )
        .reset_index()
    )


def group_statistics(df: pd.DataFrame, group: str = "river_name") -> pd.DataFrame:
    valid = exact_readings(df)
    result = (
        valid.groupby(group)
        .value_numeric.agg(
            n="count", median="median", q1=lambda x: x.quantile(0.25), q3=lambda x: x.quantile(0.75)
        )
        .reset_index()
    )
    return result.sort_values("median", ascending=False)


def comparison_coverage(flags: pd.DataFrame) -> dict:
    compared = flags.reference_status.isin(["within_reference", "outside_reference"])
    outside = int(flags.reference_status.eq("outside_reference").sum())
    return {
        "total": len(flags),
        "compared": int(compared.sum()),
        "unavailable": int((~compared).sum()),
        "outside": outside,
        "within": int(flags.reference_status.eq("within_reference").sum()),
        "outside_pct": 100 * outside / int(compared.sum()) if compared.any() else None,
    }


def blocker_counts(flags: pd.DataFrame) -> pd.DataFrame:
    blocked = flags.loc[flags.reference_status.eq("not_evaluable")]
    counts = (
        blocked.reference_blocker.value_counts()
        .rename_axis("blocker")
        .rename("observations")
        .reset_index()
    )
    counts["reason"] = counts.blocker.map(BLOCKER_LABELS).fillna("Other comparison gap")
    return counts
