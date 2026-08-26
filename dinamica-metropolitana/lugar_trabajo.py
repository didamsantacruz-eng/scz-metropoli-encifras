# -*- coding: utf-8 -*-
"""`p52_mov`: la única granularidad de LUGAR que el censo agrega al municipio.

Distingue **1 dentro o junto a la vivienda** de **2 fuera de la vivienda, pero en
el mismo municipio**. El motor de flujos colapsa las dos en «se queda», así que
el trabajo a domicilio hoy es invisible — y son los que NO generan viaje.

No está en el parquet: hay que ir al CSV.
"""
import json
import pathlib
import sys

import pandas as pd

RAW = pathlib.Path(r"C:\Users\HP\cpv2024")
REPO = pathlib.Path(r"C:\Users\HP\OneDrive\Desktop\Proyectos\scz-metropolitana-gobernacion")
SAL = pathlib.Path(__file__).resolve().parent / "lugar_trabajo.json"

N9 = {m["cod_ine"]: m["nombre"] for m in
      json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))}
dic = json.loads((RAW / "diccionario.json").read_text(encoding="utf-8"))["PERSONA"]
ET_MOV = dic["p52_mov"]["categorias"]
ET_RAMA = dic["act_eco_2d_13"]["categorias"]
CORTO = {str(int(k)): v.split(". ", 1)[-1].split(";")[0].split(",")[0].strip()
         for k, v in ET_RAMA.items() if k.isdigit()}

COLS = ["idep", "iprov", "imun", "p26_edad", "p52_mov", "condact_13",
        "act_eco_2d_13", "p25_sexo", "nivel_edu", "aestudio", "p50_catocu_13"]
tro, n = [], 0
for ch in pd.read_csv(RAW / "Persona_CPV-2024.csv", sep=";", usecols=COLS,
                      dtype=str, chunksize=600_000, low_memory=False):
    n += len(ch)
    ch["cod_ine"] = ch.idep.str.zfill(2) + ch.iprov.str.zfill(2) + ch.imun.str.zfill(2)
    tro.append(ch[ch.cod_ine.isin(N9)])
    print(f"  {n:,}", end="\r", file=sys.stderr, flush=True)
r = pd.concat(tro, ignore_index=True)
del tro
r["edad"] = pd.to_numeric(r.p26_edad, errors="coerce")
ocu = r[r.condact_13 == "1"]          # ocupados
print(f"\nocupados en los 9: {len(ocu):,}")

out = {"etiquetas_mov": ET_MOV, "region": {}, "por_municipio": {}}

v = ocu.p52_mov.value_counts()
out["region"]["reparto"] = {ET_MOV.get(str(k), str(k)): int(x) for k, x in v.items()}
print("\n== DÓNDE TRABAJA cada ocupado de la región ==")
for k, x in v.items():
    print(f"   {ET_MOV.get(str(k), str(k))[:52]:54s} {x:>9,}  {100*x/len(ocu):5.1f}%")

casa = ocu[ocu.p52_mov == "1"]
print(f"\n== los {len(casa):,} que trabajan EN o JUNTO A su vivienda ==")
a15 = casa[casa.edad >= 15]
print(f"   mujeres {100*(casa.p25_sexo == '2').mean():.1f}%  ·  "
      f"edad mediana {casa.edad.median():.0f}  ·  "
      f"años de estudio {pd.to_numeric(a15.aestudio, errors='coerce').mean():.2f}  ·  "
      f"superior {100*(a15.nivel_edu == '4').mean():.1f}%")
out["region"]["en_casa"] = {
    "n": int(len(casa)),
    "pct_mujer": round(100 * (casa.p25_sexo == "2").mean(), 1),
    "edad_mediana": float(casa.edad.median()),
    "anios_estudio": round(float(pd.to_numeric(a15.aestudio, errors="coerce").mean()), 2),
    "pct_superior": round(100 * (a15.nivel_edu == "4").mean(), 1),
    "rama": {CORTO.get(str(int(float(k))), str(k)): round(100 * x, 1)
             for k, x in casa.act_eco_2d_13.dropna().value_counts(normalize=True).head(8).items()},
    "catocu": {dic["p50_catocu_13"]["categorias"].get(str(k), str(k)): round(100 * x, 1)
               for k, x in casa.p50_catocu_13.dropna().value_counts(normalize=True).items()},
}
print("\n   a qué se dedica el que trabaja en su casa:")
for k, x in list(out["region"]["en_casa"]["rama"].items())[:6]:
    print(f"     {k[:46]:48s} {x:5.1f}%")
print("\n   y en qué condición:")
for k, x in out["region"]["en_casa"]["catocu"].items():
    print(f"     {k[:46]:48s} {x:5.1f}%")

print("\n== por municipio ==")
print(f"   {'municipio':26s} {'ocupados':>9s} {'en casa':>9s} {'%':>6s} {'mismo mun':>10s} {'otro mun':>9s}")
for c in sorted(N9, key=lambda x: N9[x]):
    g = ocu[ocu.cod_ine == c]
    d1 = int((g.p52_mov == "1").sum()); d2 = int((g.p52_mov == "2").sum())
    d3 = int((g.p52_mov == "3").sum())
    out["por_municipio"][c] = {"nombre": N9[c], "ocupados": int(len(g)),
                               "en_la_vivienda": d1, "mismo_municipio_fuera": d2,
                               "otro_municipio": d3,
                               "pct_en_la_vivienda": round(100 * d1 / max(len(g), 1), 1)}
    print(f"   {N9[c]:26s} {len(g):>9,} {d1:>9,} {100*d1/max(len(g),1):>5.1f}% {d2:>10,} {d3:>9,}")

SAL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n->", SAL.name)
