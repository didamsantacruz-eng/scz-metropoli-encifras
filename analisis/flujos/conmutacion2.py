# -*- coding: utf-8 -*-
"""CONMUTACIÓN, TODO LO QUE EL CENSO PERMITE SACAR.

★ HASTA DÓNDE LLEGA EL SECTOR, medido en el diccionario y no supuesto:
  `act_eco_2d_13` trae **23 categorías** — y pese al nombre NO son divisiones a
  dos dígitos de la CIIU, son las **secciones A–U**. No existe el nivel que
  separaría «transporte terrestre» de «transporte aéreo».
  `ocu_1d_13` trae **12** — el gran grupo de ocupación, un dígito. No hay 2 ni 4.
  ⇒ La textura fina no sale de bajar de nivel (no hay), sale de **CRUZAR**
    sección × ocupación × categoría ocupacional.

★ «Servicios» no es una bolsa: de las 23 secciones, catorce lo son y están
  separadas (comercio, transporte, alojamiento y comidas, información, finanzas,
  inmobiliarias, profesionales, administrativas, administración pública,
  enseñanza, salud, artes, otros servicios, hogares como empleadores).

★ `p50_semp` NO es tamaño de establecimiento: sus categorías son idénticas a
  `p50_catocu_13`. No hay variable de tamaño de empresa en el censo.
"""
import json
import pathlib

import pandas as pd

RAW = pathlib.Path(r"C:\Users\HP\cpv2024")
REPO = pathlib.Path(r"C:\Users\HP\OneDrive\Desktop\Proyectos\scz-metropolitana-gobernacion")
SAL = pathlib.Path(__file__).resolve().parent / "conmutacion_full.json"

N9 = {m["cod_ine"]: m["nombre"] for m in
      json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))}
dic = json.loads((RAW / "diccionario.json").read_text(encoding="utf-8"))["PERSONA"]
ET_RAMA = dic["act_eco_2d_13"]["categorias"]
ET_OCU = dic["ocu_1d_13"]["categorias"]
ET_MUN = dic["mun_nac_cod"]["categorias"]      # 466 municipios del país
ET_DEP = dic["dep_nac_cod"]["categorias"]

# el nombre corto de la sección, sin la letra ni la coletilla
# ⚠️ las claves van como TEXTO: `dist()` busca con `str(int(k))`, y con claves
#    enteras la etiqueta no resolvía y salía "7.0" en vez del nombre de la sección
CORTO = {str(int(k)): v.split(". ", 1)[-1].split(";")[0].split(",")[0].strip()
         for k, v in ET_RAMA.items() if k.isdigit()}

nombre_mun = lambda c: (N9.get(c) or ET_MUN.get(str(c).lstrip("0"), c))
nombre_dep = lambda c: ET_DEP.get(str(c[:2]).lstrip("0"), c[:2])

COLS = ["cod_ine", "mun_trabaja", "ocupado", "mujer", "edad", "anios_estudio",
        "nivel", "rama", "ocu1d", "catocu", "indigena", "afiliado", "hogar",
        "asiste", "discap", "idioma", "ecivil", "jefe"]
d = pd.read_parquet(RAW / "persona_full.parquet", columns=COLS)
d["cod_ine"] = d.cod_ine.astype(str)
d["mun_trabaja"] = d.mun_trabaja.astype(str)
r = d[d.cod_ine.isin(N9) & d.ocupado.astype(bool) & d.mun_trabaja.str.len().eq(6)].copy()
del d
print(f"ocupados residentes en los 9 con municipio de trabajo: {len(r):,}")

# ── la vivienda ─────────────────────────────────────────────────────────────
COLS_V = ["idep", "iprov", "imun", "i00", "v17_tenencia", "v07_aguapro", "v16_desague",
          "v18a_bici", "v18b_moto", "v18c_auto", "v19f_inetmovil", "v19c_compu",
          "v18f_refri", "v13_habitac", "tot_pers", "v03_pared", "v06_piso"]
tv = []
for ch in pd.read_csv(RAW / "Vivienda_CPV-2024.csv", sep=";", usecols=COLS_V,
                      dtype=str, chunksize=300_000, low_memory=False):
    ch["c"] = ch.idep.str.zfill(2) + ch.iprov.str.zfill(2) + ch.imun.str.zfill(2)
    ch = ch[ch.c.isin(N9)]
    if len(ch):
        ch["hogar"] = (ch.idep.astype(int).astype(str) + ch.iprov.str.zfill(2)
                       + ch.imun.str.zfill(2) + ch.i00.str.zfill(8)).astype("int64")
        tv.append(ch.drop(columns=["idep", "iprov", "imun", "i00", "c"]))
v = pd.concat(tv, ignore_index=True); del tv
j = r.merge(v, on="hogar", how="left", validate="m:1")
print(f"pegue con la vivienda: {100*j.v17_tenencia.notna().mean():.1f}%")


def dist(serie, etiquetas=None, tope=None):
    """Distribución COMPLETA en porcentaje, no sólo el top."""
    vc = serie.value_counts(normalize=True)
    if tope:
        vc = vc.head(tope)
    return {(etiquetas.get(str(int(k)), str(k)) if etiquetas else str(k)): round(100 * x, 1)
            for k, x in vc.items() if x >= .0005}


def perfil(g, minimo=30):
    if len(g) < minimo:
        return None
    a = g[g.edad >= 15]
    hab = pd.to_numeric(g.v13_habitac, errors="coerce")
    tot = pd.to_numeric(g.tot_pers, errors="coerce")
    o = {
        "n": int(len(g)),
        "pct_mujer": round(100 * g.mujer.mean(), 1),
        "edad_mediana": float(g.edad.median()),
        "edades": {e: round(100 * ((g.edad >= a1) & (g.edad <= b1)).mean(), 1)
                   for a1, b1, e in ((15, 24, "15-24"), (25, 39, "25-39"),
                                     (40, 64, "40-64"), (65, 200, "65+"))},
        "pct_indigena": round(100 * g.indigena.mean(), 1),
        "pct_jefe": round(100 * g.jefe.astype(bool).mean(), 1),
        "anios_estudio": round(float(a.anios_estudio.mean()), 2),
        "nivel": dist(a.nivel.replace("", pd.NA).dropna()),
        "pct_superior": round(100 * (a.nivel == "superior").mean(), 1),
        "pct_sin_seguro": round(100 * (g.afiliado == 4).mean(), 1),
        "pct_estudia": round(100 * g.asiste.astype(bool).mean(), 1),
        "rama": dist(g.rama.dropna(), CORTO),
        "ocupacion": dist(g.ocu1d.dropna(), ET_OCU),
        "catocu": dist(g.catocu.replace("", pd.NA).dropna()),
    }
    vv = g[g.v17_tenencia.notna()]
    if len(vv) >= minimo:
        o["vivienda"] = {
            "pct_propia": round(100 * (vv.v17_tenencia == "1").mean(), 1),
            "pct_alquila": round(100 * (vv.v17_tenencia == "2").mean(), 1),
            "pct_agua_red": round(100 * (vv.v07_aguapro == "1").mean(), 1),
            "pct_alcantarillado": round(100 * (vv.v16_desague == "1").mean(), 1),
            "pct_auto": round(100 * (vv.v18c_auto == "1").mean(), 1),
            "pct_moto": round(100 * (vv.v18b_moto == "1").mean(), 1),
            "pct_bici": round(100 * (vv.v18a_bici == "1").mean(), 1),
            "pct_ninguno": round(100 * ((vv.v18c_auto != "1") & (vv.v18b_moto != "1")
                                        & (vv.v18a_bici != "1")).mean(), 1),
            "pct_internet_movil": round(100 * (vv.v19f_inetmovil == "1").mean(), 1),
            "pct_compu": round(100 * (vv.v19c_compu == "1").mean(), 1),
            "pers_por_cuarto": round(float((tot / hab.replace(0, pd.NA)).median()), 2),
        }
    return o


out = {"municipios": N9, "etiquetas": {"rama": CORTO, "ocu": ET_OCU},
       "nota_granularidad": {
           "secciones_ciiu": len(CORTO), "grupos_ocupacion": len(ET_OCU),
           "hay_division_2d": False, "hay_ocupacion_2d": False,
           "hay_tamano_empresa": False}}

queda = j[j.mun_trabaja == j.cod_ine]
dentro = j[(j.mun_trabaja != j.cod_ine) & j.mun_trabaja.isin(N9)]
afuera = j[~j.mun_trabaja.isin(N9)]
out["region"] = {"no_conmuta": perfil(queda), "conmuta_dentro": perfil(dentro),
                 "trabaja_fuera": perfil(afuera), "total": int(len(j))}

# ── DÓNDE TRABAJAN: el destino, completo ───────────────────────────────────
# ★ OJO CON «TRABAJA FUERA DE LA REGIÓN». El INE codifica «provincia sin
#   municipio» como XXYY99, y Andrés Ibáñez (0701) contiene a CINCO de los nueve.
#   Quien declara 070199 casi con seguridad trabaja DENTRO de la región y hoy cae
#   del lado de afuera sólo porque no precisó el municipio. No se corrige en
#   silencio: se mide y se dice.
_prov_region = sorted({c[:4] for c in N9})
_cod = {c: int((afuera.mun_trabaja == c).sum())
        for c in sorted(afuera.mun_trabaja.unique())
        if c.endswith("99") and c[:4] in _prov_region}
out["parciales_de_la_region"] = {
    "codigos": {f"{c} · {nombre_mun(c)}": n for c, n in _cod.items()},
    "total": sum(_cod.values()),
    "sobre_los_que_trabajan_fuera": round(100 * sum(_cod.values()) / max(len(afuera), 1), 1),
}

out["destinos"] = {
    "dentro_region": {N9[k]: int(n) for k, n in dentro.mun_trabaja.value_counts().items()},
    "fuera_por_departamento": {nombre_dep(k): int(n) for k, n in
                               afuera.mun_trabaja.str[:2].value_counts().items()},
    "fuera_por_municipio": {nombre_mun(k): int(n) for k, n in
                            afuera.mun_trabaja.value_counts().head(25).items()},
}

# ── el sector de quien ENTRA a cada municipio, que es la pregunta de fondo ──
out["por_municipio"] = {}
for c in N9:
    sale = j[(j.cod_ine == c) & (j.mun_trabaja != c)]
    entra = j[(j.mun_trabaja == c) & (j.cod_ine != c)]
    out["por_municipio"][c] = {
        "nombre": N9[c],
        "ocupados": int((j.cod_ine == c).sum()),
        "se_queda": int(((j.cod_ine == c) & (j.mun_trabaja == c)).sum()),
        "sale": int(len(sale)), "entra": int(len(entra)),
        "destinos": {nombre_mun(k): int(n) for k, n in
                     sale.mun_trabaja.value_counts().head(8).items()},
        "origenes": {N9.get(k, k): int(n) for k, n in
                     entra.cod_ine.value_counts().items()},
        "perfil_sale": perfil(sale),
        "perfil_entra": perfil(entra),
        "perfil_queda": perfil(j[(j.cod_ine == c) & (j.mun_trabaja == c)]),
    }

# ── por corredor ────────────────────────────────────────────────────────────
out["pares"] = {}
for (o_, dst), n in dentro.groupby(["cod_ine", "mun_trabaja"]).size().sort_values(ascending=False).items():
    p = perfil(dentro[(dentro.cod_ine == o_) & (dentro.mun_trabaja == dst)])
    if p:
        out["pares"][f"{o_}>{dst}"] = {"origen": N9[o_], "destino": N9[dst], **p}

# ── EL CRUCE sección × ocupación, que es de donde sale la textura ──────────
def cruce(g):
    t = pd.crosstab(g.rama, g.ocu1d, normalize="index") * 100
    fuera_ = {}
    for ram in t.index:
        fila = t.loc[ram].sort_values(ascending=False).head(3)
        fuera_[CORTO.get(str(int(ram)), str(ram))] = {
            "n": int((g.rama == ram).sum()),
            "ocupaciones": {ET_OCU.get(str(int(k)), str(k)): round(float(x), 1)
                            for k, x in fila.items() if x >= 1}}
    return dict(sorted(fuera_.items(), key=lambda kv: -kv[1]["n"]))

out["cruce_rama_ocu"] = {"conmuta_dentro": cruce(dentro), "no_conmuta": cruce(queda)}

SAL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n-> {SAL.name}  {SAL.stat().st_size/1024:.0f} KB")
print(f"corredores con perfil: {len(out['pares'])}")

print("\n== DÓNDE TRABAJA el que sale de la región ==")
for k, n in list(out["destinos"]["fuera_por_departamento"].items())[:9]:
    print(f"   {k:26s} {n:>7,}")
print("\n   municipios más nombrados fuera de la región:")
for k, n in list(out["destinos"]["fuera_por_municipio"].items())[:8]:
    print(f"     {k:24s} {n:>7,}")

pr = out["parciales_de_la_region"]
print("\n== PARCIALES QUE CAEN COMO «FUERA» PERO SON DE LA REGIÓN ==")
print(f"   {pr['total']:,} de {len(afuera):,} ({pr['sobre_los_que_trabajan_fuera']}%) "
      f"declararon una provincia de la región sin precisar el municipio")
for k, n in pr["codigos"].items():
    print(f"     {k[:58]:60s} {n:>7,}")

print("\n== SECTOR: el que conmuta dentro de la región, distribución COMPLETA ==")
for k, x in out["region"]["conmuta_dentro"]["rama"].items():
    print(f"   {k[:52]:54s} {x:5.1f}%")
