#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALISE 2.0 — CEPs (motor da Analise 3.0) — PIPELINE DEFINITIVO (corrigido)

Correções aplicadas (pedidas):
1) População:
   - Calcula POPULACAO MEDIANA por CEP a partir de `populacao_total` (numérica),
     ignorando NaNs (se não houver dado -> 0).
   - Sai nos CSVs como coluna `Populacao` e aparece no HTML.
2) Crianças agregadas corretamente:
   - `criancas_0_9` = 0-4 + 5-9
   - `criancas_0_19` = 0-4 + 5-9 + 10-14 + 15-19
   - Isso evita “0-19 virar 15-19” (que acontece quando você usa a coluna errada no HTML).
3) Morumbi (HTML):
   - 1ª tabela: 0-9 ordenado por Distância
   - 2ª tabela: 0-4 ordenado por Score Composto
   - 3ª tabela: 5-9 ordenado por Score Composto
   - E o cabeçalho/coluna de crianças segue a faixa correta.
4) Geração completa:
   - Um único comando gera TODOS os CSVs (out/) + HTMLs finais.

Como executar (na raiz do repo):
  python analises/analise_2.0/analise_ceps_chacara_morumbi.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import requests


# ---------------------------------------------------------------------
# RESOLUÇÃO ROBUSTA DE PATHS (evita erro de import quando roda de qualquer pasta)
# ---------------------------------------------------------------------

def find_project_root(start: Path) -> Path:
    """Sobe diretórios até achar scripts/_datasets.py (ou data/base_principal.csv)."""
    for p in [start, *start.parents]:
        if (p / "scripts" / "_datasets.py").exists():
            return p
        if (p / "data" / "base_principal.csv").exists():
            return p
    # fallback: 2 níveis acima (padrão do repo)
    return start.parents[2]


HERE = Path(__file__).resolve()
ROOT = find_project_root(HERE)
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
ANALISE_DIR = ROOT / "analises" / "analise_2.0"
OUT_DIR = ANALISE_DIR / "out"
CACHE_DIR = DATA / "cache"

# tenta usar _datasets.py (se existir); senão fallback direto
sys.path.insert(0, str(SCRIPTS))

try:
    from _datasets import resolve_base_path  # type: ignore
except Exception:
    resolve_base_path = None  # type: ignore


# ---------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------

INFLATION_FACTOR = 1.155

ESCOLAS: Dict[str, Tuple[float, float]] = {
    "morumbi": (-23.6153631, -46.7340329),
    "chacara": (-23.6338466, -46.7131974),
}

OSRM_BASE = "http://router.project-osrm.org"
DIST_CACHE = CACHE_DIR / "cep_distancias_cache.csv"


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def normalize_cep(cep) -> str:
    """Normaliza qualquer CEP (int/float/str) para o formato #####-###."""
    if pd.isna(cep):
        return ""
    s = "".join(ch for ch in str(cep) if ch.isdigit())
    if len(s) < 8:
        s = s.zfill(8)
    s = s[:8]
    return f"{s[:5]}-{s[5:]}"


def rank_pct(s: pd.Series, ascending: bool = True) -> pd.Series:
    return s.rank(pct=True, ascending=ascending)


def parse_brl_number(x) -> float:
    """Converte 'R$ 10.835,91' -> 10835.91. Retorna NaN se não der."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    s = s.replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return np.nan


# ---------------------------------------------------------------------
# OSRM TABLE (motor da Analise 3.0)
# ---------------------------------------------------------------------

def osrm_table_distances_km(
    lats: pd.Series,
    lons: pd.Series,
    source_lat: float,
    source_lon: float,
    *,
    base_url: str,
    batch_size: int = 100,
    sleep_s: float = 0.2,
    timeout: float = 30.0,
) -> pd.Series:
    """
    Consulta OSRM /table em lotes (source = escola, destinations = centroides).
    Retorna distâncias em km (float), preservando o índice original.
    """
    lats = pd.to_numeric(lats, errors="coerce")
    lons = pd.to_numeric(lons, errors="coerce")

    distances: list[float] = []
    idx = lats.index

    with requests.Session() as sess:
        for start in range(0, len(lats), batch_size):
            batch_lats = lats.iloc[start : start + batch_size]
            batch_lons = lons.iloc[start : start + batch_size]

            valid_mask = batch_lats.notna() & batch_lons.notna()
            valid_lats = batch_lats[valid_mask]
            valid_lons = batch_lons[valid_mask]

            if valid_lats.empty:
                distances.extend([math.nan] * len(batch_lats))
                continue

            coords = [(source_lon, source_lat)] + list(zip(valid_lons, valid_lats))
            coords_str = ";".join([f"{lon:.6f},{lat:.6f}" for lon, lat in coords])

            url = (
                f"{base_url.rstrip('/')}/table/v1/driving/{coords_str}"
                f"?sources=0&annotations=distance"
            )

            try:
                r = sess.get(url, timeout=timeout)
                if r.status_code != 200:
                    dist_m = [None] * len(valid_lats)
                else:
                    data = r.json()
                    if data.get("code") != "Ok":
                        dist_m = [None] * len(valid_lats)
                    else:
                        dist_m = (data.get("distances") or [[]])[0][1:]
            except Exception:
                dist_m = [None] * len(valid_lats)

            while len(dist_m) < len(valid_lats):
                dist_m.append(None)

            valid_iter = iter(dist_m)
            for is_valid in valid_mask.tolist():
                if not is_valid:
                    distances.append(math.nan)
                else:
                    d = next(valid_iter, None)
                    distances.append(float(d) / 1000 if d is not None else math.nan)

            if sleep_s:
                time.sleep(sleep_s)

    return pd.Series(distances, index=idx, dtype="float64")


# ---------------------------------------------------------------------
# AGREGAÇÃO POR CEP (medianas)
# ---------------------------------------------------------------------

def aggregate_by_cep(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega a base por CEP e calcula:
      - renda_mediana_2026 (mediana de renda_media * inflação)
      - populacao_mediana (mediana de populacao_total ignorando NaN)
      - medianas de crianças nas faixas + somas (0-9 e 0-19)
      - centroides medianos e amostra (pontos)
    """
    df = df.copy()

    # Normaliza CEP
    df["CEP"] = df["CEP"].apply(normalize_cep)

    # Normaliza renda
    if "renda_media" in df.columns:
        # pode vir numérica ou "R$ ..."
        if df["renda_media"].dtype == object:
            df["renda_media"] = df["renda_media"].map(parse_brl_number)
        df["renda_media"] = pd.to_numeric(df["renda_media"], errors="coerce")

    # Normaliza população
    if "populacao_total" in df.columns:
        df["populacao_total"] = pd.to_numeric(df["populacao_total"], errors="coerce")

    # Crianças (base)
    df["criancas_0_4"] = pd.to_numeric(df.get("v01031_0_4anos"), errors="coerce")
    df["criancas_5_9"] = pd.to_numeric(df.get("v01032_5_9anos"), errors="coerce")
    df["criancas_10_14"] = pd.to_numeric(df.get("v01033_10_14anos"), errors="coerce")
    df["criancas_15_19"] = pd.to_numeric(df.get("v01034_15_19anos"), errors="coerce")

    # Somas (para garantir 0-9 e 0-19 corretos)
    df["criancas_0_9"] = df["criancas_0_4"].fillna(0) + df["criancas_5_9"].fillna(0)
    df["criancas_0_19"] = (
        df["criancas_0_4"].fillna(0)
        + df["criancas_5_9"].fillna(0)
        + df["criancas_10_14"].fillna(0)
        + df["criancas_15_19"].fillna(0)
    )

    grouped = df.groupby("CEP", dropna=False)

    def median_ignoring_nan(s: pd.Series) -> float:
        s2 = pd.to_numeric(s, errors="coerce").dropna()
        return float(s2.median()) if not s2.empty else 0.0

    out = pd.DataFrame(
        {
            "CEP": grouped.size().index.astype(str),
            "pontos": grouped.size().values,
            "lat_mediana": grouped["latitude_centro"].median().values,
            "lon_mediana": grouped["longitude_centro"].median().values,
            "renda_mediana_2026": grouped["renda_media"].median().values * INFLATION_FACTOR,
            # POPULAÇÃO MEDIANA (corrigido e robusto)
            "populacao_mediana": grouped["populacao_total"].apply(median_ignoring_nan).values,
            "Bairro": grouped["Bairro"].agg(
                lambda s: s.dropna().astype(str).value_counts().index[0]
                if not s.dropna().empty
                else ""
            ).values,
            "mediana_criancas_0_4": grouped["criancas_0_4"].median().values,
            "mediana_criancas_5_9": grouped["criancas_5_9"].median().values,
            "mediana_criancas_10_14": grouped["criancas_10_14"].median().values,
            "mediana_criancas_15_19": grouped["criancas_15_19"].median().values,
            "mediana_criancas_0_9": grouped["criancas_0_9"].median().values,
            "mediana_criancas_0_19": grouped["criancas_0_19"].median().values,
        }
    )

    # Normaliza CEP na saída (garante padrão)
    out["CEP"] = out["CEP"].apply(normalize_cep)
    return out


# ---------------------------------------------------------------------
# SCORES
# ---------------------------------------------------------------------

def add_scores(df: pd.DataFrame, criancas_col: str) -> pd.DataFrame:
    out = df.copy()

    out["score_trafego_2026"] = out["renda_mediana_2026"] * out[criancas_col]

    # ranks percentuais
    renda_rank = rank_pct(out["renda_mediana_2026"], ascending=True)
    criancas_rank = rank_pct(out[criancas_col], ascending=True)
    dist_rank = rank_pct(out["distancia_mediana_km"], ascending=True)

    proximidade_rank = 1.0 - dist_rank

    out["score_composto_2026"] = (
        0.50 * proximidade_rank
        + 0.25 * renda_rank
        + 0.25 * criancas_rank
    ) * 100.0

    out["score_composto_2026"] = out["score_composto_2026"].round(2)

    return out


# ---------------------------------------------------------------------
# HTML (integrado no script; não depende do gerar_relatorio_analise_2.py)
# ---------------------------------------------------------------------

HTML_CSS = """
:root {
  --brand-blue: #1f4ea3;
  --brand-teal: #1aa3a8;
  --brand-navy: #0f2f66;
  --brand-light: #f4f7fb;
  --brand-card: #ffffff;
  --text-dark: #122033;
  --text-muted: #52627a;
  --border: #d9e2f1;
  --shadow: 0 12px 30px rgba(20, 40, 90, 0.08);
}

.footer { margin-top: 22px; padding: 14px 8px; text-align: center; color: var(--text-muted); font-size: 13px; }
.footer a { color: var(--brand-blue); text-decoration: none; font-weight: 700; }
.footer a:hover { text-decoration: underline; }

body { font-family: "Segoe UI", Arial, sans-serif; margin: 0; color: var(--text-dark); background: var(--brand-light); }
.container { max-width: 1120px; margin: 0 auto; padding: 28px 24px 36px; }
.header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.brand { display: flex; flex-direction: column; gap: 4px; }
.header-title { font-size: 28px; font-weight: 800; color: var(--brand-blue); }
.header-subtitle { font-size: 16px; color: var(--brand-teal); }
.badge { background: rgba(31, 78, 163, 0.12); color: var(--brand-blue); padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.card { background: var(--brand-card); border-radius: 16px; box-shadow: var(--shadow); padding: 16px 18px; border: 1px solid var(--border); margin-bottom: 18px; }
.meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.meta-item { color: var(--text-muted); font-size: 13px; line-height: 1.3; }
.meta-item b { color: var(--text-dark); }
.note { border-left: 4px solid var(--brand-teal); padding: 10px 14px; background: #f0fbfc; border-radius: 12px; color: var(--text-dark); }
h2 { margin: 22px 0 10px 0; color: var(--brand-navy); font-size: 22px; }
.table-actions { display: flex; justify-content: flex-end; margin: 10px 0 0; }
.toggle-btn { background: rgba(31, 78, 163, 0.10); color: var(--brand-blue); border: 1px solid rgba(31, 78, 163, 0.20); padding: 8px 12px; border-radius: 999px; cursor: pointer; font-weight: 700; }
.toggle-btn:hover { background: rgba(31, 78, 163, 0.16); }
table.dataframe { width: 100%; border-collapse: collapse; background: white; border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
table.dataframe th { text-align: left; background: #eaf1ff; color: var(--brand-navy); font-weight: 800; font-size: 13px; padding: 10px 10px; border-bottom: 1px solid var(--border); }
code { background: rgba(31,78,163,0.08); padding: 2px 6px; border-radius: 8px; }

table.dataframe td { padding: 10px 10px; border-bottom: 1px solid var(--border); font-size: 13px; }
table.dataframe tr:nth-child(even) td { background: #fbfdff; }
.meta { color: var(--text-muted); font-size: 13px; }

@media (max-width: 980px) {
  .meta-grid { grid-template-columns: repeat(2, 1fr); }
}
.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 14px; }
.table-wrap table.dataframe { min-width: 760px; }
details.glossary { margin-top: 18px; }
details.glossary > summary { cursor: pointer; font-weight: 900; color: var(--brand-navy); font-size: 22px; padding: 10px 0; }
details.glossary[open] > summary { margin-bottom: 8px; }
details.glossary .card { margin-top: 8px; }
@media (max-width: 640px) {
  .container { padding: 14px 10px 24px; }
  .header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .badge { align-self: flex-end; }
  .header-title { font-size: 30px; line-height: 1.1; }
  .header-subtitle { font-size: 15px; }
  h2 { font-size: 20px; }
  table.dataframe th, table.dataframe td { padding: 8px 8px; font-size: 12px; }
  .toggle-btn { width: 100%; justify-content: center; }
  .meta-grid { grid-template-columns: 1fr; }
  .table-wrap table.dataframe { min-width: 680px; }
}


/* -----------------------------
   Toggle de tabelas (CSS-only)
   ----------------------------- */
.table-section { margin-bottom: 18px; }
.table-toggle { position: absolute; opacity: 0; pointer-events: none; }
.table-section .toggle-btn { display: inline-flex; align-items: center; gap: 8px; margin: 10px 0 0; user-select: none; }
.table-section .toggle-btn .less { display: none; }
.table-toggle:checked + .toggle-btn .more { display: none; }
.table-toggle:checked + .toggle-btn .less { display: inline; }

/* Colapsa linhas por padrão (desktop) */
.table-section .table-wrap table.dataframe tbody tr:nth-child(n+13) { display: none; }
/* Expande quando marcado */
.table-toggle:checked ~ .table-wrap table.dataframe tbody tr { display: table-row; }

@media (max-width: 640px) {
  /* Colapsa menos linhas no mobile */
  .table-section .table-wrap table.dataframe tbody tr:nth-child(n+9) { display: none; }
}

"""

HTML_JS = """(function() {
  // Mantém o Dicionário de dados fechado no mobile para não ficar gigante
  try {
    const glossary = document.querySelector("details.glossary");
    if (glossary) {
      if (window.innerWidth <= 640) glossary.removeAttribute("open");
      else glossary.setAttribute("open", "open");
    }
  } catch (e) {}
})();"""


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )



def format_ptbr_number(x, decimals: int = 2) -> str:
    """Formata número para padrão pt-BR: 12345.6 -> '12.345,60' """
    try:
        if x is None:
            return "—"
        v = float(x)
        if math.isnan(v):
            return "—"
    except Exception:
        return "—"
    s = f"{v:,.{decimals}f}"
    # s vem como 12,345.67; troca para 12.345,67
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def format_currency_brl(x) -> str:
    s = format_ptbr_number(x, decimals=2)
    return "—" if s == "—" else f"R$ {s}"


def format_int_ptbr(x) -> str:
    try:
        if x is None:
            return "—"
        v = float(x)
        if math.isnan(v):
            return "—"
        v = int(round(v))
    except Exception:
        return "—"
    return f"{v:,}".replace(",", ".")


def format_km(x) -> str:
    s = format_ptbr_number(x, decimals=2)
    return "—" if s == "—" else f"{s} km"


def format_score(x) -> str:
    return format_ptbr_number(x, decimals=2)


def format_children(x) -> str:
    """Crianças é contagem; mostra inteiro quando possível, senão 1 casa."""
    try:
        if x is None:
            return "—"
        v = float(x)
        if math.isnan(v):
            return "—"
    except Exception:
        return "—"
    if abs(v - round(v)) < 1e-9:
        return format_int_ptbr(v)
    return format_ptbr_number(v, decimals=1)


GLOSSARY_HTML = """<details class='glossary' open>
  <summary>Dicionário de dados</summary>
  <div class='card'>
    <div class='glossary'>
      <ul>
        <li><b>CEP</b>: CEP agregado (formato <code>#####-###</code>).</li>
        <li><b>Bairro</b>: bairro mais frequente dentro do CEP (modo).</li>
        <li><b>Renda</b>: <code>renda_mediana_2026</code> = mediana da renda (base) ajustada por inflação (fator {infl}).</li>
        <li><b>Crianças (faixa)</b>: mediana de crianças no CEP para a faixa mostrada na tabela.</li>
        <li><b>População</b>: <code>populacao_mediana</code> = mediana da população no CEP (campo <code>populacao_total</code>), ignorando vazios.</li>
        <li><b>Distância</b>: <code>distancia_mediana_km</code> = distância (km) do centróide do CEP até a escola via OSRM (carro), com cache por CEP.</li>
        <li><b>Amostra</b>: <code>pontos</code> = quantidade de registros usados no CEP.</li>
        <li><b>Score Tráfego</b>: <code>score_trafego_2026</code> = <code>renda_mediana_2026</code> × crianças (faixa da tabela).</li>
        <li><b>Score Composto</b>: média ponderada dos ranks percentuais: proximidade (50%), renda (25%), crianças (25%), normalizado 0–100.</li>
      </ul>
      <p class='meta'>Observação: utiliza mediana por CEP para reduzir ruído de outliers.</p>
    </div>
  </div>
</details>"""
def render_table(title: str, df: pd.DataFrame, table_id: str) -> str:
    """Renderiza uma tabela com toggle *sem JavaScript* (funciona em preview mobile).
    - Por padrão mostra só as primeiras linhas (desktop: 12, mobile: 8) via CSS.
    - O usuário expande/recolhe com um checkbox + label (CSS-only).
    """
    if df is None or df.empty:
        return f"<h2>{html_escape(title)}</h2><p class='meta'>Arquivo não encontrado.</p>"

    table_html = df.to_html(index=False, border=0, classes="dataframe", table_id=table_id)

    # Estrutura (CSS-only):
    # <section class='table-section'>
    #   <h2>..</h2>
    #   <input id='toggle-t1' ...>
    #   <label for='toggle-t1' class='toggle-btn'>...</label>
    #   <div class='table-wrap'> ...table... </div>
    # </section>
    toggle_id = f"toggle-{table_id}"
    label_html = (
        f"<label class='toggle-btn' for='{toggle_id}'>"
        f"<span class='more'>Mostrar mais</span>"
        f"<span class='less'>Mostrar menos</span>"
        f"</label>"
    )

    return (
        f"<section class='table-section'>"
        f"<h2>{html_escape(title)}</h2>"
        f"<input class='table-toggle' type='checkbox' id='{toggle_id}' />"
        f"{label_html}"
        f"<div class='table-wrap'>{table_html}</div>"
        f"</section>"
    )


def build_report_html(
    unidade: str,
    escola_lat: float,
    escola_lon: float,
    sections: list[tuple[str, str, str]],
    output_path: Path,
) -> None:
    """
    sections: lista de (csv_filename, titulo_secao, sort_mode)
      sort_mode: "distancia" ou "score"
    """
    base_ref = "data/base_principal.csv"
    meta_items = [
        f"<div class='meta-item'><b>Base:</b> {html_escape(base_ref)}</div>",
        f"<div class='meta-item'><b>Inflação aplicada:</b> {INFLATION_FACTOR}</div>",
        "<div class='meta-item'><b>Coluna de bairro usada:</b> CEP</div>",
        f"<div class='meta-item'><b>Escola (lat, lon):</b> {escola_lat}, {escola_lon}</div>",
    ]

    rendered_sections: list[str] = []
    for i, (fname, title, sort_mode) in enumerate(sections, start=1):
        csv_path = OUT_DIR / fname
        if not csv_path.exists():
            rendered_sections.append(render_table(title, pd.DataFrame(), f"t{i}"))
            continue

        df = pd.read_csv(csv_path)

        # Ordenação conforme pedido
        if sort_mode == "distancia" and "distancia_mediana_km" in df.columns:
            df = df.sort_values("distancia_mediana_km", ascending=True)
        elif sort_mode == "score" and "score_composto_2026" in df.columns:
            df = df.sort_values("score_composto_2026", ascending=False)

        # Detecta a coluna de crianças do arquivo (exatamente UMA: criancas_<faixa>)
        criancas_cols = [c for c in df.columns if c.startswith("criancas_")]
        criancas_col = criancas_cols[0] if criancas_cols else None
        criancas_label = "Criancas"
        if criancas_col:
            # ex: criancas_0_9 -> Criancas 0-9
            faixa = criancas_col.replace("criancas_", "").replace("_", "-")
            criancas_label = f"Criancas {faixa}"

        # Formatação/seleção final para HTML
        rename_map = {
            "CEP": "CEP",
            "Bairro": "Bairro",
            "renda_mediana_2026": "Renda",
            "Populacao": "Populacao",
            "distancia_mediana_km": "Distancia",
            "pontos": "Amostra",
            "score_trafego_2026": "Score Trafego",
            "score_composto_2026": "Score Composto",
        }
        if criancas_col:
            rename_map[criancas_col] = criancas_label

        ordered = [k for k in ["CEP","Bairro","renda_mediana_2026", criancas_col, "Populacao",
                               "distancia_mediana_km","pontos","score_trafego_2026","score_composto_2026"]
                   if k and k in df.columns]
        view = df[ordered].rename(columns=rename_map)

        # -----------------------------
        # Formatação (melhor leitura)
        # -----------------------------
        for colname in list(view.columns):
            if colname == "Renda":
                view[colname] = view[colname].map(format_currency_brl)
            elif colname.startswith("Criancas"):
                view[colname] = view[colname].map(format_children)
            elif colname == "Populacao":
                view[colname] = view[colname].map(format_int_ptbr)
            elif colname == "Distancia":
                view[colname] = view[colname].map(format_km)
            elif colname == "Amostra":
                view[colname] = view[colname].map(format_int_ptbr)
            elif colname == "Score Trafego":
                view[colname] = view[colname].map(lambda x: format_ptbr_number(x, decimals=2))
            elif colname == "Score Composto":
                view[colname] = view[colname].map(format_score)

        rendered_sections.append(render_table(title, view, f"t{i}"))

    titulo = "Colegio Elvira Brandao"
    subtitulo = f"Relatorio de CEPs - {unidade.title()}"

    html = "\n".join(
        [
            "<!DOCTYPE html>",
            "<html lang='pt-br'>",
            "<head>",
            "  <meta charset='utf-8' />",
            "  <meta name='viewport' content='width=device-width, initial-scale=1' />",
            f"  <title>{html_escape(titulo)}</title>",
            f"  <style>{HTML_CSS}</style>",
            "</head>",
            "<body>",
            "  <div class='container'>",
            "    <div class='header'>",
            "      <div class='brand'>",
            f"        <div class='header-title'>{html_escape(titulo)}</div>",
            f"        <div class='header-subtitle'>{html_escape(subtitulo)}</div>",
            "      </div>",
            "      <div class='badge'>Analise 2.0</div>",
            "    </div>",
            "    <div class='card'>",
            "      <div class='meta-grid'>",
            *meta_items,
            "      </div>",
            "    </div>",
            
            *rendered_sections,
            f"    {GLOSSARY_HTML.format(infl=INFLATION_FACTOR)}",
            "  </div>",
                        f"  <script>{HTML_JS}</script>",
            "  <footer class='footer'>",
            "    Desenvolvido por Breno Rodrigues Azevedo |",
            "    <a href='https://www.linkedin.com/in/breno-azevedo-9109b8232/' target='_blank' rel='noopener'>LinkedIn</a>",
            "    |",
            "    <a href='https://github.com/brenoazvd' target='_blank' rel='noopener'>GitHub</a>",
            "  </footer>",
            "</body>",
            "</html>",
        ]
    )

    output_path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Carrega base principal
    if resolve_base_path is not None:
        base_path = Path(resolve_base_path("principal"))
    else:
        base_path = DATA / "base_principal.csv"

    print(f"[info] Carregando base_principal: {base_path}")
    df_base = pd.read_csv(base_path, low_memory=False)

    # Cache de distâncias
    if DIST_CACHE.exists():
        df_cache = pd.read_csv(DIST_CACHE, dtype={"CEP": str, "unidade": str})
        df_cache["CEP"] = df_cache["CEP"].apply(normalize_cep)
        # normaliza nome de coluna antiga (se houver)
        if "distancia_km" not in df_cache.columns and "distancia" in df_cache.columns:
            df_cache = df_cache.rename(columns={"distancia": "distancia_km"})
    else:
        df_cache = pd.DataFrame(columns=["CEP", "unidade", "distancia_km"])

    for unidade in ["morumbi", "chacara"]:
        print(f"\n[info] Processando unidade: {unidade}")

        df = df_base[df_base["unidade"].astype(str).str.lower().str.contains(unidade)].copy()
        df_ceps = aggregate_by_cep(df)

        # Distância com cache por CEP
        escola_lat, escola_lon = ESCOLAS[unidade]

        # garante dtype str para merge
        df_ceps["CEP"] = df_ceps["CEP"].astype(str).apply(normalize_cep)
        df_cache["CEP"] = df_cache["CEP"].astype(str).apply(normalize_cep)

        df_ceps = df_ceps.merge(
            df_cache[df_cache["unidade"].astype(str).str.lower() == unidade][["CEP", "distancia_km"]],
            on="CEP",
            how="left",
        )

        missing = df_ceps["distancia_km"].isna()
        if missing.any():
            print(f"[info] Calculando {missing.sum()} distâncias novas via OSRM /table...")

            novas = osrm_table_distances_km(
                df_ceps.loc[missing, "lat_mediana"],
                df_ceps.loc[missing, "lon_mediana"],
                escola_lat,
                escola_lon,
                base_url=OSRM_BASE,
            )

            df_ceps.loc[missing, "distancia_km"] = novas.values

            novos_cache = pd.DataFrame(
                {
                    "CEP": df_ceps.loc[missing, "CEP"].astype(str),
                    "unidade": unidade,
                    "distancia_km": df_ceps.loc[missing, "distancia_km"],
                }
            )

            df_cache = pd.concat([df_cache, novos_cache], ignore_index=True)
            df_cache["CEP"] = df_cache["CEP"].apply(normalize_cep)
            df_cache.to_csv(DIST_CACHE, index=False, encoding="utf-8-sig")

        df_ceps["distancia_mediana_km"] = df_ceps["distancia_km"]

        # Definição de faixas por unidade
        if unidade == "morumbi":
            faixas = {
                "0_4": "mediana_criancas_0_4",
                "5_9": "mediana_criancas_5_9",
                "0_9": "mediana_criancas_0_9",
            }
        else:
            faixas = {
                "0_4": "mediana_criancas_0_4",
                "5_9": "mediana_criancas_5_9",
                "10_14": "mediana_criancas_10_14",
                "15_19": "mediana_criancas_15_19",
                "0_19": "mediana_criancas_0_19",
            }

        # Gera CSVs por faixa (com 1 coluna de crianças apenas, e Populacao correta)
        for key, col in faixas.items():
            df_final = add_scores(df_ceps, criancas_col=col)
            df_final = df_final.sort_values("score_trafego_2026", ascending=False)

            df_final = df_final[
                [
                    "CEP",
                    "Bairro",
                    "renda_mediana_2026",
                    col,
                    "populacao_mediana",
                    "distancia_mediana_km",
                    "pontos",
                    "score_trafego_2026",
                    "score_composto_2026",
                ]
            ].copy()

            df_final = df_final.rename(
                columns={
                    col: f"criancas_{key}",
                    "populacao_mediana": "Populacao",
                }
            )

            # Formata CEP já no padrão
            df_final["CEP"] = df_final["CEP"].apply(normalize_cep)

            fname = f"{unidade}_ceps_idade_{key}_2026.csv"
            path = OUT_DIR / fname
            df_final.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"[ok] Gerado: {path.name}")

    # -----------------------------------------------------------------
    # GERA HTML (integrado e correto)
    # -----------------------------------------------------------------
    print("\n[info] Gerando HTML da Analise 2.0 (integrado)...")

    # Morumbi: 0-9 por distância; depois 0-4 e 5-9 por score
    morumbi_sections = [
        ("morumbi_ceps_idade_0_9_2026.csv", "Morumbi – CEPs (faixa 0-9 anos) — ordenado por: Distancia", "distancia"),
        ("morumbi_ceps_idade_0_4_2026.csv", "Morumbi – CEPs (faixa 0-4 anos) — ordenado por: Score Composto", "score"),
        ("morumbi_ceps_idade_5_9_2026.csv", "Morumbi – CEPs (faixa 5-9 anos) — ordenado por: Score Composto", "score"),
    ]
    build_report_html(
        "morumbi",
        ESCOLAS["morumbi"][0],
        ESCOLAS["morumbi"][1],
        morumbi_sections,
        ANALISE_DIR / "ceps_relatorio_morumbi_2026.html",
    )

    # Chácara: mantém as tabelas por score; começa pelo 0-19 (geral)
    chacara_sections = [
        ("chacara_ceps_idade_0_19_2026.csv", "Chacara – CEPs (geral 0-19 anos) — ordenado por: Distancia", "distancia"),
        ("chacara_ceps_idade_0_4_2026.csv", "Chacara – CEPs (faixa 0-4 anos) — ordenado por: Score Composto", "score"),
        ("chacara_ceps_idade_5_9_2026.csv", "Chacara – CEPs (faixa 5-9 anos) — ordenado por: Score Composto", "score"),
        ("chacara_ceps_idade_10_14_2026.csv", "Chacara – CEPs (faixa 10-14 anos) — ordenado por: Score Composto", "score"),
        ("chacara_ceps_idade_15_19_2026.csv", "Chacara – CEPs (faixa 15-19 anos) — ordenado por: Score Composto", "score"),
    ]
    build_report_html(
        "chacara",
        ESCOLAS["chacara"][0],
        ESCOLAS["chacara"][1],
        chacara_sections,
        ANALISE_DIR / "ceps_relatorio_chacara_2026.html",
    )

    print("[ok] HTML gerado com sucesso")
    print("\n[FINAL] Analise 2.0 concluída (CSV + HTML) 🚀")


if __name__ == "__main__":
    main()
