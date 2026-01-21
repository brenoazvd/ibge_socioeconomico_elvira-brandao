from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from _datasets import (
    ANALISE_1_DIR,
    ANALISE_3_DIR,
    UNIDADES,
    project_root,
    resolve_base_path,
    resolve_mirror_path,
)

def read_csv_smart(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1")


def parse_renda_seguro(x) -> float:
    if pd.isna(x):
        return math.nan
    s = str(x)
    s = re.sub(r"[^0-9,\.]", "", s)
    if s.count(".") > 1:
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return math.nan


def haversine_km(lat, lon, lat0: float, lon0: float) -> np.ndarray:
    lat = np.radians(pd.to_numeric(lat, errors="coerce"))
    lon = np.radians(pd.to_numeric(lon, errors="coerce"))
    lat0 = math.radians(lat0)
    lon0 = math.radians(lon0)
    dlat = lat - lat0
    dlon = lon - lon0
    a = np.sin(dlat / 2) ** 2 + np.cos(lat0) * np.cos(lat) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return 6371.0 * c


def mode_with_share(series: pd.Series) -> pd.Series:
    series = series.dropna()
    if series.empty:
        return pd.Series({"cluster_predominante": np.nan, "cluster_share": np.nan})
    mode = series.mode()
    if mode.empty:
        return pd.Series({"cluster_predominante": np.nan, "cluster_share": np.nan})
    mode_val = mode.iat[0]
    share = (series == mode_val).mean()
    return pd.Series({"cluster_predominante": mode_val, "cluster_share": share})


def fmt_money(value) -> str:
    if pd.isna(value):
        return "-"
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_num(value, decimals: int = 2) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}"


def fmt_km(value) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.2f} km"


def resolve_input(
    base_dir: Path,
    raw_path: Path | None,
    clusters_path: Path | None,
    unidade: str,
) -> Path:
    if clusters_path and clusters_path.exists():
        return clusters_path

    default_clusters = base_dir / ANALISE_1_DIR / f"{unidade}_clusters.csv"
    if default_clusters.exists():
        return default_clusters

    if raw_path and raw_path.exists():
        return raw_path

    base_path = resolve_base_path("principal", root=base_dir, must_exist=True)
    if base_path:
        return base_path

    mirror_path = resolve_mirror_path(unidade, root=base_dir, must_exist=True)
    if mirror_path:
        return mirror_path

    raise FileNotFoundError("Nao foi possivel localizar o CSV da unidade.")


def choose_bairro_col(df: pd.DataFrame, preferred: str | None) -> str | None:
    if preferred:
        return preferred
    if "Bairro" in df.columns:
        return "Bairro"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analise por bairros usando lat/lon (unidade)."
    )
    parser.add_argument("--input", help="CSV de entrada (opcional).")
    parser.add_argument(
        "--clusters",
        help="CSV de clusters da analise 1.0 (opcional, preferido se existir).",
    )
    parser.add_argument(
        "--output-dir",
        default=ANALISE_3_DIR,
        help="Diretorio de saida para CSV e relatorio.",
    )
    parser.add_argument(
        "--bairro-col",
        help="Coluna de bairro a usar (default: Bairro).",
    )
    parser.add_argument(
        "--unidade",
        choices=UNIDADES,
        default="morumbi",
        help="Unidade para filtrar a base principal.",
    )
    parser.add_argument("--escola-lat", type=float, default=-23.6164)
    parser.add_argument("--escola-lon", type=float, default=-46.73831)
    parser.add_argument("--inflation-factor", type=float, default=1.155)
    parser.add_argument("--min-pontos", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--top-videos", type=int, default=8)
    args = parser.parse_args()

    base_dir = project_root()
    input_override = Path(args.input) if args.input else None
    if input_override and not input_override.is_absolute():
        input_override = base_dir / input_override
    clusters_override = Path(args.clusters) if args.clusters else None
    if clusters_override and not clusters_override.is_absolute():
        clusters_override = base_dir / clusters_override

    input_path = resolve_input(base_dir, input_override, clusters_override, args.unidade)
    df = read_csv_smart(input_path)
    if "unidade" in df.columns:
        df = df[df["unidade"].astype(str).str.lower() == args.unidade].copy()
        if df.empty:
            raise ValueError("Nenhuma linha encontrada para a unidade selecionada.")

    bairro_col = choose_bairro_col(df, args.bairro_col)
    if not bairro_col or bairro_col not in df.columns:
        raise ValueError("Coluna de bairro nao encontrada no CSV.")

    lat_col = "latitude_centro" if "latitude_centro" in df.columns else None
    lon_col = "longitude_centro" if "longitude_centro" in df.columns else None
    if not lat_col or not lon_col:
        raise ValueError("Colunas de latitude/longitude nao encontradas.")

    df["renda_media_num"] = df["renda_media"].apply(parse_renda_seguro)
    for col in ("v01031_0_4anos", "v01032_5_9anos", "populacao_total"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df["criancas_0_9"] = df["v01031_0_4anos"].fillna(0) + df["v01032_5_9anos"].fillna(0)
    df["renda_atualizada_2025"] = df["renda_media_num"] * args.inflation_factor
    df["distancia_km"] = haversine_km(
        df[lat_col], df[lon_col], args.escola_lat, args.escola_lon
    )

    grouped = (
        df.groupby(bairro_col, dropna=False)
        .agg(
            pontos=(bairro_col, "size"),
            lat_mediana=(lat_col, "median"),
            lon_mediana=(lon_col, "median"),
            distancia_mediana_km=("distancia_km", "median"),
            renda_mediana_2025=("renda_atualizada_2025", "median"),
            criancas_0_9_mediana=("criancas_0_9", "median"),
            populacao_mediana=("populacao_total", "median"),
        )
        .reset_index()
    )
    grouped = grouped.rename(columns={bairro_col: "Bairro"})
    grouped["score_trafego_2025"] = (
        grouped["renda_mediana_2025"] * grouped["criancas_0_9_mediana"]
    )

    if "cluster" in df.columns:
        cluster_stats = (
            df.groupby(bairro_col)["cluster"].apply(mode_with_share).unstack().reset_index()
        )
        cluster_stats = cluster_stats.rename(columns={bairro_col: "Bairro"})
        grouped = grouped.merge(cluster_stats, on="Bairro", how="left")

    grouped = grouped.sort_values("score_trafego_2025", ascending=False)
    grouped["rank_score_trafego"] = (
        grouped["score_trafego_2025"]
        .rank(ascending=False, method="min")
        .astype("Int64")
    )
    grouped["rank_proximidade"] = (
        grouped["distancia_mediana_km"]
        .rank(ascending=True, method="min")
        .astype("Int64")
    )

    score_min = grouped["score_trafego_2025"].min()
    score_max = grouped["score_trafego_2025"].max()
    if pd.notna(score_min) and pd.notna(score_max) and score_max > score_min:
        grouped["score_index_0_100"] = (
            (grouped["score_trafego_2025"] - score_min)
            / (score_max - score_min)
            * 100
        )
    else:
        grouped["score_index_0_100"] = np.nan

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    unidade_label = "Morumbi" if args.unidade == "morumbi" else "Chacara"
    output_csv = output_dir / f"{args.unidade}_score_bairros_latlon_2025.csv"
    grouped.to_csv(output_csv, index=False, encoding="utf-8-sig")

    filtered = grouped[grouped["pontos"] >= args.min_pontos].copy()
    proximos = filtered.sort_values("distancia_mediana_km").head(args.top_n)
    top_score = filtered.sort_values("score_trafego_2025", ascending=False).head(
        args.top_n
    )
    top_videos = proximos.sort_values("score_trafego_2025", ascending=False).head(
        args.top_videos
    )

    report_path = output_dir / f"{args.unidade}_bairros_proximos_relatorio.md"
    html_path = output_dir / f"{args.unidade}_bairros_proximos_relatorio.html"

    def build_table_view(
        df_view: pd.DataFrame, include_cluster: bool
    ) -> pd.DataFrame:
        cols = [
            "Bairro",
            "distancia_mediana_km",
            "score_trafego_2025",
            "renda_mediana_2025",
            "criancas_0_9_mediana",
            "populacao_mediana",
            "pontos",
        ]
        if include_cluster:
            cols += ["cluster_predominante", "cluster_share"]
        view = df_view[cols].copy()
        view["distancia_mediana_km"] = view["distancia_mediana_km"].apply(fmt_km)
        view["score_trafego_2025"] = view["score_trafego_2025"].apply(fmt_num)
        view["renda_mediana_2025"] = view["renda_mediana_2025"].apply(fmt_money)
        view["criancas_0_9_mediana"] = view["criancas_0_9_mediana"].apply(fmt_num)
        view["populacao_mediana"] = view["populacao_mediana"].apply(fmt_num, decimals=0)
        if include_cluster:
            view["cluster_predominante"] = view["cluster_predominante"].apply(fmt_num, decimals=0)
            view["cluster_share"] = view["cluster_share"].apply(fmt_num)
        return view

    def render_table_md(df_view: pd.DataFrame, include_cluster: bool) -> str:
        view = build_table_view(df_view, include_cluster)
        header = "| " + " | ".join(view.columns) + " |"
        sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
        rows = ["| " + " | ".join(map(str, row)) + " |" for row in view.values.tolist()]
        return "\n".join([header, sep] + rows)

    def render_table_html(df_view: pd.DataFrame, include_cluster: bool) -> str:
        view = build_table_view(df_view, include_cluster)
        rename_map = {
            "distancia_mediana_km": "Distancia",
            "score_trafego_2025": "Score",
            "renda_mediana_2025": "Renda mediana",
            "criancas_0_9_mediana": "Criancas 0-9",
            "populacao_mediana": "Populacao mediana",
            "pontos": "Pontos",
            "cluster_predominante": "Cluster predominante",
            "cluster_share": "Cluster share",
        }
        view = view.rename(columns=rename_map)
        return view.to_html(index=False, escape=True)

    include_cluster = "cluster_predominante" in grouped.columns
    report_lines = [
        f"# Relatorio de bairros proximos - {unidade_label} (lat/lon)",
        "",
        "Base: {}".format(input_path.as_posix()),
        f"Escola (lat, lon): {args.escola_lat}, {args.escola_lon}",
        f"Inflacao aplicada: {args.inflation_factor}",
        f"Minimo de pontos por bairro: {args.min_pontos}",
        f"Coluna de bairro usada: {bairro_col}",
        "",
        "Formula do score (nivel bairro): renda_mediana_2025 * criancas_0_9_mediana",
        "",
        "## Bairros mais proximos (por distancia mediana)",
        render_table_md(proximos, include_cluster),
        "",
        "## Top score trafego (bairros com mais potencial)",
        render_table_md(top_score, include_cluster),
        "",
        "## Sugestao para videos (proximos + alto score)",
        render_table_md(top_videos, include_cluster),
        "",
        "Observacao: o ranking usa mediana por bairro para reduzir ruido de outliers.",
    ]

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    html_lines = [
        "<!DOCTYPE html>",
        "<html lang=\"pt-br\">",
        "<head>",
        "  <meta charset=\"utf-8\" />",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />",
        f"  <title>Relatorio de bairros proximos - {unidade_label}</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 24px; color: #222; }",
        "    h1, h2 { margin: 0 0 12px 0; }",
        "    p { margin: 6px 0; }",
        "    table { border-collapse: collapse; width: 100%; margin: 8px 0 24px 0; }",
        "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
        "    th { background: #f3f3f3; }",
        "    .meta { color: #555; font-size: 14px; }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>Relatorio de bairros proximos - {unidade_label} (lat/lon)</h1>",
        f"  <p class=\"meta\"><strong>Base:</strong> {input_path.as_posix()}</p>",
        f"  <p class=\"meta\"><strong>Escola (lat, lon):</strong> {args.escola_lat}, {args.escola_lon}</p>",
        f"  <p class=\"meta\"><strong>Inflacao aplicada:</strong> {args.inflation_factor}</p>",
        f"  <p class=\"meta\"><strong>Minimo de pontos por bairro:</strong> {args.min_pontos}</p>",
        f"  <p class=\"meta\"><strong>Coluna de bairro usada:</strong> {bairro_col}</p>",
        "  <p class=\"meta\"><strong>Formula do score:</strong> renda_mediana_2025 * criancas_0_9_mediana</p>",
        "  <h2>Bairros mais proximos (por distancia mediana)</h2>",
        render_table_html(proximos, include_cluster),
        "  <h2>Top score trafego (bairros com mais potencial)</h2>",
        render_table_html(top_score, include_cluster),
        "  <h2>Sugestao para videos (proximos + alto score)</h2>",
        render_table_html(top_videos, include_cluster),
        "  <p class=\"meta\">Observacao: o ranking usa mediana por bairro para reduzir ruido de outliers.</p>",
        "</body>",
        "</html>",
    ]
    html_path.write_text("\n".join(html_lines), encoding="utf-8")

    print(f"Arquivo gerado: {output_csv}")
    print(f"Relatorio gerado: {report_path}")
    print(f"Relatorio HTML gerado: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
