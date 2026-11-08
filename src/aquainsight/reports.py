"""Portable, escaped exports built only from the selected records."""

import json
from html import escape

import pandas as pd

from aquainsight import DEMO_WARNING, DISCLAIMER
from aquainsight.analytics import site_coverage, summary


def csv_bytes(df: pd.DataFrame) -> bytes:
    out = df.copy()
    if "data_mode" in out and out.data_mode.eq("SYNTHETIC DEMO").any():
        out["data_notice"] = DEMO_WARNING
    if out.empty and df.attrs.get("data_mode") == "SYNTHETIC DEMO":
        out[DEMO_WARNING] = pd.Series(dtype=str)
    # Neutralize spreadsheet formulas in untrusted textual cells without modifying stored data.
    for col in out.select_dtypes(include=["object", "string"]).columns:
        out[col] = out[col].map(
            lambda x: (
                "'" + x
                if isinstance(x, str) and x.startswith(("=", "+", "-", "@", "\t", "\r"))
                else x
            )
        )
    return out.to_csv(index=False).encode("utf-8-sig")


def quality_json(dataset) -> str:
    return json.dumps(
        {
            "metadata": dataset.metadata,
            "quality": dataset.quality,
            "data_modes": sorted(dataset.observations.data_mode.unique().tolist()),
            "notice": DEMO_WARNING
            if dataset.observations.attrs.get("data_mode") == "SYNTHETIC DEMO"
            else f"{dataset.observations.attrs.get('data_mode', 'USER-UPLOADED')} historical observations",
        },
        indent=2,
        default=str,
        ensure_ascii=False,
    )


def monitoring_report(
    df: pd.DataFrame, flags: pd.DataFrame, filters: dict, metadata: dict, reference_class: int
) -> str:
    notice = (
        DEMO_WARNING
        if df.attrs.get("data_mode") == "SYNTHETIC DEMO"
        or metadata.get("data_mode") == "SYNTHETIC DEMO"
        else f"{metadata.get('data_mode', 'USER-UPLOADED')} historical observations"
    )
    stats = summary(df)
    sources = df[["source_name", "source_url", "source_file"]].drop_duplicates()
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>AquaInsight monitoring summary</title>
<style>body{{font:15px system-ui;max-width:1100px;margin:40px auto;color:#183c45;padding:20px}}table{{border-collapse:collapse;font-size:12px;display:block;overflow:auto}}td,th{{padding:8px;border:1px solid #dae4e7}}.notice{{padding:16px;background:#fff0d5}}</style>
<h1>AquaInsight Jakarta · Monitoring summary</h1><p class="notice">{escape(notice)}</p><p>{DISCLAIMER}</p>
<p>Selected reference Class {reference_class}; no legal designation is implied.</p>
<h2>Active filters</h2><pre>{escape(json.dumps(filters, indent=2, default=str))}</pre>
<h2>Coverage</h2><pre>{escape(json.dumps(stats, indent=2, default=str))}</pre>{site_coverage(df).to_html(index=False)}
<h2>Reference outcomes</h2>{flags.reference_status.value_counts().to_frame("observations").to_html()}
<h2>Provenance</h2>{sources.to_html(index=False)}<pre>{escape(json.dumps(metadata, indent=2, default=str))}</pre>
<h2>Selected observations and flags ({len(flags)})</h2>{flags.to_html(index=False)}
<h2>Interpretation limits</h2><p>Historical discrete samples, no continuous monitoring, causal attribution or prediction. Month-only observations retain sampling month without an invented day; first/latest months are separate from exact dates. Missing time information is excluded from time charts. Missing units, unknown chemical bases, missing and censored readings are not numerically compared. Duplicates are retained. Coverage percentages describe supplied records, not an expected sampling schedule. Selected reference class is exploratory. pH exception applicability must be confirmed.</p></html>"""
