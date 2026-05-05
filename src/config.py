"""Project-wide constants for the gastroenterite (CID-10 A09) extraction."""

from __future__ import annotations

from datetime import date
from pathlib import Path

# CID-10: A09 covers "Diarreia e gastroenterite de origem infecciosa presumível".
# Sub-codes (A09.0 / A09.9) appear in SIM/SIH as A090 / A099 (4-character form).
CID10_PREFIX = "A09"

# Time window. 25-year span captures the pre-rotavirus-vaccine baseline
# (PNI rollout March/2006), Bolsa Família scale-up, and post-vaccine
# decline — the structural inflections that matter for trend analysis.
# Floor is 1996 (Brazil's CID-10 adoption); pre-1996 needs CID-9 crosswalk.
# For SIH we expect data through current year minus 1 month; for
# SIM/SINASC there is typically a 1.5-2 year publication lag, so the
# pipeline auto-detects the latest available year per source.
END_YEAR = date.today().year - 1
START_YEAR = END_YEAR - 24  # 25-year inclusive window

# Age groups of interest. Keys map to denominator strategies in src/rates.py
AGE_GROUPS = {
    "menor_1_ano": "Menor de 1 ano",
    "1_a_4_anos": "1 a 4 anos",
    "menor_5_anos": "Menor de 5 anos (total)",
}

# DATASUS FTP base (HTTPS mirror is also served from the same host).
DATASUS_BASE = "https://ftp.datasus.gov.br/dissemin/publicos"

# IBGE population estimates by age - SIDRA tables.
# Tabela 6579 (Estimativas anuais por UF) and Projecao 2018 are alternatives,
# but for under-5 single-year-of-age we use Projeção da População (Tabela 7358).
IBGE_SIDRA_BASE = "https://apisidra.ibge.gov.br/values"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data_raw"
OUTPUT_DIR = PROJECT_ROOT / "output"
GRAPHS_DIR = OUTPUT_DIR / "graphs"
SAMPLE_DIR = PROJECT_ROOT / "sample_data"

for d in (DATA_DIR, OUTPUT_DIR, GRAPHS_DIR):
    d.mkdir(parents=True, exist_ok=True)
