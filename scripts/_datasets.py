from __future__ import annotations

from pathlib import Path

STAGES = ("raw", "coords", "principal")
UNIDADES = ("morumbi", "chacara")

BASE_PATHS = {
    "raw": "data/base_bruta.csv",
    "coords": "data/base_coords_corrigidas.csv",
    "principal": "data/base_principal.csv",
}

MIRROR_DIR = "data/filling_Ceps"
MIRROR_FILES = {
    "morumbi": "Elvira Brandão Morumbi - Euvira Brandão Dados ADS_coords_corrigidas_com_enderecos.csv",
    "chacara": "Elvira - Chacara - INEP 35107700 Dados ADS_coords_corrigidas_com_enderecos.csv",
}

ANALISES_DIR = "analises"
ANALISE_1_DIR = f"{ANALISES_DIR}/analise_1.0"
ANALISE_2_DIR = f"{ANALISES_DIR}/analise_2.0"
ANALISE_3_DIR = f"{ANALISES_DIR}/analise_3.0"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_base_path(stage: str, root: Path | None = None, must_exist: bool = True) -> Path | None:
    if stage not in STAGES:
        raise ValueError(f"Stage invalido: {stage}")
    root = root or project_root()
    path = root / BASE_PATHS[stage]
    if must_exist and not path.exists():
        return None
    return path


def resolve_mirror_path(unidade: str, root: Path | None = None, must_exist: bool = True) -> Path | None:
    if unidade not in UNIDADES:
        raise ValueError(f"Unidade invalida: {unidade}")
    root = root or project_root()
    path = root / MIRROR_DIR / MIRROR_FILES[unidade]
    if must_exist and not path.exists():
        return None
    return path
