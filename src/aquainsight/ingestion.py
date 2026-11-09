"""CSV/XLSX reading and explicit long/wide normalization."""

from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd

from aquainsight.cleaning import normalize_unit, parse_date, parse_number, text
from aquainsight.mappings import parameter_code, suggest_mapping
from aquainsight.validation import Dataset, coordinate_pair


def read_file(
    content: bytes,
    filename: str,
    sheet: str | int = 0,
    encoding: str = "utf-8-sig",
    delimiter: str | None = None,
) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        return pd.read_excel(
            BytesIO(content), sheet_name=sheet, dtype=object, keep_default_na=False
        )
    if suffix != ".csv":
        raise ValueError("Choose a .csv or .xlsx file.")
    try:
        decoded = content.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValueError("Encoding failed. Choose UTF-8, CP1252 or Latin-1.") from exc
    frame = pd.read_csv(
        StringIO(decoded), sep=delimiter, engine="python", dtype=str, keep_default_na=False
    )
    frame.columns = [str(column).lstrip("\ufeff") for column in frame.columns]
    return frame


def excel_sheets(content: bytes) -> list[str]:
    return pd.ExcelFile(BytesIO(content), engine="openpyxl").sheet_names


def normalize(
    frame: pd.DataFrame,
    metadata: dict,
    mapping: dict[str, str] | None = None,
    wide: dict[str, tuple[str, str]] | None = None,
    decimal: str = "auto",
    date_order: str = "auto",
) -> Dataset:
    mode = metadata.get("data_mode", "USER-UPLOADED")
    if mode not in {"OFFICIAL", "USER-UPLOADED"}:
        raise ValueError("Unsupported data mode. Import genuine historical observations.")
    if "data_mode" in frame:
        declared = {text(value) for value in frame["data_mode"]} - {""}
        if not declared.issubset({"OFFICIAL", "USER-UPLOADED"}):
            raise ValueError(
                "Unsupported data mode in file. Import genuine historical observations."
            )
    mapping = suggest_mapping(list(frame.columns)) if mapping is None else mapping
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Each source column can map to only one canonical field.")
    required = [] if wide else ["parameter_original_name", "value_raw"]
    missing = [c for c in required if c not in mapping]
    if missing:
        raise ValueError(
            "Missing mappings: " + ", ".join(missing) + ". Map columns or select wide format."
        )
    if not {"site_id", "site_name"}.intersection(mapping):
        raise ValueError("Map at least site_id or site_name to identify monitoring locations.")
    records, rejected = [], []
    for index, (_, row) in enumerate(frame.iterrows(), start=2):
        base = {target: row[source] for target, source in mapping.items()}
        items = [
            (
                base.get("parameter_original_name", ""),
                base.get("value_raw", ""),
                base.get("unit_original", ""),
            )
        ]
        if wide:
            items = [(name, row[col], unit) for col, (name, unit) in wide.items()]
        for name, raw, unit in items:
            record = dict(base)
            record.update(
                parameter_original_name=text(name),
                value_raw=text(raw),
                unit_original=text(unit),
                source_row=index,
            )
            site_id = text(base.get("site_id", "")) or text(base.get("site_name", ""))
            if not site_id or not text(name):
                rejected.append(
                    {
                        **record,
                        "reason": "Missing site identity or parameter",
                        "source_file": metadata.get("source_file", ""),
                        "source_name": metadata.get("source_name", ""),
                        "source_url": metadata.get("source_url", ""),
                        "data_mode": mode,
                        "data_notice": "Historical observation; source provenance retained",
                    }
                )
                continue
            value, qualifier, note = parse_number(raw, decimal)
            # Preserve explicit qualifiers when re-importing canonical exports.
            explicit = text(base.get("qualifier", ""))
            if explicit and explicit != "exact":
                qualifier, value, note = (
                    explicit,
                    None,
                    "Source qualifier prevents exact comparison",
                )
            source_date = base.get("sample_date", "")
            if mapping.get("sample_date") == "sample_date" and "sample_date_raw" in row.index:
                source_date = row["sample_date_raw"]
            stamp, date_note = parse_date(source_date, date_order)
            lat, lon, coord_note = coordinate_pair(
                base.get("latitude", ""), base.get("longitude", "")
            )
            record.update(
                source_id=metadata.get("source_id", metadata.get("source_file", "upload")),
                source_name=metadata.get("source_name", "User upload"),
                source_url=metadata.get("source_url", ""),
                source_file=metadata.get("source_file", ""),
                data_mode=mode,
                data_notice="Official historical observations; locally supplied catalog export"
                if mode == "OFFICIAL"
                else "Historical observations; user-supplied provenance",
                site_id=site_id,
                site_name=text(base.get("site_name", "")),
                river_name=text(base.get("river_name", "")),
                sample_id=text(base.get("sample_id", "")),
                sample_date_raw=text(source_date),
                sample_date=stamp,
                latitude=lat,
                longitude=lon,
                parameter_code=parameter_code(text(name)),
                value_numeric=value,
                unit_normalized=normalize_unit(unit),
                qualifier=qualifier,
                quality_note="; ".join(
                    x
                    for x in [
                        note,
                        date_note,
                        coord_note,
                        "Missing site name" if not text(base.get("site_name", "")) else "",
                    ]
                    if x
                ),
                date_issue=date_note,
                coordinate_issue=coord_note,
                coordinates_verified=bool(metadata.get("coordinates_verified", False)),
            )
            # Canonical re-imports retain original lineage as well as the new import file.
            for field in ["source_id", "source_name", "source_url", "source_file"]:
                if text(row.get(field, "")):
                    record[field] = text(row[field])
            record["import_file"] = metadata.get("source_file", "")
            record["import_row"] = index
            for field in [
                "sample_month",
                "sample_date_precision",
                "monitoring_period",
                "address",
                "parameter_group",
                "source_reference_raw",
                "unit_basis_note",
                "latitude_raw",
                "longitude_raw",
            ]:
                record[field] = text(row.get(field, ""))
            if text(row.get("source_row", "")):
                record["source_row"] = row["source_row"]
            records.append(record)
    columns = [
        "source_id",
        "source_name",
        "source_url",
        "source_file",
        "source_row",
        "data_mode",
        "data_notice",
        "site_id",
        "site_name",
        "river_name",
        "sample_id",
        "sample_date_raw",
        "sample_date",
        "latitude",
        "longitude",
        "parameter_code",
        "parameter_original_name",
        "value_raw",
        "value_numeric",
        "unit_original",
        "unit_normalized",
        "qualifier",
        "quality_note",
        "date_issue",
        "coordinate_issue",
        "coordinates_verified",
    ]
    obs = pd.DataFrame(
        records,
        columns=[
            *columns,
            "import_file",
            "import_row",
            "sample_month",
            "sample_date_precision",
            "monitoring_period",
            "address",
            "parameter_group",
            "source_reference_raw",
            "unit_basis_note",
            "latitude_raw",
            "longitude_raw",
        ],
    )
    obs.attrs["data_mode"] = mode
    obs["sample_date"] = pd.to_datetime(obs["sample_date"])
    obs["value_numeric"] = pd.to_numeric(obs["value_numeric"], errors="coerce")
    keys = [
        "source_id",
        "site_id",
        "sample_date_raw",
        "sample_month",
        "sample_id",
        "parameter_code",
        "value_raw",
        "unit_normalized",
    ]
    obs["duplicate_candidate"] = obs.duplicated(keys, keep=False)
    quality = {
        "source_rows": len(frame),
        "expanded_observations": len(records) + len(rejected),
        "retained_observations": len(obs),
        "rejected_observations": len(rejected),
        "missing_readings": int((obs.qualifier == "missing").sum()),
        "censored_readings": int((obs.qualifier == "censored").sum()),
        "invalid_or_ambiguous_readings": int(obs.qualifier.isin(["invalid", "ambiguous"]).sum()),
        "missing_dates": int((obs.date_issue == "Missing date").sum()),
        "date_parsing_failures": int(
            (obs.date_issue.ne("") & obs.date_issue.ne("Missing date")).sum()
        ),
        "duplicate_candidates": int(obs.duplicate_candidate.sum()),
        "invalid_coordinates": int(obs.coordinate_issue.ne("").sum()),
        "missing_site_names": int(obs.site_name.eq("").sum()),
        "missing_units": int(obs.unit_normalized.eq("").sum()),
        "source_coverage": obs.groupby("source_name").size().to_dict(),
        "unusual_units": sorted(
            set(obs.unit_normalized)
            - {"mg/L", "µg/L", "pH", "dimensionless", "MPN/100 mL", "Pt-Co Unit", ""}
        ),
        "policy": "All identified observations retained, including missing/invalid readings. Duplicate candidates are retained. Rejections lack site identity or parameter.",
    }
    return Dataset(frame.copy(deep=True), obs, pd.DataFrame(rejected), quality, dict(metadata))


def empty_observations() -> pd.DataFrame:
    """A typed zero-row canonical frame for the upload screen before data is loaded."""
    return normalize(
        pd.DataFrame(columns=["site_id", "parameter", "value"]),
        {"data_mode": "USER-UPLOADED"},
    ).observations
