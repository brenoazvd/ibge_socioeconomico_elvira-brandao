#!/usr/bin/env python3
"""
Corrige colunas de latitude/longitude que perderam o ponto decimal (ex.: -2362866310850830 -> -23.62866310850830).

Uso:
  pip install pandas
  python corrigir_latlon.py "arquivo.csv" --latcol latitude_centro --loncol longitude_centro
  # (opcionais)
  # --deg-lat 2   -> quantos dígitos ficam antes do ponto na latitude (padrão 2, ex.: -23.x)
  # --deg-lon 2   -> quantos dígitos ficam antes do ponto na longitude (padrão 2, ex.: -46.x)
  # --saida "arquivo_corrigido.csv"

Observação: este script não chama nenhum serviço externo; ele apenas corrige o formato das coordenadas.
"""
import argparse
import re
import sys
from pathlib import Path
import pandas as pd

def clean_to_digits_and_sign(x: str) -> str:
    """Mantém apenas dígitos e o primeiro sinal '-' se existir."""
    s = str(x).strip()
    if not s:
        return ""
    # Remove tudo que não for dígito ou '-'
    s = re.sub(r"[^0-9\-]", "", s)
    # Se houver mais de um '-', mantém só o primeiro e remove os demais
    if s.count("-") > 1:
        first = s.find("-")
        s = "-" + s[first+1:].replace("-", "")
    return s

def insert_decimal(raw: str, deg_digits: int) -> str:
    """Insere ponto decimal após 'deg_digits' (excluindo o sinal)."""
    if not raw:
        return ""
    # Sinal opcional
    sign = "-" if raw.startswith("-") else ""
    body = raw[1:] if sign else raw
    if not body.isdigit():
        return ""  # inválido
    if len(body) <= deg_digits:
        # não há casas suficientes para inserir ponto; retorna como está
        return sign + body
    return f"{sign}{body[:deg_digits]}.{body[deg_digits:]}"

def fix_column(series, deg_digits: int):
    import pandas as pd
    fixed = []
    for val in series:
        cleaned = clean_to_digits_and_sign(val)
        fixed.append(insert_decimal(cleaned, deg_digits))
    return pd.to_numeric(pd.Series(fixed), errors="coerce")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo", help="CSV de entrada")
    ap.add_argument("--latcol", required=True, help="Nome da coluna de latitude (ex.: latitude_centro)")
    ap.add_argument("--loncol", required=True, help="Nome da coluna de longitude (ex.: longitude_centro)")
    ap.add_argument("--deg-lat", type=int, default=2, help="Dígitos antes do ponto na latitude (default: 2)")
    ap.add_argument("--deg-lon", type=int, default=2, help="Dígitos antes do ponto na longitude (default: 2)")
    ap.add_argument("--saida", help="CSV de saída (default: <arquivo>_coords_corrigidas.csv)")
    args = ap.parse_args()

    inp = Path(args.arquivo)
    if not inp.exists():
        print(f"Arquivo não encontrado: {inp}", file=sys.stderr)
        sys.exit(1)

    # Leitura com encodings comuns
    last_err = None
    df = None
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            import pandas as pd
            df = pd.read_csv(inp, encoding=enc)
            break
        except Exception as e:
            last_err = e
            df = None
    if df is None:
        raise last_err

    # Normaliza nomes de colunas (remove espaços)
    df.columns = df.columns.str.strip()

    if args.latcol not in df.columns or args.loncol not in df.columns:
        print(f"Colunas não encontradas. Disponíveis: {list(df.columns)}", file=sys.stderr)
        sys.exit(2)

    # Corrige
    df[args.latcol] = fix_column(df[args.latcol], args.deg_lat)
    df[args.loncol] = fix_column(df[args.loncol], args.deg_lon)

    # Salva
    out = Path(args.saida) if args.saida else inp.with_name(inp.stem + "_coords_corrigidas.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"OK: Coordenadas corrigidas salvas em: {out}")

if __name__ == "__main__":
    main()
