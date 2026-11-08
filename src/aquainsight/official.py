"""Adapters verified against the locally supplied Jakarta 2022/2023 CSV exports.

Keep years separate: shared identifiers do not establish method/site equivalence.
Month precision is preserved without inventing day-of-month or sample IDs.
"""

from hashlib import sha256
from pathlib import Path

import pandas as pd

from aquainsight.ingestion import normalize, read_file
from aquainsight.validation import Dataset

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
OFFICIAL_SCHEMA_VERSION = "2"
FILES = {
    2023: "Filedata Data Kualitas Air Sungai Tahun 2023.csv",
    2022: "Filedata Data Kualitas Air Sungai 2022.csv",
}
URLS = {
    2023: "https://data.go.id/dataset/dataset/data-kualitas-air-sungai-tahun-2023",
    2022: "https://data.go.id/dataset/dataset/data-kualitas-air-sungai-2022",
}
REQUIRED = {
    2023: {
        "titik_sampel",
        "lintang_selatan",
        "bujur_timur",
        "jenis_parameter",
        "parameter",
        "baku_mutu",
        "hasil_pengukuran",
        "periode_data",
        "periode_pemantauan",
        "bulan_sampling",
        "nama_sungai",
        "alamat",
    },
    2022: {
        "periode_data",
        "tahun",
        "periode",
        "bulan_sampling",
        "titik_sampel",
        "sungai",
        "alamat",
        "lintang",
        "bujur",
        "jenis_parameter",
        "parameter",
        "satuan",
        "baku_mutu",
        "hasil_pengukuran",
    },
}
PARAMETERS_2022 = {
    "Zat Padat Terlarut  TDS": "TDS",
    "Zat Padat Tersuspensi  TSS": "TSS",
    "COD  dichromat": "COD",
    "Kadmium  Cd": "Cd",
    "Seng  Zn": "Zn",
    "Tembaga  Cu": "Cu",
    "Timah Hitam  Pb": "Pb",
    "Crom Hexavalen  Cr6": "Cr6+",
}


def available_official_files(raw_dir: Path = RAW_DIR) -> dict[int, Path]:
    return {year: raw_dir / name for year, name in FILES.items() if (raw_dir / name).is_file()}


def identify_official_schema(frame: pd.DataFrame) -> int | None:
    columns = {str(c).lstrip("\ufeff") for c in frame.columns}
    return next((year for year, required in REQUIRED.items() if required.issubset(columns)), None)


def normalize_official(frame: pd.DataFrame, year: int, metadata: dict) -> Dataset:
    raw = frame.copy(deep=True)
    raw.columns = [str(c).lstrip("\ufeff") for c in raw.columns]
    missing = REQUIRED[year] - set(raw.columns)
    if missing:
        raise ValueError(f"Jakarta {year} schema missing columns: {sorted(missing)}")
    prepared = raw.fillna("").astype(str)
    prepared["source_row"] = range(2, len(raw) + 2)
    prepared["parameter"] = prepared.parameter.str.strip()
    excluded = prepared.parameter.isin(
        ["", "-"]
    ) | prepared.jenis_parameter.str.strip().str.lower().isin(["nilai ip", "status ip"])
    rejected = prepared.loc[excluded].copy()
    rejected["reason"] = (
        rejected.jenis_parameter.str.strip()
        .map(
            {
                "nilai IP": "Derived pollution-index summary, not a parameter measurement",
                "status IP": "Derived pollution-status summary, not a parameter measurement",
            }
        )
        .fillna("Missing parameter identity")
    )
    for field in ["source_name", "source_file", "source_url", "data_mode"]:
        rejected[field] = metadata.get(field, "")
    prepared = prepared.loc[~excluded].copy()
    month_raw = prepared.bulan_sampling.str.strip()
    month = month_raw.str[-2:] if year == 2022 else month_raw.str.zfill(2)
    year_raw = prepared.periode_data.str.strip()
    valid_month = month.str.fullmatch(r"0[1-9]|1[0-2]") & year_raw.eq(str(year))
    if year == 2022:
        valid_month &= month_raw.str.fullmatch(r"\d{6}") & month_raw.str[:4].eq(year_raw)
    if not valid_month.all():
        raise ValueError(
            "Sampling month/year is invalid or disagrees with the selected dataset year."
        )
    prepared["sample_month"] = year_raw + "-" + month
    prepared["sample_date_precision"] = "month"
    prepared["monitoring_period"] = (
        prepared["periode"] if year == 2022 else prepared["periode_pemantauan"]
    )
    prepared["address"] = prepared.alamat
    prepared["parameter_group"] = prepared.jenis_parameter
    prepared["source_reference_raw"] = prepared.baku_mutu
    lat, lon = ("lintang", "bujur") if year == 2022 else ("lintang_selatan", "bujur_timur")
    prepared["latitude_raw"], prepared["longitude_raw"] = prepared[lat], prepared[lon]
    prepared["_latitude"] = pd.to_numeric(
        prepared[lat].str.replace(",", ".", regex=False), errors="coerce"
    )
    prepared["_longitude"] = pd.to_numeric(
        prepared[lon].str.replace(",", ".", regex=False), errors="coerce"
    )
    prepared["_unit"] = ""
    prepared["unit_basis_note"] = (
        "2023 source has no unit column; concentration units and chemical bases are unverified."
    )
    if year == 2022:
        prepared["_unit"] = (
            prepared.satuan.str.strip()
            .str.lower()
            .map({"mg l": "mg/L", "mpn 100 ml": "MPN/100 mL", "pt-co unit": "Pt-Co Unit", "-": ""})
            .fillna(prepared.satuan.str.strip())
        )
        prepared["unit_basis_note"] = (
            "2022 unit column normalized explicitly; nitrate chemical basis is unspecified."
        )
    # pH is intrinsically dimensionless; its original source unit remains blank or '-'.
    prepared.loc[prepared.parameter.eq("pH"), "_unit"] = "pH"
    prepared.loc[prepared.parameter.eq("pH"), "unit_basis_note"] = (
        "pH is intrinsically dimensionless; source unit field preserved without inferring a concentration unit."
    )
    mapping = {
        "site_id": "titik_sampel",
        "site_name": "alamat",
        "river_name": "sungai" if year == 2022 else "nama_sungai",
        "parameter_original_name": "parameter",
        "value_raw": "hasil_pengukuran",
        "unit_original": "_unit",
        "latitude": "_latitude",
        "longitude": "_longitude",
    }
    result = normalize(prepared, metadata, mapping=mapping, decimal="," if year == 2022 else ".")
    obs = result.observations
    # The source adapter owns these fields. Align by original source row because
    # summary/invalid-identity rows may have been excluded during normalization.
    source_rows = prepared.set_index("source_row").loc[obs["source_row"].astype(int)]
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
        obs[field] = source_rows[field].to_numpy()
    obs["import_row"] = obs.source_row
    if year == 2022:
        obs["parameter_code"] = obs.parameter_original_name.map(
            lambda name: PARAMETERS_2022.get(name, name)
        )
        obs["unit_original"] = (
            raw.iloc[obs.source_row.astype(int).to_numpy() - 2].satuan.astype(str).to_numpy()
        )
    else:
        obs["unit_original"] = ""
    obs["sample_date_raw"] = (
        raw.iloc[obs.source_row.astype(int).to_numpy() - 2].bulan_sampling.astype(str).to_numpy()
    )
    obs["date_issue"] = "Sampling month supplied; exact day unavailable"
    obs["quality_note"] = (
        obs.quality_note.str.replace(
            "Missing date", "Sampling month supplied; exact day unavailable", regex=False
        )
        + "; "
        + obs["unit_basis_note"]
    )
    obs["duplicate_candidate"] = obs.duplicated(
        [
            "source_id",
            "site_id",
            "sample_month",
            "monitoring_period",
            "parameter_code",
            "value_raw",
            "unit_normalized",
        ],
        keep=False,
    )
    pairs = obs[["site_id", "latitude", "longitude"]].drop_duplicates()
    conflicting = pairs.groupby("site_id").size().loc[lambda counts: counts > 1].index.tolist()
    shared = (
        pairs.groupby(["latitude", "longitude"])
        .site_id.nunique()
        .loc[lambda counts: counts > 1]
        .index
    )
    shared_sites = (
        pairs.set_index(["latitude", "longitude"])
        .loc[pairs.set_index(["latitude", "longitude"]).index.isin(shared), "site_id"]
        .unique()
        .tolist()
    )
    excluded_sites = sorted(set(conflicting) | set(shared_sites))
    obs.loc[obs.site_id.isin(excluded_sites), "coordinates_verified"] = False
    result.original = raw
    result.rejected = rejected
    result.quality.update(
        source_rows=len(raw),
        expanded_observations=len(raw),
        retained_observations=len(obs),
        rejected_observations=len(rejected),
        excluded_summary_rows=int(
            raw.jenis_parameter.str.strip().str.lower().isin(["nilai ip", "status ip"]).sum()
        ),
        missing_parameter_rows=int(excluded.sum())
        - int(raw.jenis_parameter.str.strip().str.lower().isin(["nilai ip", "status ip"]).sum()),
        month_precision_observations=len(obs),
        unavailable_exact_dates=len(obs),
        missing_dates=0,
        date_parsing_failures=0,
        duplicate_candidates=int(obs.duplicate_candidate.sum()),
        conflicting_coordinate_sites=conflicting,
        shared_coordinate_sites=sorted(shared_sites),
        map_excluded_sites=excluded_sites,
        missing_units=int(obs.unit_normalized.eq("").sum()),
        policy="All identified parameter readings retained, including invalid/missing readings. Derived index/status rows and rows without parameter identity excluded with diagnostics. Duplicate candidates retained.",
    )
    result.metadata.update(
        date_precision="month; no exact sampling dates supplied",
        sampling_months=sorted(obs.sample_month.unique()),
        excluded_rows="Derived pollution index/status and missing-parameter rows retained in rejected diagnostics",
        cross_year_comparability="Not established: years are loaded separately; methods and station equivalence unverified",
        coordinate_policy="Coordinates supplied in source and checked for numeric ranges, site consistency and shared pairs; conflicting/shared sites omitted",
        unit_policy="2022 source units normalized; 2023 units absent, except intrinsically dimensionless pH. No inferred nitrate-as-N basis.",
    )
    return result


def load_official(path: Path, year: int) -> Dataset:
    content = path.read_bytes()
    metadata = {
        "source_id": f"jakarta-river-{year}",
        "source_name": f"Data Kualitas Air Sungai {year} · Provinsi DKI Jakarta",
        "source_url": URLS[year],
        "source_file": path.name,
        "data_mode": "OFFICIAL",
        "coordinates_verified": True,
        "license": "Catalog marked open; specific redistribution license not verified. Raw files remain gitignored.",
        "access_date": "2026-11-08",
        "retrieval_method": "Downloaded by user from the official Jakarta catalog; inspected locally",
        "sha256": sha256(content).hexdigest(),
    }
    return normalize_official(read_file(content, path.name), year, metadata)
