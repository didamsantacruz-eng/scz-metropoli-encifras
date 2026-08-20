# -*- coding: utf-8 -*-
"""AUDITORÍA DE LOS FLUJOS DE RECEPCIÓN — qué hay, qué falta, qué está mal.

Va al CSV crudo del censo, no al parquet: el parquet no trae `p37_lugres5` ni
`p373_paisres5_cod`, que son justamente las preguntas por las que se pregunta.
"""
import json
import pathlib
import sys

import pandas as pd

CSV = pathlib.Path(r"C:\Users\HP\cpv2024\Persona_CPV-2024.csv")
DICC = pathlib.Path(r"C:\Users\HP\cpv2024\diccionario.json")
REPO = pathlib.Path(r"C:\Users\HP\OneDrive\Desktop\Proyectos\scz-metropolitana-gobernacion")
SAL = pathlib.Path(__file__).resolve().parent / "auditoria_flujos.json"

COLS = ["idep", "iprov", "imun", "p26_edad",
        "p35_lugnac", "p353_paisnac_cod", "mun_nac_cod",
        "p36_lugres", "p361_anres", "p363_paisres_cod",
        "p37_lugres5", "p373_paisres5_cod", "dep_res5_cod", "mun_res5_cod",
        "p25_sexo", "nivel_edu", "aestudio", "condact_13", "ocu_1d_13",
        "act_eco_2d_13", "p50_catocu_13", "p32_pueblos", "p31_cobersalud"]

muns = json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))
N9 = {m["cod_ine"]: m["nombre"] for m in muns}
dic = json.loads(DICC.read_text(encoding="utf-8"))["PERSONA"]
PAISES = dic.get("p373_paisres5_cod", {}).get("categorias", {})

trozos = []
leidas = 0
for ch in pd.read_csv(CSV, sep=";", usecols=COLS, dtype=str,
                      chunksize=500_000, low_memory=False):
    leidas += len(ch)
    ch["cod_ine"] = (ch.idep.str.zfill(2) + ch.iprov.str.zfill(2)
                     + ch.imun.str.zfill(2))
    trozos.append(ch[ch.cod_ine.isin(N9)])
    print(f"  leidas {leidas:,}", end="\r", flush=True, file=sys.stderr)
r = pd.concat(trozos, ignore_index=True)
del trozos
r["edad"] = pd.to_numeric(r.p26_edad, errors="coerce")
print(f"\nfilas del CSV: {leidas:,} | residentes en los 9: {len(r):,}")

out = {"filas_csv": int(leidas), "residentes_9": int(len(r))}

# ── 1 · ¿DÓNDE VIVÍA HACE 5 AÑOS? La pregunta completa, con su categoría 3 ──
cat = dic["p37_lugres5"]["categorias"]
v = r.p37_lugres5.value_counts(dropna=False)
out["lugres5"] = {cat.get(str(k), f"({k})"): int(n) for k, n in v.items()}
print("\n== p37_lugres5, los 9 municipios ==")
for k, n in v.items():
    print(f"   {cat.get(str(k), '(' + str(k) + ')'):34s} {n:>10,}  {100*n/len(r):5.1f}%")

# ── 2 · LOS QUE VENÍAN DE OTRO PAÍS, y de cuál ──────────────────────────────
ext = r[r.p37_lugres5 == "3"]
out["desde_exterior_5a"] = int(len(ext))
paises = ext.p373_paisres5_cod.value_counts()
out["paises_5a"] = {PAISES.get(str(k), str(k)): int(n) for k, n in paises.head(20).items()}
print(f"\n== vivian en OTRO PAIS hace 5 anios: {len(ext):,} personas ==")
for k, n in paises.head(12).items():
    print(f"   {PAISES.get(str(k), str(k)):28s} {n:>8,}")

# ── 3 · ¿QUÉ HACE EL MOTOR CON ELLOS? ───────────────────────────────────────
# `analisis_flujos.py` clasifica por `mun_res5`, que en el parquet viene vacío
# para quien vivía afuera. Se reproduce acá con las columnas del CSV.
sin_mun = ext.mun_res5_cod.isna() | ext.mun_res5_cod.isin(["", "0", "nan"])
out["exterior_sin_mun_res5"] = int(sin_mun.sum())
print(f"\n   de esos, sin `mun_res5_cod`: {int(sin_mun.sum()):,} "
      f"({100*sin_mun.mean():.1f}%)  -> el motor los manda a 'sd' y los DESCARTA")

# ── 4 · EL PERFIL, PARTIDO POR ORIGEN ───────────────────────────────────────
def clase(row):
    l5 = row["p37_lugres5"]
    if l5 == "1":
        return "aqui"
    if l5 == "3":
        return "exterior"
    if l5 == "4":
        return "no_nacido"
    if l5 == "2":
        m = row["mun_res5_cod"]
        if not isinstance(m, str) or not m:
            return "otro_mun_sd"
        c = m.zfill(6) if len(m) < 6 else m
        # mun_res5_cod viene como 'DPPMM' sin cero a la izquierda del depto
        c = c[-5:].zfill(5)
        c6 = c[0].zfill(2) + c[1:3] + c[3:5]
        if c6 in N9:
            return "region"
        return "scz" if c6[:2] == "07" else "otro_dep"
    return "sd"

base = r[r.edad >= 5].copy()
base["origen"] = base.apply(clase, axis=1)
rep = base.origen.value_counts()
out["origen_5a"] = {k: int(n) for k, n in rep.items()}
print("\n== origen hace 5 anios (5+ anios de edad) ==")
for k, n in rep.items():
    print(f"   {k:14s} {n:>10,}  {100*n/len(base):5.1f}%")

def perfil(g):
    if not len(g):
        return None
    a15 = g[g.edad >= 15]
    est = pd.to_numeric(a15.aestudio, errors="coerce")
    return {
        "n": int(len(g)),
        "pct_mujer": round(100 * (g.p25_sexo == "2").mean(), 1),
        "edad_mediana": float(g.edad.median()),
        "anios_estudio": round(float(est.mean()), 2) if len(a15) else None,
        "pct_superior": round(100 * (a15.nivel_edu == "4").mean(), 1) if len(a15) else None,
        "pct_indigena": round(100 * (g.p32_pueblos == "1").mean(), 1),
        "pct_sin_seguro": round(100 * (g.p31_cobersalud == "2").mean(), 1),
        "ocu_top": {k: round(100 * v, 1) for k, v in
                    a15[a15.ocu_1d_13.notna()].ocu_1d_13.value_counts(normalize=True).head(4).items()},
    }

out["perfil_por_origen"] = {k: perfil(base[base.origen == k])
                            for k in ("aqui", "region", "scz", "otro_dep", "exterior")}
print("\n== perfil por origen (lo que HOY no se puede ver en la web) ==")
print(f"   {'origen':10s} {'n':>10s} {'%muj':>6s} {'edad':>5s} {'estud':>6s} {'%sup':>6s} {'%indig':>7s}")
for k in ("aqui", "region", "scz", "otro_dep", "exterior"):
    p = out["perfil_por_origen"][k]
    if p:
        print(f"   {k:10s} {p['n']:>10,} {p['pct_mujer']:>6.1f} {p['edad_mediana']:>5.0f} "
              f"{p['anios_estudio']:>6.2f} {p['pct_superior']:>6.1f} {p['pct_indigena']:>7.1f}")

# ── 5 · EL AÑO DE LLEGADA, que permitiría una SERIE y hoy no se usa ─────────
out["tiene_anio_llegada"] = {
    "p361_anres_no_nulos": int(r.p361_anres.notna().sum()),
    "ejemplos": sorted(x for x in r.p361_anres.dropna().unique()[:12]),
}
print(f"\n== ano de llegada a la residencia actual (`p361_anres`): "
      f"{int(r.p361_anres.notna().sum()):,} declaran ==")

SAL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n->", SAL)
