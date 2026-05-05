"""End-to-end pipeline: download DATASUS, build indicators, write Excel + charts.

Usage:
    python extract.py                       # default 10-year window auto-detected
    python extract.py --start 2014 --end 2023
    python extract.py --skip-download       # use cached DBC files only
    python extract.py --sample              # generate output from sample_data/
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import END_YEAR, GRAPHS_DIR, OUTPUT_DIR, SAMPLE_DIR, START_YEAR
from src.excel_report import write_excel
from src.plots import render_all
from src.population import aggregate_by_age_group, extract_population
from src.rates import aggregate_to_region, build_indicator_table
from src.sih import extract_sih
from src.sim import extract_sim
from src.sinasc import extract_sinasc

log = logging.getLogger("gastroenterite")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, default=START_YEAR)
    p.add_argument("--end", type=int, default=END_YEAR)
    p.add_argument("--sim-end", type=int, default=None,
                   help="Last year for SIM/SINASC (default: end - 1, due to publication lag).")
    p.add_argument("--force", action="store_true", help="Re-download even if cached.")
    p.add_argument("--sample", action="store_true",
                   help="Skip downloads, load from sample_data/*.csv (offline demo).")
    p.add_argument("--verbose", "-v", action="count", default=0)
    return p.parse_args()


def _setup_logging(verbosity: int) -> None:
    level = logging.WARNING if verbosity == 0 else (logging.INFO if verbosity == 1 else logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _load_sample() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    log.warning("Loading SAMPLE data (no DATASUS access).")
    sih = pd.read_csv(SAMPLE_DIR / "sih.csv")
    sim = pd.read_csv(SAMPLE_DIR / "sim.csv")
    sinasc = pd.read_csv(SAMPLE_DIR / "sinasc.csv")
    pop = pd.read_csv(SAMPLE_DIR / "populacao.csv")
    return sih, sim, sinasc, pop


def main() -> int:
    args = _parse_args()
    _setup_logging(args.verbose)

    sih_years = list(range(args.start, args.end + 1))
    sim_end = args.sim_end if args.sim_end is not None else args.end - 1
    sim_years = list(range(args.start, sim_end + 1))

    if args.sample:
        sih, sim, sinasc, pop = _load_sample()
    else:
        log.warning("Extracting SIH for years %s", sih_years)
        sih = extract_sih(sih_years, force=args.force)
        log.warning("Extracting SIM for years %s", sim_years)
        sim = extract_sim(sim_years, force=args.force)
        log.warning("Extracting SINASC for years %s", sim_years)
        sinasc = extract_sinasc(sim_years, force=args.force)
        log.warning("Extracting IBGE population estimates")
        pop_raw = extract_population(sih_years)
        pop = aggregate_by_age_group(pop_raw)

    if any(d.empty for d in (sih, sim, sinasc, pop)):
        log.error("One or more sources returned empty: SIH=%d, SIM=%d, SINASC=%d, POP=%d",
                  len(sih), len(sim), len(sinasc), len(pop))
        return 1

    df_uf = build_indicator_table(sih, sim, sinasc, pop)
    df_regiao = aggregate_to_region(df_uf)

    out_xlsx = OUTPUT_DIR / "gastroenterite_A09_menores_5_anos.xlsx"
    metadata = {
        "Indicador": "Gastroenterite (CID-10 A09)",
        "Faixas etárias": "<1 ano; 1-4 anos; <5 anos (total)",
        "Fontes - numerador": "SIH-SUS (internações), SIM (óbitos)",
        "Fontes - denominador": "SINASC (NV) e Projeção da População IBGE (Tabela 7358)",
        "Local": "UF e Região de residência",
        "Período SIH": f"{args.start}-{args.end}",
        "Período SIM/SINASC": f"{args.start}-{sim_end}",
        "Taxas <1 ano": "por 1.000 nascidos vivos (= IMR, comparável a WHO/UN-IGME)",
        "Taxas 1-4 e <5 anos": "por 100.000 hab. da faixa (framing GBD, causa-específica)",
        "Taxa <5 anos adicional": "óbitos por 1.000 NV (framing WHO/U5MR, causa-específica)",
        "Comparabilidade internacional": (
            "IMR (<1 ano por 1000 NV) alinhado a WHO/UN-IGME. "
            "Causa-específica (CID A09) por 100k hab. alinhada a GBD. "
            "U5MR aqui é aproximação crude (óbitos<5 / NV mesmo ano), "
            "não a probabilidade sintética q(5) da UN-IGME."
        ),
        "Janela temporal": (
            f"{args.start}-{args.end} (25 anos). Floor metodológico = 1996 "
            "(adoção da CID-10 no Brasil). Janela cobre rollout do "
            "rotavírus no PNI (mar/2006), expansão do Bolsa Família e "
            "disrupção COVID."
        ),
        "Caveat - cobertura SIM": (
            "A cobertura do SIM melhorou substancialmente no período, "
            "principalmente nas regiões Norte e Nordeste. Quedas reais "
            "de mortalidade nos primeiros anos podem estar parcialmente "
            "compensadas por melhor registro. Ver fatores de correção "
            "publicados pelo Ministério da Saúde para análise de "
            "tendência rigorosa."
        ),
        "Caveat - projeções IBGE": (
            "Denominadores populacionais usam IBGE Tabela 7358 "
            "(Projeção da População), revisada após o Censo 2022. "
            "Snapshots anteriores da mesma tabela podem diferir para "
            "anos 2000-2010."
        ),
        "Gerado em": datetime.now().isoformat(timespec="seconds"),
    }

    log.warning("Writing Excel: %s", out_xlsx)
    write_excel(df_uf, df_regiao, sih, sim, sinasc, pop, metadata, out_xlsx)

    log.warning("Rendering charts to %s", GRAPHS_DIR)
    paths = render_all(df_uf, df_regiao, GRAPHS_DIR)
    log.warning("Done. %d charts written.", len(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
