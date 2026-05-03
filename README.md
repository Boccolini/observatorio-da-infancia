# Observatório da Infância

Indicadores epidemiológicos de saúde infantil no Brasil a partir de fontes
públicas (DATASUS, IBGE).

Primeiro indicador implementado: **internações (SIH-SUS) e óbitos (SIM) por
gastroenterite (CID-10 A09) em menores de 5 anos**, por UF e Região de
residência, com taxas calculadas e visualizações.

## Entregável

Após rodar `python extract.py`:

`output/gastroenterite_A09_menores_5_anos.xlsx` com 13 abas:

| Aba | Conteúdo |
|---|---|
| `00_Metadados` | Fonte, período, taxas, data de geração |
| `01_UF_Indicadores` | Contagens + taxas por (ano × UF) |
| `02_Regiao_Brasil` | Contagens + taxas por (ano × Região) e Brasil |
| `03_SIH_Internacoes` | SIH bruto: ano × UF × faixa etária |
| `04_SIM_Obitos` | SIM bruto: ano × UF × faixa etária |
| `05_SINASC_NV` | Nascidos vivos por (ano × UF) |
| `06_Populacao_IBGE` | População IBGE por (ano × UF × faixa) |
| `07_taxa_*` | Séries temporais (ano × Região) por indicador |

E `output/graphs/*.png` com 12 gráficos:

- 1 gráfico de linhas por região (5 regiões + Brasil) para cada um dos 6 indicadores
- 1 gráfico de barras por UF (último ano disponível) para cada um dos 6 indicadores

## Faixas etárias e taxas

| Faixa | Numerador | Denominador | Multiplicador |
|---|---|---|---|
| < 1 ano | SIH/SIM (CID A09) | Nascidos vivos (SINASC) | × 1.000 |
| 1 a 4 anos | SIH/SIM (CID A09) | População IBGE 1-4 anos | × 100.000 |
| < 5 anos (total) | soma das duas faixas | População IBGE 0-4 anos | × 100.000 |

## Fontes

- **SIH-SUS**: arquivos `RD<UF><AAMM>.dbc` em
  `https://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/`.
  Filtramos `DIAG_PRINC` começando em `A09`. Local de residência (`MUNIC_RES`).
- **SIM**: arquivos `DO<UF><AAAA>.dbc` em
  `https://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/`.
  Filtramos `CAUSABAS` começando em `A09`. Local de residência (`CODMUNRES`).
- **SINASC**: `DN<UF><AAAA>.dbc` em
  `https://ftp.datasus.gov.br/dissemin/publicos/SINASC/NOV/DNRES/`.
- **População IBGE**: SIDRA Tabela 7358 (Projeção da População 2018), idade
  simples 0-4, por UF.

Período padrão: **últimos 10 anos** (auto-detectado pela data corrente; SIM e
SINASC usam 1 ano a menos para acomodar o atraso de publicação).

## Estrutura

```
.
├── extract.py              # Entrypoint (pipeline completo)
├── requirements.txt
├── src/
│   ├── config.py           # Constantes (CID, período, paths)
│   ├── geo.py              # UF ↔ Região
│   ├── downloader.py       # HTTP retry + cache em data_raw/
│   ├── dbc_reader.py       # DBC → DataFrame
│   ├── sih.py              # Extração SIH
│   ├── sim.py              # Extração SIM
│   ├── sinasc.py           # Extração SINASC
│   ├── population.py       # IBGE SIDRA
│   ├── rates.py            # Cálculo de indicadores
│   ├── excel_report.py     # Geração do XLSX
│   └── plots.py            # Geração dos PNGs
├── scripts/
│   └── build_sample.py     # Gera dados sintéticos para validação offline
├── sample_data/            # CSVs sintéticos (não usar para análise!)
└── output_sample/          # XLSX + gráficos de exemplo (gerados com --sample)
```

## Uso

```bash
# Instalar dependências (Python 3.11 recomendado)
pip install -r requirements.txt

# Rodar com período padrão (últimos 10 anos auto-detectados)
python extract.py -v

# Rodar com período custom
python extract.py --start 2014 --end 2024 --sim-end 2023 -v

# Re-baixar arquivos mesmo se cache local existe
python extract.py --force -v

# Rodar offline com dados sintéticos (validação do pipeline)
python extract.py --sample
```

Os arquivos `.dbc` baixados ficam em `data_raw/` (~vários GB para o período
completo de 10 anos — SIH é o maior).

## Notas técnicas

- **Decompressão DBC**: usamos `datasus-dbc` (binding Python para o
  decompressor Rust do formato proprietário do DATASUS) e em seguida
  `dbfread` para leitura do DBF resultante.
- **Resiliência**: o downloader faz retry com backoff exponencial; arquivos
  inexistentes (404) são silenciosamente pulados (cobre buracos em UFs
  pequenas em determinados meses).
- **Performance**: lemos só as colunas necessárias do DBF, o que reduz
  drasticamente o uso de memória em estados grandes.
- **Cobertura de SIH**: cobre apenas internações **na rede SUS**. Para
  estimar o total nacional, considerar dados complementares da ANS para
  rede privada.
- **Causa básica vs. principal**: SIM usa `CAUSABAS` (causa básica), SIH usa
  `DIAG_PRINC` (diagnóstico principal da AIH). São conceitos diferentes —
  internações por A09 não implicam óbito por A09.

## Roadmap

Próximos indicadores planejados:

- Mortalidade infantil por causas evitáveis (Lista BR de Causas Evitáveis)
- Cobertura vacinal por imunobiológico (PNI)
- Internações sensíveis à atenção primária em <5 anos
- Baixo peso ao nascer e prematuridade (SINASC)
