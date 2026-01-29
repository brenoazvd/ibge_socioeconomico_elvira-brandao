from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from _datasets import (
    ANALISE_1_DIR,
    ANALISE_3_DIR,
    UNIDADES,
    project_root,
    resolve_base_path,
    resolve_mirror_path,
)

try:
    from scipy.spatial import cKDTree
except Exception:  # pragma: no cover - optional dependency
    cKDTree = None


DEFAULT_URL = (
    "https://raw.githubusercontent.com/geoinfo-smdu/cadastro-fiscal/"
    "master/antigo_arrumar/resultados/sao-paulo-address-IPTU-2021.csv.zip"
)

LAT_CANDIDATES = ["latitude_centro", "latitude", "lat", "LATITUDE", "Latitude", "Lat"]
LON_CANDIDATES = ["longitude_centro", "longitude", "lon", "lng", "LONGITUDE", "Longitude", "Long", "LON", "LNG"]


def read_csv_smart(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1")


def detect_column(df: pd.DataFrame, candidates: list[str], partial_keys: list[str] | None = None) -> str | None:
    partial_keys = partial_keys or []
    candidate_set = {c.lower().strip() for c in candidates}
    for col in df.columns:
        if str(col).strip() in candidates or str(col).lower().strip() in candidate_set:
            return str(col)
    for col in df.columns:
        low = str(col).lower().strip()
        for key in partial_keys:
            if key in low:
                return str(col)
    return None


def ensure_columns(df: pd.DataFrame, cols: list[str]) -> None:
    for col in cols:
        if col not in df.columns:
            df[col] = ""


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{path.stem}_backup_{ts}{path.suffix}"
    path.replace(backup)
    return backup


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def load_openaddresses(path: Path) -> pd.DataFrame:
    usecols = ["longitude", "latitude", "logradouro", "numero", "cep"]
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("Zip file has no CSV inside.")
            with zf.open(names[0]) as fh:
                return pd.read_csv(fh, usecols=usecols, low_memory=False)
    return pd.read_csv(path, usecols=usecols, low_memory=False)


def format_cep(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = "".join(ch for ch in str(value) if ch.isdigit())
    if len(s) == 8:
        return f"{s[:5]}-{s[5:]}"
    return s


def normalize_cep_digits(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def load_json_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_json_cache(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_viacep(
    session: requests.Session,
    cep_digits: str,
    cache: dict[str, Any],
    sleep_s: float,
) -> dict[str, Any] | None:
    if not cep_digits or len(cep_digits) != 8:
        return None
    if cep_digits in cache:
        cached = cache.get(cep_digits)
        if isinstance(cached, dict) and cached.get("erro"):
            return None
        return cached

    url = f"https://viacep.com.br/ws/{cep_digits}/json/"
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        cache[cep_digits] = {"erro": True}
        return None

    if isinstance(data, dict) and data.get("erro"):
        cache[cep_digits] = {"erro": True}
        return None

    cache[cep_digits] = data
    if sleep_s > 0:
        time.sleep(sleep_s)
    return data


def build_tree(df_addr: pd.DataFrame) -> tuple[Any, np.ndarray]:
    if cKDTree is None:
        raise RuntimeError("scipy is required (pip install scipy).")
    lat = pd.to_numeric(df_addr["latitude"], errors="coerce")
    lon = pd.to_numeric(df_addr["longitude"], errors="coerce")
    mask = lat.notna() & lon.notna()
    lat = lat[mask].to_numpy(dtype=float)
    lon = lon[mask].to_numpy(dtype=float)
    scale = np.cos(np.deg2rad(np.nanmean(lat))) if len(lat) else 1.0
    coords = np.column_stack((lat, lon * scale))
    return cKDTree(coords), mask.to_numpy(), scale


def update_from_viacep(
    df: pd.DataFrame,
    cache: dict[str, Any],
    overwrite: bool,
    include_logradouro: bool,
    sleep_s: float,
    backup_bairro: bool,
    indices: list[int] | None = None,
) -> int:
    ensure_columns(df, ["CEP", "Bairro", "Cidade", "UF"])
    if include_logradouro:
        ensure_columns(df, ["Logradouro"])
    if backup_bairro:
        if "Bairro_original" not in df.columns:
            df["Bairro_original"] = df["Bairro"]

    target_indices = indices if indices is not None else df.index.tolist()
    ceps = df.loc[target_indices, "CEP"].fillna("").astype(str).map(normalize_cep_digits)
    unique_ceps = sorted({c for c in ceps if len(c) == 8})
    if not unique_ceps:
        return 0

    session = requests.Session()
    resolved: dict[str, dict[str, Any]] = {}
    for cep_digits in unique_ceps:
        data = fetch_viacep(session, cep_digits, cache, sleep_s)
        if isinstance(data, dict):
            resolved[cep_digits] = data

    updated = 0
    for idx in target_indices:
        row = df.loc[idx]
        cep_digits = normalize_cep_digits(row.get("CEP", ""))
        if len(cep_digits) != 8:
            continue
        data = resolved.get(cep_digits)
        if not data:
            continue

        bairro = str(data.get("bairro", "") or "").strip()
        cidade = str(data.get("localidade", "") or "").strip()
        uf = str(data.get("uf", "") or "").strip()
        logradouro = str(data.get("logradouro", "") or "").strip()

        if bairro and (overwrite or not str(row.get("Bairro", "")).strip()):
            df.at[idx, "Bairro"] = bairro
            updated += 1
        if cidade and (overwrite or not str(row.get("Cidade", "")).strip()):
            df.at[idx, "Cidade"] = cidade
        if uf and (overwrite or not str(row.get("UF", "")).strip()):
            df.at[idx, "UF"] = uf
        if include_logradouro and logradouro and (overwrite or not str(row.get("Logradouro", "")).strip()):
            df.at[idx, "Logradouro"] = logradouro

    return updated


def sync_mirror(
    df: pd.DataFrame,
    base_dir: Path,
    no_backup: bool,
    no_sync: bool,
) -> None:
    if no_sync:
        return
    if "unidade" not in df.columns:
        print("Coluna 'unidade' nao encontrada; skip mirror.")
        return

    for unidade in UNIDADES:
        mirror_path = resolve_mirror_path(unidade, root=base_dir, must_exist=False)
        if not mirror_path:
            continue
        df_unit = df[df["unidade"] == unidade].copy()
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        if not no_backup and mirror_path.exists():
            backup = backup_file(mirror_path)
            if backup:
                print(f"Backup criado (mirror): {backup}")
        df_unit.to_csv(mirror_path, index=False, encoding="utf-8-sig")
        print(f"Mirror atualizado: {mirror_path}")


def update_clusters(
    clusters_path: Path,
    df_src: pd.DataFrame,
    unidade: str | None = None,
) -> None:
    if not clusters_path.exists():
        print(f"Cluster file not found: {clusters_path}")
        return
    df_cluster = read_csv_smart(clusters_path)
    if unidade and "unidade" in df_src.columns:
        df_src = df_src[df_src["unidade"] == unidade].copy()
    if df_src.empty:
        print(f"Nenhum dado para atualizar clusters: {clusters_path}")
        return
    if "id" not in df_src.columns:
        print("Source file has no id column; skip clusters update.")
        return

    cols = ["id", "CEP", "Bairro", "Cidade", "UF", "Logradouro"]
    cols = [c for c in cols if c in df_src.columns]
    df_new = df_src[cols].copy()
    df_merged = df_cluster.merge(df_new, on="id", how="left", suffixes=("", "_new"))

    for col in cols:
        if col == "id":
            continue
        new_col = f"{col}_new"
        if new_col in df_merged.columns:
            df_merged[col] = df_merged[new_col].where(
                df_merged[new_col].notna() & (df_merged[new_col].astype(str).str.strip() != ""),
                df_merged.get(col, ""),
            )
            df_merged = df_merged.drop(columns=[new_col])

    df_merged.to_csv(clusters_path, index=False, encoding="utf-8-sig")
    print(f"Clusters updated: {clusters_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Atualiza CEP/logradouro via OpenAddresses e bairro via ViaCEP."
    )
    parser.add_argument("--data", help="Caminho do CSV/ZIP do OpenAddresses.")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL para download do OpenAddresses.")
    parser.add_argument("--download", action="store_true", help="Baixa o arquivo se nao existir.")
    parser.add_argument(
        "--input",
        help="CSV base com lat/lon corrigidos (default: data/base_coords_corrigidas.csv).",
    )
    parser.add_argument(
        "--output",
        help="CSV de saida (default: data/base_principal.csv).",
    )
    parser.add_argument(
        "--unidade",
        choices=[*UNIDADES, "all"],
        default="all",
        help="Atualiza apenas esta unidade (default: all).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Sobrescreve CEP/Logradouro existentes.")
    parser.add_argument("--include-number", action="store_true", help="Inclui numero no logradouro.")
    parser.add_argument("--k", type=int, default=5, help="Numero de vizinhos para buscar CEP valido.")
    parser.add_argument(
        "--max-distance-m",
        type=float,
        default=1000.0,
        help="Distancia maxima (metros) para aceitar CEP/logradouro. Use 0 para desativar.",
    )
    parser.add_argument("--via-cep", action="store_true", help="Busca Bairro/Cidade/UF via ViaCEP usando o CEP.")
    parser.add_argument("--via-cep-overwrite", action="store_true", help="Sobrescreve campos preenchidos pelo ViaCEP.")
    parser.add_argument("--via-cep-logradouro", action="store_true", help="Atualiza logradouro com ViaCEP (opcional).")
    parser.add_argument("--via-cep-cache", default="data/cache/viacep_cache.json")
    parser.add_argument("--via-cep-sleep", type=float, default=0.2, help="Pausa entre chamadas ao ViaCEP.")
    parser.add_argument("--backup-bairro", action="store_true", help="Salva Bairro atual em Bairro_original antes do ViaCEP.")
    parser.add_argument(
        "--clear-unused-bairro-cols",
        action="store_true",
        help="Limpa colunas Bairro_osm/Bairro_geosampa para evitar confusao.",
    )
    parser.add_argument("--no-backup", action="store_true", help="Nao cria backup dos CSVs.")
    parser.add_argument(
        "--no-sync-mirror",
        action="store_true",
        help="Nao sincroniza dados para data/filling_Ceps.",
    )
    parser.add_argument("--no-sync-legacy", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-update-clusters", action="store_true", help="Nao atualiza clusters da analise 1.0.")
    parser.add_argument("--no-regenerate-analise-3", action="store_true", help="Nao roda a analise 3.0.")
    args = parser.parse_args()

    base_dir = project_root()

    def resolve_arg_path(value: str | None) -> Path | None:
        if not value:
            return None
        path = Path(value)
        return path if path.is_absolute() else base_dir / path

    data_path = resolve_arg_path(args.data) if args.data else (
        base_dir / "data" / "cache" / "openaddresses" / "sao-paulo-address-IPTU-2021.csv.zip"
    )

    if not data_path.exists():
        if args.download or args.data is None:
            print(f"Downloading OpenAddresses data to {data_path}...")
            download_file(args.url, data_path)
        else:
            print(f"Data file not found: {data_path}", file=sys.stderr)
            return 2

    input_path = resolve_arg_path(args.input) if args.input else resolve_base_path("coords", root=base_dir)
    if not input_path or not input_path.exists():
        print("Arquivo de entrada nao encontrado.", file=sys.stderr)
        return 2

    output_path = resolve_arg_path(args.output) if args.output else resolve_base_path(
        "principal", root=base_dir, must_exist=False
    )
    if not output_path:
        print("Arquivo de saida nao configurado.", file=sys.stderr)
        return 2

    df_addr = load_openaddresses(data_path)
    tree, mask, scale = build_tree(df_addr)
    df_addr = df_addr.loc[mask].reset_index(drop=True)

    # Prepare address fields
    df_addr["cep"] = df_addr["cep"].apply(format_cep)
    df_addr["logradouro"] = df_addr["logradouro"].astype(str).str.strip()
    if args.include_number:
        df_addr["numero"] = df_addr["numero"].astype(str).str.strip()
        has_num = df_addr["numero"].ne("") & df_addr["numero"].ne("nan")
        df_addr.loc[has_num, "logradouro"] = df_addr.loc[has_num, "logradouro"] + ", " + df_addr.loc[has_num, "numero"]

    viacep_cache: dict[str, Any] = {}
    viacep_cache_path = None
    if args.via_cep:
        viacep_cache_path = resolve_arg_path(args.via_cep_cache)
        if viacep_cache_path is None:
            print("Caminho do cache ViaCEP invalido.", file=sys.stderr)
            return 2
        viacep_cache = load_json_cache(viacep_cache_path)

    df = read_csv_smart(input_path)
    lat_col = detect_column(df, LAT_CANDIDATES, ["lat"])
    lon_col = detect_column(df, LON_CANDIDATES, ["lon", "lng", "long"])
    if not lat_col or not lon_col:
        print("Lat/lon nao encontrados no arquivo de entrada.", file=sys.stderr)
        return 2

    ensure_columns(df, ["CEP", "Logradouro"])

    unit_mask = pd.Series(True, index=df.index)
    if args.unidade != "all":
        if "unidade" not in df.columns:
            print("Coluna 'unidade' nao encontrada para filtrar.", file=sys.stderr)
            return 2
        unit_mask = df["unidade"].astype(str).str.lower().eq(args.unidade)

    if not args.no_backup and output_path.exists():
        backup = backup_file(output_path)
        if backup:
            print(f"Backup criado: {backup}")

    lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=float)
    lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=float)
    coords = np.column_stack((lat, lon * scale))

    distances, indices = tree.query(coords, k=min(args.k, len(df_addr)))
    if len(indices.shape) == 1:
        indices = indices[:, None]
        distances = distances[:, None]

    updated = 0
    max_distance_m = args.max_distance_m
    for i, (idx, row) in enumerate(df.iterrows()):
        if not unit_mask.loc[idx]:
            continue
        if np.isnan(lat[i]) or np.isnan(lon[i]):
            continue
        if not args.overwrite:
            if str(row.get("CEP", "")).strip() and str(row.get("Logradouro", "")).strip():
                continue

        cand_indices = indices[i]
        cand_distances = distances[i]
        cep_val = ""
        log_val = ""
        for cand_idx, dist in zip(cand_indices, cand_distances):
            if cand_idx >= len(df_addr):
                continue
            if max_distance_m > 0 and dist * 111_000 > max_distance_m:
                break
            cep_val = df_addr.at[cand_idx, "cep"]
            log_val = df_addr.at[cand_idx, "logradouro"]
            if cep_val or log_val:
                break

        if not cep_val and not log_val:
            continue

        if args.overwrite or not str(row.get("CEP", "")).strip():
            df.at[idx, "CEP"] = cep_val
        if args.overwrite or not str(row.get("Logradouro", "")).strip():
            df.at[idx, "Logradouro"] = log_val
        updated += 1

    if args.via_cep:
        target_indices = df.index[unit_mask].tolist()
        updated_via = update_from_viacep(
            df,
            cache=viacep_cache,
            overwrite=args.via_cep_overwrite,
            include_logradouro=args.via_cep_logradouro,
            sleep_s=args.via_cep_sleep,
            backup_bairro=args.backup_bairro,
            indices=target_indices,
        )
        if updated_via:
            print(f"ViaCEP atualizado: {updated_via} linhas em {output_path}")

    if args.clear_unused_bairro_cols:
        for col in ("Bairro_osm", "Bairro_geosampa"):
            if col in df.columns:
                df[col] = ""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"Arquivo atualizado: {output_path} (linhas atualizadas: {updated}) "
        f"| base: {input_path.name}"
    )

    sync_mirror(
        df,
        base_dir,
        no_backup=args.no_backup,
        no_sync=args.no_sync_mirror or args.no_sync_legacy,
    )

    if args.via_cep and viacep_cache_path:
        save_json_cache(viacep_cache_path, viacep_cache)

    if not args.no_update_clusters:
        for unidade in UNIDADES:
            if args.unidade != "all" and unidade != args.unidade:
                continue
            clusters_path = base_dir / ANALISE_1_DIR / f"{unidade}_clusters.csv"
            update_clusters(clusters_path, df, unidade=unidade)

    if not args.no_regenerate_analise_3:
        if args.unidade not in ("morumbi", "all"):
            print("Analise 3.0 nao executada (unidade filtrada).")
            print("Done.")
            return 0
        script_path = (
            base_dir
            / "analises"
            / "analise_3.0"
            / "analise_bairros_chacara_morumbi.py"
        )
        if script_path.exists():
            import subprocess

            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--unidade",
                    "morumbi",
                    "--output-dir",
                    str(base_dir / ANALISE_3_DIR),
                ],
                check=True,
            )
        else:
            print("Analise 3.0 script not found; skip.")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
