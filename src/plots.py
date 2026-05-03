"""Generate PNG charts for the gastroenterite report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .geo import REGIOES

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

REGION_COLORS = {
    "Norte":        "#1f77b4",
    "Nordeste":     "#ff7f0e",
    "Sudeste":      "#2ca02c",
    "Sul":          "#d62728",
    "Centro-Oeste": "#9467bd",
    "Brasil":       "#000000",
}


def _line_by_region(df: pd.DataFrame, value: str, title: str, ylabel: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for reg in REGIOES + ["Brasil"]:
        sub = df[df["regiao"] == reg].sort_values("ano")
        if sub.empty:
            continue
        lw = 2.5 if reg == "Brasil" else 1.5
        ls = "--" if reg == "Brasil" else "-"
        ax.plot(sub["ano"], sub[value], label=reg,
                color=REGION_COLORS[reg], linewidth=lw, linestyle=ls, marker="o", markersize=4)
    ax.set_title(title)
    ax.set_xlabel("Ano")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", frameon=False, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def _bar_uf_latest(df_uf: pd.DataFrame, value: str, title: str, ylabel: str, out: Path) -> None:
    last_year = int(df_uf["ano"].max())
    sub = df_uf[df_uf["ano"] == last_year].sort_values(value, ascending=False)
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = [REGION_COLORS[r] for r in sub["regiao"]]
    ax.bar(sub["uf_sigla"], sub[value], color=colors)
    ax.set_title(f"{title} - {last_year}")
    ax.set_xlabel("UF")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


CHARTS = [
    ("taxa_int_menor_1_por_1000NV",
     "Internações por gastroenterite (CID A09) - menores de 1 ano",
     "Internações por 1.000 nascidos vivos"),
    ("taxa_obt_menor_1_por_1000NV",
     "Óbitos por gastroenterite (CID A09) - menores de 1 ano",
     "Óbitos por 1.000 nascidos vivos"),
    ("taxa_int_1a4_por_100k",
     "Internações por gastroenterite (CID A09) - 1 a 4 anos",
     "Internações por 100.000 hab."),
    ("taxa_obt_1a4_por_100k",
     "Óbitos por gastroenterite (CID A09) - 1 a 4 anos",
     "Óbitos por 100.000 hab."),
    ("taxa_int_menor_5_por_100k",
     "Internações por gastroenterite (CID A09) - menores de 5 anos",
     "Internações por 100.000 hab."),
    ("taxa_obt_menor_5_por_100k",
     "Óbitos por gastroenterite (CID A09) - menores de 5 anos",
     "Óbitos por 100.000 hab."),
]


def render_all(df_uf: pd.DataFrame, df_regiao: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for col, title, ylab in CHARTS:
        p1 = out_dir / f"linha_regiao_{col}.png"
        _line_by_region(df_regiao, col, title, ylab, p1)
        paths.append(p1)
        p2 = out_dir / f"barras_uf_{col}.png"
        _bar_uf_latest(df_uf, col, title, ylab, p2)
        paths.append(p2)
    return paths
