#!/usr/bin/env python3
"""
Preenche CEP, Bairro, Cidade, UF e Logradouro via Nominatim/OSM a partir de latitude/longitude.
Uso:
  pip install pandas requests
  python preencher_endereco_por_latlon.py "arquivo.csv" [--saida out.csv] [--sleep 1.2] [--useragent "SeuApp/1.0 (email@dominio.com)"] [--verbose] [--log-every 25]
"""
import argparse, time, sys, requests, pandas as pd
from pathlib import Path

LAT_CANDIDATES = ["latitude", "lat", "Latitude", "LATITUDE", "Lat"]
LON_CANDIDATES = ["longitude", "lon", "lng", "Longitude", "LONGITUDE", "Long", "LON", "LNG"]

def detect_column(df, candidates, partial_keys=None):
    if partial_keys is None: partial_keys = []
    for c in df.columns:
        if str(c).strip() in candidates or str(c).lower().strip() in [x.lower() for x in candidates]:
            return c
    for c in df.columns:
        low = str(c).lower().strip()
        for pk in partial_keys:
            if pk in low: return c
    return None

def detect_lat_lon(df):
    lat_col = detect_column(df, LAT_CANDIDATES, ["lat"])
    longitude_centro = detect_column(df, LON_CANDIDATES, ["lon","lng","long"])
    return lat_col, longitude_centro

def reverse_geocode(lat, lon, ua):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"format": "jsonv2", "lat": lat, "lon": lon, "addressdetails": 1}
    headers = {"User-Agent": ua}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    js = r.json()
    addr = js.get("address", {}) if isinstance(js, dict) else {}
    return {
        "CEP": addr.get("postcode") or addr.get("postalcode") or "",
        "Bairro": addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district") or "",
        "Cidade": addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or addr.get("county") or "",
        "UF": addr.get("state") or "",
        "Logradouro": addr.get("road") or ""
    }

def ensure_columns(df, cols):
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo")
    ap.add_argument("--saida")
    ap.add_argument("--sleep", type=float, default=1.2)
    ap.add_argument("--useragent", default="Endereco-Filler/1.0 (contact@example.com)")
    ap.add_argument("--verbose", action="store_true", help="Mostra progresso no terminal")
    ap.add_argument("--log-every", type=int, default=25, help="Frequência de logs (linhas)")
    args = ap.parse_args()

    inp = Path(args.arquivo)
    if not inp.exists():
        print("Arquivo não encontrado", file=sys.stderr); sys.exit(1)

    # read
    last_err=None; df=None
    for enc in ["utf-8","utf-8-sig","latin-1"]:
        try:
            df = pd.read_csv(inp, encoding=enc); break
        except Exception as e: last_err=e
    if df is None: raise last_err

    lat_col, longitude_centro = detect_lat_lon(df)
    if not lat_col or not longitude_centro:
        print("Não foi possível detectar colunas de latitude/longitude.", file=sys.stderr); sys.exit(2)

    ensure_columns(df, ["CEP","Bairro","Cidade","UF","Logradouro"])

    filled=0; total=len(df)
    processadas=0; start=time.time()

    for idx,row in df.iterrows():
        processadas += 1

        if str(row.get("CEP","")).strip():
            if args.verbose and (processadas % args.log_every == 0):
                elapsed = time.time()-start
                rate = processadas/max(elapsed,1e-9)
                eta = (total-processadas)/max(rate,1e-9)
                print(f"[{processadas}/{total}] skip | filled={filled} | elapsed={elapsed:,.0f}s | ETA≈{eta:,.0f}s", flush=True)
            continue

        try:
            lat=float(row[lat_col]); lon=float(row[longitude_centro])
        except Exception:
            if args.verbose and (processadas % args.log_every == 0):
                elapsed = time.time()-start
                rate = processadas/max(elapsed,1e-9)
                eta = (total-processadas)/max(rate,1e-9)
                print(f"[{processadas}/{total}] inválido (lat/lon) | filled={filled} | elapsed={elapsed:,.0f}s | ETA≈{eta:,.0f}s", flush=True)
            continue

        try:
            info = reverse_geocode(lat, lon, args.useragent)
            for k,v in info.items():
                if v and (str(row.get(k,'')).strip()== ''):
                    df.at[idx,k]=v
            if info.get("CEP"): filled+=1
        except requests.HTTPError:
            time.sleep(max(args.sleep*2, 2.0))
        except Exception:
            pass

        if args.verbose and (processadas % args.log_every == 0 or processadas == total):
            elapsed = time.time()-start
            rate = processadas/max(elapsed,1e-9)
            eta = (total-processadas)/max(rate,1e-9)
            ultimo = df.at[idx,"CEP"] if "CEP" in df.columns else ""
            print(f"[{processadas}/{total}] last_CEP='{ultimo}' | filled={filled} | elapsed={elapsed:,.0f}s | ETA≈{eta:,.0f}s",
                  flush=True)

        time.sleep(args.sleep)

    out = Path(args.saida) if args.saida else inp.with_name(inp.stem + "_com_enderecos.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    dur = time.time()-start
    print(f"OK: CEPs preenchidos em {filled}/{total}. Arquivo salvo em: {out} | tempo total: {dur:,.0f}s")

if __name__ == "__main__":
    main()
