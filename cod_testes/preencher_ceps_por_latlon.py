#!/usr/bin/env python3
import argparse, time, sys, requests, pandas as pd
from pathlib import Path
LAT_CANDIDATES=["latitude","lat","Latitude","LATITUDE","Lat"]
LON_CANDIDATES=["longitude","lon","lng","Longitude","LONGITUDE","Long","LON","LNG"]
def detect(df, cands, partials=None):
    if partials is None: partials=[]
    for c in df.columns:
        if str(c).strip() in cands or str(c).lower().strip() in [x.lower() for x in cands]: return c
    for c in df.columns:
        low=str(c).lower().strip()
        for p in partials:
            if p in low: return c
    return None
def rev(lat,lon,ua):
    r=requests.get("https://nominatim.openstreetmap.org/reverse",
                   params={"format":"jsonv2","lat":lat,"lon":lon,"addressdetails":1},
                   headers={"User-Agent":ua}, timeout=20)
    r.raise_for_status()
    a=(r.json() or {}).get("address",{})
    return a.get("postcode") or a.get("postalcode") or ""
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("arquivo"); ap.add_argument("--saida")
    ap.add_argument("--sleep",type=float,default=1.2)
    ap.add_argument("--useragent",default="CEP-Filler/1.0 (contact@example.com)")
    args=ap.parse_args()
    inp=Path(args.arquivo)
    if not inp.exists(): print("Arquivo não encontrado", file=sys.stderr); sys.exit(1)
    df=None; last=None
    for enc in ["utf-8","utf-8-sig","latin-1"]:
        try: df=pd.read_csv(inp, encoding=enc); break
        except Exception as e: last=e
    if df is None: raise last
    if "CEP" not in df.columns: df["CEP"]=""
    latitude_centro=detect(df,LAT_CANDIDATES,["lat"]); longitude_centro=detect(df,LON_CANDIDATES,["lon","lng","long"])
    if not latitude_centro or not longitude_centro: print("Não foi possível detectar colunas de latitude/longitude.", file=sys.stderr); sys.exit(2)
    filled=0; total=len(df)
    for i,row in df.iterrows():
        if str(row.get("CEP","")).strip(): continue
        try: lat=float(row[latitude_centro]); lon=float(row[longitude_centro])
        except Exception: continue
        try:
            cep=rev(lat,lon,args.useragent)
            if cep: df.at[i,"CEP"]=cep; filled+=1
        except requests.HTTPError: time.sleep(max(args.sleep*2,2.0))
        except Exception: pass
        time.sleep(args.sleep)
    out=Path(args.saida) if args.saida else inp.with_name(inp.stem+"_com_CEPs.csv")
    df.to_csv(out,index=False,encoding="utf-8-sig")
    print(f"OK: {filled}/{total} CEPs preenchidos -> {out}")
if __name__=="__main__": main()
