"""Generate synthetic but realistic sample data to validate the pipeline offline.

Numbers are loosely calibrated against published TabNet aggregates for gastroenterite
(CID-10 A09) - they should NOT be used for analysis, only to demonstrate the
pipeline shape end-to-end without DATASUS network access.
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample_data"
SAMPLE.mkdir(parents=True, exist_ok=True)

# Mirror src.geo without importing (script-friendly)
UF = [
    ("11", "RO", "Norte"), ("12", "AC", "Norte"), ("13", "AM", "Norte"),
    ("14", "RR", "Norte"), ("15", "PA", "Norte"), ("16", "AP", "Norte"),
    ("17", "TO", "Norte"),
    ("21", "MA", "Nordeste"), ("22", "PI", "Nordeste"), ("23", "CE", "Nordeste"),
    ("24", "RN", "Nordeste"), ("25", "PB", "Nordeste"), ("26", "PE", "Nordeste"),
    ("27", "AL", "Nordeste"), ("28", "SE", "Nordeste"), ("29", "BA", "Nordeste"),
    ("31", "MG", "Sudeste"), ("32", "ES", "Sudeste"), ("33", "RJ", "Sudeste"),
    ("35", "SP", "Sudeste"),
    ("41", "PR", "Sul"), ("42", "SC", "Sul"), ("43", "RS", "Sul"),
    ("50", "MS", "Centro-Oeste"), ("51", "MT", "Centro-Oeste"),
    ("52", "GO", "Centro-Oeste"), ("53", "DF", "Centro-Oeste"),
]

# UF rough live-births baseline (2020 SINASC totals, integer thousands)
NV_BASELINE = {
    "RO": 25000,  "AC": 16000,  "AM": 70000,  "RR": 12000,
    "PA": 130000, "AP": 14000,  "TO": 24000,  "MA": 105000,
    "PI": 41000,  "CE": 110000, "RN": 40000,  "PB": 50000,
    "PE": 120000, "AL": 45000,  "SE": 28000,  "BA": 180000,
    "MG": 240000, "ES": 50000,  "RJ": 200000, "SP": 590000,
    "PR": 145000, "SC": 95000,  "RS": 130000, "MS": 42000,
    "MT": 55000,  "GO": 90000,  "DF": 45000,
}

# Roughly: hospitalization rate per 1000 NV varies by region
# Norte/Nordeste higher (~10-15/1000NV); Sul/Sudeste lower (~3-6/1000NV)
REGION_INT_BASE = {
    "Norte": 14.0, "Nordeste": 11.0, "Centro-Oeste": 7.0,
    "Sudeste": 4.5, "Sul": 3.5,
}
# Mortality per 1000 NV ~0.08-0.30 across regions
REGION_OBT_BASE = {
    "Norte": 0.30, "Nordeste": 0.25, "Centro-Oeste": 0.12,
    "Sudeste": 0.08, "Sul": 0.07,
}

START_YEAR = 2014
END_YEAR_SIH = 2024
END_YEAR_SIM = 2023  # 1-year publication lag for SIM/SINASC


def _trend(year: int, base: int) -> float:
    # Slight downward trend over the decade (~3% per year)
    return max(0.4, 1 - 0.03 * (year - START_YEAR)) * base


def build_sinasc() -> pd.DataFrame:
    rows = []
    for uf_code, sigla, regiao in UF:
        nv0 = NV_BASELINE[sigla]
        for year in range(START_YEAR, END_YEAR_SIM + 1):
            n = int(_trend(year, nv0) * random.uniform(0.95, 1.05))
            rows.append({"ano": year, "uf_code": uf_code, "uf_sigla": sigla,
                         "regiao": regiao, "nascidos_vivos": n})
    return pd.DataFrame(rows)


def build_population() -> pd.DataFrame:
    """Returns long format: ano, uf_code, faixa, populacao, uf_sigla, regiao."""
    rows = []
    for uf_code, sigla, regiao in UF:
        nv0 = NV_BASELINE[sigla]
        for year in range(START_YEAR, END_YEAR_SIH + 1):
            # Approx: pop_<1y ~ NV (1 cohort), pop_1-4 ~ 4 * NV
            pop_0 = int(_trend(year, nv0) * random.uniform(0.95, 1.0))
            pop_1_4 = int(_trend(year, nv0) * 4 * random.uniform(0.95, 1.05))
            rows.append({"ano": year, "uf_code": uf_code, "faixa": "menor_1_ano",
                         "populacao": pop_0, "uf_sigla": sigla, "regiao": regiao})
            rows.append({"ano": year, "uf_code": uf_code, "faixa": "1_a_4_anos",
                         "populacao": pop_1_4, "uf_sigla": sigla, "regiao": regiao})
    return pd.DataFrame(rows)


def build_sih(sinasc: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    rows = []
    nv_lookup = {(r.ano, r.uf_code): r.nascidos_vivos for r in sinasc.itertuples()}
    pop_lookup = {(r.ano, r.uf_code, r.faixa): r.populacao for r in pop.itertuples()}
    for uf_code, sigla, regiao in UF:
        base_int = REGION_INT_BASE[regiao]
        for year in range(START_YEAR, END_YEAR_SIH + 1):
            # Use prior-year NV as proxy for SIM-only years
            nv_year = year if year <= END_YEAR_SIM else END_YEAR_SIM
            nv = nv_lookup.get((nv_year, uf_code), 50000)
            int_m1 = int(base_int * nv / 1000 * random.uniform(0.7, 1.3))
            pop14 = pop_lookup.get((year, uf_code, "1_a_4_anos"), 50000)
            int_14 = int(base_int * 0.6 * pop14 / 1000 * random.uniform(0.7, 1.3))
            rows.append({"ano": year, "uf_code": uf_code, "uf_sigla": sigla,
                         "regiao": regiao, "faixa": "menor_1_ano", "internacoes": int_m1})
            rows.append({"ano": year, "uf_code": uf_code, "uf_sigla": sigla,
                         "regiao": regiao, "faixa": "1_a_4_anos", "internacoes": int_14})
    return pd.DataFrame(rows)


def build_sim(sinasc: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    rows = []
    nv_lookup = {(r.ano, r.uf_code): r.nascidos_vivos for r in sinasc.itertuples()}
    pop_lookup = {(r.ano, r.uf_code, r.faixa): r.populacao for r in pop.itertuples()}
    for uf_code, sigla, regiao in UF:
        base_obt = REGION_OBT_BASE[regiao]
        for year in range(START_YEAR, END_YEAR_SIM + 1):
            nv = nv_lookup.get((year, uf_code), 50000)
            obt_m1 = max(0, int(base_obt * nv / 1000 * random.uniform(0.5, 1.5)))
            pop14 = pop_lookup.get((year, uf_code, "1_a_4_anos"), 50000)
            # 1-4y mortality ~ 0.5-2 per 100,000 hab depending on region
            rate_obt_14 = base_obt * 4  # scale up to per-100k order
            obt_14 = max(0, int(rate_obt_14 * pop14 / 100_000 * random.uniform(0.5, 1.5)))
            rows.append({"ano": year, "uf_code": uf_code, "uf_sigla": sigla,
                         "regiao": regiao, "faixa": "menor_1_ano", "obitos": obt_m1})
            rows.append({"ano": year, "uf_code": uf_code, "uf_sigla": sigla,
                         "regiao": regiao, "faixa": "1_a_4_anos", "obitos": obt_14})
    return pd.DataFrame(rows)


def main() -> None:
    random.seed(20260503)
    sinasc = build_sinasc()
    pop = build_population()
    sih = build_sih(sinasc, pop)
    sim = build_sim(sinasc, pop)
    sinasc.to_csv(SAMPLE / "sinasc.csv", index=False)
    pop.to_csv(SAMPLE / "populacao.csv", index=False)
    sih.to_csv(SAMPLE / "sih.csv", index=False)
    sim.to_csv(SAMPLE / "sim.csv", index=False)
    print(f"Wrote sample data to {SAMPLE}")
    print(f"  sih: {len(sih)} rows")
    print(f"  sim: {len(sim)} rows")
    print(f"  sinasc: {len(sinasc)} rows")
    print(f"  populacao: {len(pop)} rows")


if __name__ == "__main__":
    main()
