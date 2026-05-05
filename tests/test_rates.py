import pandas as pd
import pytest

from src.rates import KEY, _safe_rate, aggregate_to_region, build_indicator_table


def test_safe_rate_basic():
    num = pd.Series([10, 20, 0])
    den = pd.Series([100, 50, 1000])
    out = _safe_rate(num, den, 1000)
    assert list(out) == [100.0, 400.0, 0.0]


def test_safe_rate_zero_denominator_is_na():
    num = pd.Series([10, 5])
    den = pd.Series([0, 100])
    out = _safe_rate(num, den, 1000)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == 50.0


def _df_uf_fixture() -> pd.DataFrame:
    return pd.DataFrame([
        {"ano": 2020, "uf_code": 35, "uf_sigla": "SP", "regiao": "Sudeste",
         "int_menor_1": 100, "int_1a4": 200, "int_menor_5": 300,
         "obt_menor_1": 10, "obt_1a4": 5, "obt_menor_5": 15,
         "nv": 50_000, "pop_menor_1": 50_000, "pop_1a4": 200_000, "pop_menor_5": 250_000},
        {"ano": 2020, "uf_code": 33, "uf_sigla": "RJ", "regiao": "Sudeste",
         "int_menor_1": 50, "int_1a4": 100, "int_menor_5": 150,
         "obt_menor_1": 5, "obt_1a4": 3, "obt_menor_5": 8,
         "nv": 25_000, "pop_menor_1": 25_000, "pop_1a4": 100_000, "pop_menor_5": 125_000},
        {"ano": 2020, "uf_code": 29, "uf_sigla": "BA", "regiao": "Nordeste",
         "int_menor_1": 80, "int_1a4": 160, "int_menor_5": 240,
         "obt_menor_1": 8, "obt_1a4": 4, "obt_menor_5": 12,
         "nv": 40_000, "pop_menor_1": 40_000, "pop_1a4": 160_000, "pop_menor_5": 200_000},
    ])


def test_aggregate_to_region_sums_counts_and_appends_brasil():
    df_uf = _df_uf_fixture()
    out = aggregate_to_region(df_uf)

    sudeste = out[(out["regiao"] == "Sudeste") & (out["ano"] == 2020)].iloc[0]
    assert sudeste["int_menor_1"] == 150
    assert sudeste["nv"] == 75_000

    brasil = out[(out["regiao"] == "Brasil") & (out["ano"] == 2020)].iloc[0]
    assert brasil["int_menor_1"] == 230
    assert brasil["nv"] == 115_000


def test_aggregate_to_region_recomputes_rates_from_summed_counts():
    df_uf = _df_uf_fixture()
    out = aggregate_to_region(df_uf)

    sudeste = out[(out["regiao"] == "Sudeste") & (out["ano"] == 2020)].iloc[0]
    # 150 / 75_000 * 1000 = 2.0
    assert sudeste["taxa_int_menor_1_por_1000NV"] == pytest.approx(2.0)
    # (300+150) / (250_000+125_000) * 100_000 = 120.0
    assert sudeste["taxa_int_menor_5_por_100k"] == pytest.approx(120.0)


def test_aggregate_to_region_u5mr_per_1000_live_births():
    df_uf = _df_uf_fixture()
    out = aggregate_to_region(df_uf)

    sudeste = out[(out["regiao"] == "Sudeste") & (out["ano"] == 2020)].iloc[0]
    # (15+8) / (50_000+25_000) * 1000 = 23/75 = 0.3066...
    assert sudeste["taxa_obt_menor_5_por_1000NV"] == pytest.approx(23 / 75)

    brasil = out[(out["regiao"] == "Brasil") & (out["ano"] == 2020)].iloc[0]
    # (15+8+12) / (50_000+25_000+40_000) * 1000 = 35/115
    assert brasil["taxa_obt_menor_5_por_1000NV"] == pytest.approx(35_000 / 115_000)


def test_aggregate_to_region_zero_denominator_yields_na():
    df_uf = _df_uf_fixture()
    df_uf.loc[:, "nv"] = 0
    out = aggregate_to_region(df_uf)
    assert out["taxa_int_menor_1_por_1000NV"].isna().all()


def test_build_indicator_table_handles_missing_pop_without_corrupting_keys():
    sih = pd.DataFrame([
        {"ano": 2020, "uf_code": 35, "uf_sigla": "SP", "regiao": "Sudeste",
         "faixa": "menor_1_ano", "internacoes": 100},
        {"ano": 2020, "uf_code": 35, "uf_sigla": "SP", "regiao": "Sudeste",
         "faixa": "1_a_4_anos", "internacoes": 200},
    ])
    sim = pd.DataFrame([
        {"ano": 2020, "uf_code": 35, "uf_sigla": "SP", "regiao": "Sudeste",
         "faixa": "menor_1_ano", "obitos": 10},
    ])
    sinasc = pd.DataFrame([
        {"ano": 2020, "uf_code": 35, "uf_sigla": "SP", "regiao": "Sudeste",
         "nascidos_vivos": 50_000},
    ])
    pop = pd.DataFrame([
        {"ano": 2020, "uf_code": 35, "faixa": "menor_1_ano", "populacao": 50_000},
        {"ano": 2020, "uf_code": 35, "faixa": "1_a_4_anos", "populacao": 200_000},
    ])

    df = build_indicator_table(sih, sim, sinasc, pop)
    assert len(df) == 1
    row = df.iloc[0]
    for col in KEY:
        assert row[col] not in (0, "0")
    assert row["uf_sigla"] == "SP"
    assert row["regiao"] == "Sudeste"
    assert row["taxa_int_menor_1_por_1000NV"] == pytest.approx(2.0)
