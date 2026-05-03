"""UF and region mappings used throughout the pipeline."""

from __future__ import annotations

# UF code (IBGE 2-digit) -> (sigla, nome, regiao)
UF_INFO: dict[str, tuple[str, str, str]] = {
    "11": ("RO", "Rondônia",            "Norte"),
    "12": ("AC", "Acre",                "Norte"),
    "13": ("AM", "Amazonas",            "Norte"),
    "14": ("RR", "Roraima",             "Norte"),
    "15": ("PA", "Pará",                "Norte"),
    "16": ("AP", "Amapá",               "Norte"),
    "17": ("TO", "Tocantins",           "Norte"),
    "21": ("MA", "Maranhão",            "Nordeste"),
    "22": ("PI", "Piauí",               "Nordeste"),
    "23": ("CE", "Ceará",               "Nordeste"),
    "24": ("RN", "Rio Grande do Norte", "Nordeste"),
    "25": ("PB", "Paraíba",             "Nordeste"),
    "26": ("PE", "Pernambuco",          "Nordeste"),
    "27": ("AL", "Alagoas",             "Nordeste"),
    "28": ("SE", "Sergipe",             "Nordeste"),
    "29": ("BA", "Bahia",               "Nordeste"),
    "31": ("MG", "Minas Gerais",        "Sudeste"),
    "32": ("ES", "Espírito Santo",      "Sudeste"),
    "33": ("RJ", "Rio de Janeiro",      "Sudeste"),
    "35": ("SP", "São Paulo",           "Sudeste"),
    "41": ("PR", "Paraná",              "Sul"),
    "42": ("SC", "Santa Catarina",      "Sul"),
    "43": ("RS", "Rio Grande do Sul",   "Sul"),
    "50": ("MS", "Mato Grosso do Sul",  "Centro-Oeste"),
    "51": ("MT", "Mato Grosso",         "Centro-Oeste"),
    "52": ("GO", "Goiás",               "Centro-Oeste"),
    "53": ("DF", "Distrito Federal",    "Centro-Oeste"),
}

UF_SIGLAS = [info[0] for info in UF_INFO.values()]
REGIOES = ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]


def uf_code_from_sigla(sigla: str) -> str:
    for code, (s, _, _) in UF_INFO.items():
        if s == sigla:
            return code
    raise KeyError(f"UF sigla desconhecida: {sigla}")


def sigla_from_uf_code(code: str | int) -> str:
    code_str = f"{int(code):02d}"
    return UF_INFO[code_str][0]


def regiao_from_uf_code(code: str | int) -> str:
    code_str = f"{int(code):02d}"
    return UF_INFO[code_str][2]


def regiao_from_sigla(sigla: str) -> str:
    return regiao_from_uf_code(uf_code_from_sigla(sigla))


def municipio_to_uf_code(mun_code: str | int) -> str:
    """IBGE municipio code -> UF code (first 2 digits)."""
    return f"{int(mun_code):07d}"[:2]
