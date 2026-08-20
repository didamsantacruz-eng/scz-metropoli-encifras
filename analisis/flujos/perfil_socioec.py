# -*- coding: utf-8 -*-
"""¿Se puede ver el perfil SOCIOECONÓMICO de quien llegó, por origen?

Demostración, no promesa: se cruza Persona con Vivienda por `i00` + geografía y
se parte por de dónde venía hace 5 años. Tenencia de la vivienda, servicios y
bienes son lo que convierte un retrato demográfico en uno socioeconómico.
"""
import json
import pathlib
import sys

import pandas as pd

RAW = pathlib.Path(r"C:\Users\HP\cpv2024")
REPO = pathlib.Path(r"C:\Users\HP\OneDrive\Desktop\Proyectos\scz-metropolitana-gobernacion")
SAL = pathlib.Path(__file__).resolve().parent / "perfil_socioec.json"

N9 = {m["cod_ine"]: m["nombre"] for m in
      json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))}
dic = json.loads((RAW / "diccionario.json").read_text(encoding="utf-8"))["VIVIENDA"]


def cat(var):
    return (dic.get(var) or {}).get("categorias", {})


# ── personas: origen hace 5 años + llave del hogar ──────────────────────────
COLS_P = ["idep", "iprov", "imun", "i00", "p26_edad", "p24_parentes",
          "p37_lugres5", "mun_res5_cod"]
trozos, n = [], 0
for ch in pd.read_csv(RAW / "Persona_CPV-2024.csv", sep=";", usecols=COLS_P,
                      dtype=str, chunksize=600_000, low_memory=False):
    n += len(ch)
    ch["cod_ine"] = ch.idep.str.zfill(2) + ch.iprov.str.zfill(2) + ch.imun.str.zfill(2)
    trozos.append(ch[ch.cod_ine.isin(N9)])
    print(f"  personas {n:,}", end="\r", file=sys.stderr, flush=True)
p = pd.concat(trozos, ignore_index=True)
del trozos
p["edad"] = pd.to_numeric(p.p26_edad, errors="coerce")
print(f"\npersonas en los 9: {len(p):,}")


def origen(row):
    l5 = row["p37_lugres5"]
    if l5 == "1":
        return "aqui"
    if l5 == "3":
        return "exterior"
    if l5 != "2":
        return "sd"
    m = row["mun_res5_cod"]
    if not isinstance(m, str) or not m:
        return "parcial"
    c = m.zfill(6)[-6:]
    if c in N9:
        return "region"
    return "scz" if c[:2] == "07" else "otro_dep"


b = p[p.edad >= 5].copy()
del p
b["origen"] = b.apply(origen, axis=1)

# ── viviendas ───────────────────────────────────────────────────────────────
COLS_V = ["idep", "iprov", "imun", "i00", "v17_tenencia", "v03_pared", "v06_piso",
          "v07_aguapro", "v16_desague", "v09_energia", "v19f_inetmovil",
          "v18c_auto", "v18b_moto", "v19c_compu", "v13_habitac", "tot_pers"]
# por trozos: leerla entera junto con las 2,28 M personas se queda sin memoria
_tv = []
for ch in pd.read_csv(RAW / "Vivienda_CPV-2024.csv", sep=";", usecols=COLS_V,
                      dtype=str, chunksize=300_000, low_memory=False):
    ch["cod_ine"] = ch.idep.str.zfill(2) + ch.iprov.str.zfill(2) + ch.imun.str.zfill(2)
    _tv.append(ch[ch.cod_ine.isin(N9)])
v = pd.concat(_tv, ignore_index=True)
del _tv
print(f"viviendas en los 9: {len(v):,}")

j = b.merge(v.drop(columns=["idep", "iprov", "imun"]), on=["cod_ine", "i00"],
            how="left", validate="m:1")
print(f"personas con vivienda pegada: {int(j.v17_tenencia.notna().sum()):,} "
      f"({100*j.v17_tenencia.notna().mean():.1f}%)")

TEN = cat("v17_tenencia")
out = {"tenencia_categorias": TEN, "por_origen": {}}
print(f"\n{'origen':10s} {'n':>10s} {'%propia':>8s} {'%alquila':>9s} {'%agua red':>10s} "
      f"{'%alcant':>8s} {'%internet':>10s} {'%auto':>7s} {'pers/hab':>9s}")
for k in ("aqui", "region", "scz", "otro_dep", "exterior", "parcial"):
    g = j[(j.origen == k) & j.v17_tenencia.notna()]
    if not len(g):
        continue
    hab = pd.to_numeric(g.v13_habitac, errors="coerce")
    tot = pd.to_numeric(g.tot_pers, errors="coerce")
    fila = {
        "n": int(len(g)),
        "pct_propia": round(100 * (g.v17_tenencia == "1").mean(), 1),
        "pct_alquilada": round(100 * (g.v17_tenencia == "2").mean(), 1),
        "pct_agua_red": round(100 * (g.v07_aguapro == "1").mean(), 1),
        "pct_alcantarillado": round(100 * (g.v16_desague == "1").mean(), 1),
        "pct_internet_movil": round(100 * (g.v19f_inetmovil == "1").mean(), 1),
        "pct_auto": round(100 * (g.v18c_auto == "1").mean(), 1),
        "pers_por_habitacion": round(float((tot / hab.replace(0, pd.NA)).median()), 2),
    }
    out["por_origen"][k] = fila
    print(f"{k:10s} {fila['n']:>10,} {fila['pct_propia']:>8.1f} {fila['pct_alquilada']:>9.1f} "
          f"{fila['pct_agua_red']:>10.1f} {fila['pct_alcantarillado']:>8.1f} "
          f"{fila['pct_internet_movil']:>10.1f} {fila['pct_auto']:>7.1f} "
          f"{fila['pers_por_habitacion']:>9.2f}")

SAL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n->", SAL)
