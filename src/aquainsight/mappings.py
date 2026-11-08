"""Explicit bilingual aliases; unknown parameters retain their identity/basis."""

ALIASES = {
    "sample_id": [],
    "qualifier": [],
    "site_id": ["kode_titik", "kode_lokasi", "stasiun"],
    "site_name": ["lokasi", "nama_lokasi", "titik_pantau"],
    "river_name": ["nama_sungai", "sungai"],
    "sample_date": ["tanggal", "tanggal_sampling", "tanggal_pengambilan"],
    "parameter_original_name": ["parameter", "nama_parameter", "parameter_code"],
    "value_raw": ["nilai", "hasil", "value", "value_numeric"],
    "unit_original": ["satuan", "unit", "unit_normalized"],
    "latitude": ["lintang"],
    "longitude": ["bujur"],
}
PARAMETERS = {
    "ph": "pH",
    "derajat keasaman": "pH",
    "derajat keasaman (ph)": "pH",
    "do": "DO",
    "oksigen terlarut": "DO",
    "dissolved oxygen": "DO",
    "bod": "BOD",
    "kebutuhan oksigen biokimiawi": "BOD",
    "cod": "COD",
    "kebutuhan oksigen kimiawi": "COD",
    "tss": "TSS",
    "padatan tersuspensi total": "TSS",
    "nitrat sebagai n": "NO3-N",
    "nitrate as n": "NO3-N",
    "no3-n": "NO3-N",
    "nitrate as no3": "NO3",
    "no3": "NO3",
    "fosfat sebagai p": "PO4-P",
    "phosphate as p": "PO4-P",
}


def suggest_mapping(columns: list[str]) -> dict[str, str]:
    lookup = {str(c).strip().lower(): c for c in columns}
    result = {}
    for target, aliases in ALIASES.items():
        for alias in [target, *aliases]:
            if alias in lookup:
                result[target] = lookup[alias]
                break
    return result


def parameter_code(value: str) -> str:
    return PARAMETERS.get(value.strip().lower(), value.strip())
