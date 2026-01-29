# -*- coding: utf-8 -*-
"""
Analise 3.0 (Bairros) — HTML responsivo (estilo Analise 2.0) + CSVs por faixa

Gera:
- Chacara:
  - chacara_bairros_idade_0_19_2026.csv  (ordenado por Distancia)
  - chacara_bairros_idade_0_4_2026.csv   (ordenado por Score Composto)
  - chacara_bairros_idade_5_9_2026.csv   (ordenado por Score Composto)
  - chacara_bairros_idade_10_14_2026.csv (ordenado por Score Composto)
  - chacara_bairros_idade_15_19_2026.csv (ordenado por Score Composto)
  - chacara_bairros_relatorio_2026.html
- Morumbi:
  - morumbi_bairros_idade_0_9_2026.csv   (ordenado por Distancia)
  - morumbi_bairros_idade_0_4_2026.csv   (ordenado por Score Composto)
  - morumbi_bairros_idade_5_9_2026.csv   (ordenado por Score Composto)
  - morumbi_bairros_relatorio_2026.html

Fonte: data/base_principal.csv (pipeline de CEP/bairro já resolvido).
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

def infer_children_label(title: str, df: pd.DataFrame) -> str:
    """Infere o rótulo de 'Crianças X-Y' a partir do título da tabela ou das colunas do dataframe."""
    t = (title or "").lower()
    # tenta ler faixa pelo título (0-4, 5-9, 10-14, 15-19, 0-9, 0-19)
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", t)
    if m:
        return f"Crianças {m.group(1)}-{m.group(2)}"
    # fallback: tenta achar coluna de crianças
    for c in df.columns:
        cl = str(c).lower().replace(" ", "_")
        if cl.startswith("criancas_") or cl.startswith("crianças_"):
            # pega sufixo
            suf = cl.split("criancas_")[-1].split("crianças_")[-1]
            suf = suf.replace("_", "-")
            return f"Crianças {suf}"
    return "Crianças"


# -----------------------------
# Config
# -----------------------------
INFLATION_FACTOR_DEFAULT = 1.155

MORUMBI_SCHOOL = (-23.6153631, -46.7340329)
CHACARA_SCHOOL = (-23.6338466, -46.7131974)

DEFAULT_OSRM_BASE = "http://router.project-osrm.org"
DEFAULT_CACHE_DIR = Path("data/cache")
DEFAULT_OSRM_CACHE_CSV = DEFAULT_CACHE_DIR / "osrm_bairros_distance_cache.csv"

DEFAULT_OUT_DIR = Path("analises/analise_3.0/out")


# -----------------------------
# Helpers
# -----------------------------
def _project_root_fallback() -> Path:
    # Tenta detectar raiz do repo a partir do local deste arquivo
    return Path(__file__).resolve().parents[2]


def project_root() -> Path:
    try:
        from _datasets import project_root as pr  # type: ignore
        return pr()
    except Exception:
        return _project_root_fallback()


def resolve_base_principal() -> Path:
    try:
        from _datasets import resolve_base_path  # type: ignore
        p = resolve_base_path("principal")
        if p is not None:
            return p
    except Exception:
        pass
    return project_root() / "data/base_principal.csv"


def to_float_br_money(x) -> float:
    if pd.isna(x):
        return float("nan")
    s = str(x).strip()
    if not s:
        return float("nan")
    # remove R$, pontos de milhar e troca virgula por ponto
    s = s.replace("R$", "").replace("\u00a0", " ").strip()
    s = s.replace(".", "").replace(",", ".")
    # deixa só digitos/ponto/menos
    s = re.sub(r"[^0-9\.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return float("nan")


def fmt_int(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    try:
        return f"{int(round(float(x))):,}".replace(",", ".")
    except Exception:
        return "—"


def fmt_float(x, nd=2) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    try:
        s = f"{float(x):,.{nd}f}"
        # 12,345.67 -> 12.345,67
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return s
    except Exception:
        return "—"


def fmt_money_brl(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    try:
        return "R$ " + fmt_float(x, 2)
    except Exception:
        return "—"

def fmt_km(x) -> str:
    s = fmt_float(x, 2)
    return "—" if s == "—" else f"{s} km"


def norm_bairro(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def osrm_table_distances_km(
    lats: pd.Series,
    lons: pd.Series,
    source_lat: float,
    source_lon: float,
    base_url: str,
    batch_size: int = 100,
    timeout_s: float = 30.0,
    sleep_s: float = 0.2,
) -> pd.Series:
    """
    Calcula distancias (km) via OSRM /table em lotes.
    Retorna NaN se falhar.
    """
    import json
    import time
    import urllib.request

    idx = lats.index
    out = []
    coords_all = list(zip(lats.tolist(), lons.tolist()))
    for i in range(0, len(coords_all), batch_size):
        chunk = coords_all[i : i + batch_size]
        # source + destinations
        coords = [(source_lat, source_lon)] + chunk
        coords_str = ";".join([f"{lon},{lat}" for (lat, lon) in coords])
        url = f"{base_url.rstrip('/')}/table/v1/driving/{coords_str}?sources=0&annotations=distance"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            if data.get("code") != "Ok":
                raise RuntimeError(f"OSRM code != Ok: {data.get('code')}")
            dist_m = (data.get("distances") or [[]])[0][1:]  # ignora source
            # convert m -> km
            for d in dist_m:
                out.append(float(d) / 1000 if d is not None else float("nan"))
        except Exception:
            out.extend([float("nan")] * len(chunk))

        if sleep_s:
            time.sleep(sleep_s)

    return pd.Series(out, index=idx, dtype="float64")


def load_distance_cache(path: Path) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path, dtype={"unidade": str, "Bairro": str})
        df["unidade"] = df["unidade"].astype(str).str.strip().str.lower()
        df["Bairro"] = df["Bairro"].astype(str).map(norm_bairro)
        return df
    return pd.DataFrame(columns=["unidade", "Bairro", "distancia_km"])


def save_distance_cache(path: Path, df_cache: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df_cache = df_cache.dropna(subset=["unidade", "Bairro"])
    df_cache.to_csv(path, index=False, encoding="utf-8-sig")


def add_scores(df_in: pd.DataFrame, children_col: str) -> pd.DataFrame:
    df = df_in.copy()
    df["score_trafego_2026"] = df["renda_mediana_2026"] * df[children_col].fillna(0)

    renda_rank = df["renda_mediana_2026"].rank(pct=True)
    criancas_rank = df[children_col].rank(pct=True)
    dist_rank = df["distancia_mediana_km"].rank(pct=True, ascending=True)
    proximidade_rank = 1 - dist_rank

    df["score_composto_2026"] = (
        (proximidade_rank * 0.5 + renda_rank * 0.25 + criancas_rank * 0.25) * 100
    ).round(2)
    return df


# -----------------------------
# HTML (estilo Analise 2.0)
# -----------------------------
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
  // Mantem o Dicionario de dados fechado no mobile para nao ficar gigante
  try {
    const glossary = document.querySelector("details.glossary");
    if (glossary) {
      if (window.innerWidth <= 640) glossary.removeAttribute("open");
      else glossary.setAttribute("open", "open");
    }
  } catch (e) {}
})();"""

GLOSSARY_HTML = """<details class='glossary' open>
  <summary>Dicionario de dados</summary>
  <div class='card'>
    <div class='glossary'>
      <ul>
        <li><b>Bairro</b>: bairro agregado (nome padronizado).</li>
        <li><b>Renda</b>: <code>renda_mediana_2026</code> = mediana da renda (base) ajustada por inflacao (fator {infl}).</li>
        <li><b>Criancas (faixa)</b>: mediana de criancas no bairro para a faixa mostrada na tabela.</li>
        <li><b>Populacao</b>: <code>populacao_mediana</code> = mediana da populacao no bairro (campo <code>populacao_total</code>).</li>
        <li><b>Distancia</b>: <code>distancia_mediana_km</code> = distancia (km) do centroide do bairro ate a escola via OSRM (carro), com cache.</li>
        <li><b>Amostra</b>: quantidade de registros usados no agrupamento do bairro.</li>
        <li><b>Score Trafego</b>: <code>score_trafego_2026</code> = <code>renda_mediana_2026</code> x criancas (faixa da tabela).</li>
        <li><b>Score Composto</b>: media ponderada dos ranks percentuais: proximidade (50%), renda (25%), criancas (25%), normalizado 0-100.</li>
      </ul>
      <p class='meta'>Observacao: utiliza mediana por bairro para reduzir ruido de outliers.</p>
    </div>
  </div>
</details>"""

def html_table(df_view: pd.DataFrame, table_id: str, title: str) -> str:
    if df_view is None or df_view.empty:
        return f"<h2>{title}</h2><p class='meta'>Arquivo nao encontrado.</p>"

    table_html = df_view.to_html(index=False, border=0, classes="dataframe", table_id=table_id)
    toggle_id = f"toggle-{table_id}"
    label_html = (
        f"<label class='toggle-btn' for='{toggle_id}'>"
        f"<span class='more'>Mostrar mais</span>"
        f"<span class='less'>Mostrar menos</span>"
        f"</label>"
    )

    return (
        f"<section class='table-section'>"
        f"<h2>{title}</h2>"
        f"<input class='table-toggle' type='checkbox' id='{toggle_id}' />"
        f"{label_html}"
        f"<div class='table-wrap'>{table_html}</div>"
        f"</section>"
    )


def render_html_page(
    unidade: str,
    school_lat: float,
    school_lon: float,
    inflation: float,
    tables: List[Tuple[str, str, pd.DataFrame]],
) -> str:
    unidade_title = "Chacara" if unidade == "chacara" else "Morumbi"
    tables_html = "\n".join([html_table(df, tid, title) for (tid, title, df) in tables])

    return f"""<!DOCTYPE html>
<html lang='pt-br'>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>Relatorio de Bairros - {unidade_title}</title>
  <style>{HTML_CSS}</style>
</head>
<body>
  <div class='container'>
    <div class='header'>
      <div class='brand'>
        <div class='header-title'>Colegio Elvira Brandao</div>
        <div class='header-subtitle'>Relatorio de Bairros - {unidade_title}</div>
      </div>
      <div class='badge'>Analise 3.0</div>
    </div>

    <div class='card'>
      <div class='meta-grid'>
        <div class='meta-item'><b>Base:</b> data/base_principal.csv</div>
        <div class='meta-item'><b>Inflacao aplicada:</b> {inflation}</div>
        <div class='meta-item'><b>Coluna de bairro usada:</b> Bairro</div>
        <div class='meta-item'><b>Escola (lat, lon):</b> {school_lat}, {school_lon}</div>
      </div>
    </div>

    {tables_html}

    {GLOSSARY_HTML.format(infl=inflation)}
  </div>
  <script>{HTML_JS}</script>
  <footer class='footer'>
    Desenvolvido por Breno Rodrigues Azevedo |
    <a href='https://www.linkedin.com/in/breno-azevedo-9109b8232/' target='_blank' rel='noopener'>LinkedIn</a>
    |
    <a href='https://github.com/brenoazvd' target='_blank' rel='noopener'>GitHub</a>
  </footer>
</body>
</html>
"""


# -----------------------------
# Pipeline
# -----------------------------
@dataclass
class TableSpec:
    key: str
    children_col: str
    children_label: str
    order_by: str
    ascending: bool
    title: str


def aggregate_bairros(df: pd.DataFrame, inflation: float, unidade: str) -> pd.DataFrame:
    df = df.copy()
    df["unidade"] = df["unidade"].astype(str).str.strip().str.lower()
    df = df[df["unidade"] == unidade].copy()

    df["Bairro"] = df["Bairro"].map(norm_bairro)

    # renda
    df["renda_media_num"] = df["renda_media"].map(to_float_br_money)
    # criancas (garante numeric)
    for c in ["v01031_0_4anos","v01032_5_9anos","v01033_10_14anos","v01034_15_19anos","populacao_total"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["criancas_0_4"] = df["v01031_0_4anos"]
    df["criancas_5_9"] = df["v01032_5_9anos"]
    df["criancas_10_14"] = df["v01033_10_14anos"]
    df["criancas_15_19"] = df["v01034_15_19anos"]
    df["criancas_0_9"] = df["criancas_0_4"].fillna(0) + df["criancas_5_9"].fillna(0)
    df["criancas_0_19"] = (
        df["criancas_0_4"].fillna(0) + df["criancas_5_9"].fillna(0) + df["criancas_10_14"].fillna(0) + df["criancas_15_19"].fillna(0)
    )

    g = df.groupby("Bairro", dropna=False)

    out = pd.DataFrame({
        "Bairro": g.size().index.astype(str),
        "pontos": g.size().values,
        "lat_mediana": g["latitude_centro"].median().values,
        "lon_mediana": g["longitude_centro"].median().values,
        "renda_mediana_2026": g["renda_media_num"].median().values * inflation,
        "populacao_mediana": g["populacao_total"].median().values,
        "criancas_0_4_mediana": g["criancas_0_4"].median().values,
        "criancas_5_9_mediana": g["criancas_5_9"].median().values,
        "criancas_10_14_mediana": g["criancas_10_14"].median().values,
        "criancas_15_19_mediana": g["criancas_15_19"].median().values,
        "criancas_0_9_mediana": g["criancas_0_9"].median().values,
        "criancas_0_19_mediana": g["criancas_0_19"].median().values,
    })
    return out


def compute_distances_with_cache(
    df_bairros: pd.DataFrame,
    unidade: str,
    school_lat: float,
    school_lon: float,
    base_url: str,
    cache_csv: Path,
) -> pd.DataFrame:
    df = df_bairros.copy()
    cache = load_distance_cache(cache_csv)
    cache_u = cache[cache["unidade"] == unidade].copy()

    df["Bairro"] = df["Bairro"].map(norm_bairro)
    cache_u = cache_u.set_index("Bairro")

    dist = []
    to_calc_idx = []
    for i, r in df.iterrows():
        b = r["Bairro"]
        if b in cache_u.index and pd.notna(cache_u.loc[b, "distancia_km"]):
            dist.append(float(cache_u.loc[b, "distancia_km"]))
        else:
            dist.append(float("nan"))
            to_calc_idx.append(i)

    df["distancia_mediana_km"] = dist

    if to_calc_idx:
        sub = df.loc[to_calc_idx]
        d_new = osrm_table_distances_km(
            sub["lat_mediana"], sub["lon_mediana"],
            source_lat=school_lat, source_lon=school_lon,
            base_url=base_url,
        )
        df.loc[to_calc_idx, "distancia_mediana_km"] = d_new.values

        # atualiza cache
        cache_add = pd.DataFrame({
            "unidade": unidade,
            "Bairro": sub["Bairro"].values,
            "distancia_km": d_new.values,
        })
        if not cache_add.empty:
            cache = pd.concat([cache, cache_add], ignore_index=True)
        # dedup: mantem ultimo valor nao-nan
        cache = cache.sort_values(["unidade", "Bairro"]).drop_duplicates(["unidade","Bairro"], keep="last")
        save_distance_cache(cache_csv, cache)

    return df


def build_outputs(unidade: str, df_bairros: pd.DataFrame, specs: List[TableSpec], out_dir: Path) -> Tuple[List[Tuple[str,str,pd.DataFrame]], List[Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_for_html = []
    csv_paths: List[Path] = []

    for spec in specs:
        df_sc = add_scores(df_bairros, spec.children_col)
        df_sc = df_sc.sort_values(spec.order_by, ascending=spec.ascending).copy()

        # CSV (raw numeric)
        csv_name = f"{unidade}_bairros_idade_{spec.key}_2026.csv"
        csv_path = out_dir / csv_name
        df_csv = df_sc[[
            "Bairro",
            "renda_mediana_2026",
            spec.children_col,
            "populacao_mediana",
            "distancia_mediana_km",
            "pontos",
            "score_trafego_2026",
            "score_composto_2026",
        ]].copy()
        df_csv = df_csv.rename(columns={spec.children_col: f"criancas_{spec.key}"})
        df_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
        csv_paths.append(csv_path)

        # HTML view (friendly)
        df_view = pd.DataFrame({
            "Bairro": df_sc["Bairro"],
            "Renda": df_sc["renda_mediana_2026"],
            spec.children_label: df_sc[spec.children_col],
            "Populacao": df_sc["populacao_mediana"],
            "Distancia": df_sc["distancia_mediana_km"],
            "Amostra": df_sc["pontos"],
            "Score Trafego": df_sc["score_trafego_2026"],
            "Score Composto": df_sc["score_composto_2026"],
        })
        # Formata valores para HTML (estilo Analise 2.0)
        df_view["Renda"] = df_view["Renda"].map(fmt_money_brl)
        df_view[spec.children_label] = df_view[spec.children_label].map(lambda x: fmt_float(x, 1))
        df_view["Populacao"] = df_view["Populacao"].map(fmt_int)
        df_view["Distancia"] = df_view["Distancia"].map(fmt_km)
        df_view["Amostra"] = df_view["Amostra"].map(fmt_int)
        df_view["Score Trafego"] = df_view["Score Trafego"].map(lambda x: fmt_float(x, 2))
        df_view["Score Composto"] = df_view["Score Composto"].map(lambda x: fmt_float(x, 2))
        table_id = f"{unidade}_{spec.key}"
        tables_for_html.append((table_id, spec.title, df_view))

    return tables_for_html, csv_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inflation", type=float, default=INFLATION_FACTOR_DEFAULT)
    ap.add_argument("--osrm", type=str, default=DEFAULT_OSRM_BASE)
    ap.add_argument("--cache", type=str, default=str(DEFAULT_OSRM_CACHE_CSV))
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--unidade", type=str, choices=["chacara","morumbi","ambas"], default="ambas")
    args = ap.parse_args()

    root = project_root()
    base_path = resolve_base_principal()
    out_dir = (root / args.out).resolve()
    cache_csv = (root / args.cache).resolve()

    print(f"[info] Base: {base_path}")
    df_base = pd.read_csv(base_path, low_memory=False)

    unidades = ["chacara","morumbi"] if args.unidade == "ambas" else [args.unidade]

    for unidade in unidades:
        if unidade == "chacara":
            school_lat, school_lon = CHACARA_SCHOOL
            specs = [
                TableSpec("0_19","criancas_0_19_mediana","Crian\u00e7as 0-19","distancia_mediana_km",True,"Chacara \u2013 Bairros (geral 0-19 anos) \u2014 ordenado por: Distancia"),
                TableSpec("0_4","criancas_0_4_mediana","Crian\u00e7as 0-4","score_composto_2026",False,"Chacara \u2013 Bairros (faixa 0-4 anos) \u2014 ordenado por: Score Composto"),
                TableSpec("5_9","criancas_5_9_mediana","Crian\u00e7as 5-9","score_composto_2026",False,"Chacara \u2013 Bairros (faixa 5-9 anos) \u2014 ordenado por: Score Composto"),
                TableSpec("10_14","criancas_10_14_mediana","Crian\u00e7as 10-14","score_composto_2026",False,"Chacara \u2013 Bairros (faixa 10-14 anos) \u2014 ordenado por: Score Composto"),
                TableSpec("15_19","criancas_15_19_mediana","Crian\u00e7as 15-19","score_composto_2026",False,"Chacara \u2013 Bairros (faixa 15-19 anos) \u2014 ordenado por: Score Composto"),
            ]
        else:
            school_lat, school_lon = MORUMBI_SCHOOL
            specs = [
                TableSpec("0_9","criancas_0_9_mediana","Crian\u00e7as 0-9","distancia_mediana_km",True,"Morumbi \u2013 Bairros (faixa 0-9 anos) \u2014 ordenado por: Distancia"),
                TableSpec("0_4","criancas_0_4_mediana","Crian\u00e7as 0-4","score_composto_2026",False,"Morumbi \u2013 Bairros (faixa 0-4 anos) \u2014 ordenado por: Score Composto"),
                TableSpec("5_9","criancas_5_9_mediana","Crian\u00e7as 5-9","score_composto_2026",False,"Morumbi \u2013 Bairros (faixa 5-9 anos) \u2014 ordenado por: Score Composto"),
            ]

        print(f"\n[info] Processando unidade: {unidade}")
        df_b = aggregate_bairros(df_base, args.inflation, unidade)
        df_b = compute_distances_with_cache(df_b, unidade, school_lat, school_lon, args.osrm, cache_csv)

        # gera CSVs + tabelas
        tables_html, csvs = build_outputs(unidade, df_b, specs, out_dir)
        html = render_html_page(unidade, school_lat, school_lon, args.inflation, tables_html)
        html_path = out_dir / f"{unidade}_bairros_relatorio_2026.html"
        html_path.write_text(html, encoding="utf-8")

        print(f"[ok] HTML: {html_path}")
        for p in csvs:
            print(f"[ok] CSV:  {p.name}")

    print("\n[FINAL] Analise 3.0 (bairros) concluida ✅")


if __name__ == "__main__":
    main()
