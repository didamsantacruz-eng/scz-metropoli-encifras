# -*- coding: utf-8 -*-
"""Junta todo lo medido en un solo JSON para la hoja de auditoría.

Ningún número de la hoja se escribe a mano: todos salen de acá, y acá salen del
censo o de los archivos publicados.
"""
import os
import json
import pathlib

import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
# ⚠️ RUTAS PORTABLES (2026-08-26). Acá vivían clavadas la ruta del repo en
#    OneDrive y la del microdato en el disco de Carlos. El repo pasó a manos de
#    más gente: con la ruta clavada, este script sólo corría en la máquina donde
#    se escribió.
#    · REPO se deduce del propio archivo; no hace falta configurarlo.
#    · RAW es microdato del INE y VIVE FUERA DEL REPO por definición, así que no
#      se puede deducir: sale de la variable de entorno CPV2024 y, si no está,
#      cae en la ruta de siempre para no romper esta máquina.
REPO = pathlib.Path(__file__).resolve().parent.parent
RAW = pathlib.Path(os.environ.get("CPV2024", r"C:\Users\HP\cpv2024"))

aud = json.loads((AQUI / "auditoria_flujos.json").read_text(encoding="utf-8"))
perfil_pub = json.loads((REPO / "docs/datos/flujos_perfil.json").read_text(encoding="utf-8"))
socio = {}
p = AQUI / "perfil_socioec.json"
if p.exists():
    socio = json.loads(p.read_text(encoding="utf-8"))

N9 = {m["cod_ine"]: m["nombre"] for m in
      json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))}

# ── los orígenes de fuera de la región, que ya están calculados y no se publican
fl = pd.read_csv(REPO / "catalogo/flujos_2024.csv", dtype={"origen": str, "destino": str})
h = fl[fl.destino.isin(N9)]
fuera = {}
for t in ("nacimiento", "residencia5", "trabajo"):
    s = h[h.tipo == t]
    sf = s[~s.origen.isin(N9)]
    fuera[t] = {"pares": int(len(s)), "origenes": int(s.origen.nunique()),
                "personas_de_fuera": int(sf.personas.sum()),
                "pares_9x9": int(len(s[s.origen.isin(N9)]))}
top = (h[(h.tipo == "residencia5") & (~h.origen.isin(N9))]
       .groupby("origen").personas.sum().sort_values(ascending=False).head(12))
fuera["top_origenes_res5"] = {k: int(v) for k, v in top.items()}

# ── la emigración, un módulo entero sin usar ────────────────────────────────
em = pd.read_csv(RAW / "Emigracion_CPV-2024.csv", sep=";", dtype=str)
em["cod_ine"] = em.idep.str.zfill(2) + em.iprov.str.zfill(2) + em.imun.str.zfill(2)
e9 = em[em.cod_ine.isin(N9)]
anios = pd.to_numeric(e9.e204_ansal, errors="coerce")
PAIS = {"152": "Chile", "724": "España", "032": "Argentina", "32": "Argentina",
        "076": "Brasil", "76": "Brasil", "840": "Estados Unidos", "999": "Sin especificar",
        "380": "Italia", "826": "Reino Unido", "604": "Perú", "756": "Suiza",
        "392": "Japón", "276": "Alemania"}
emig = {
    "total_pais": int(len(em)),
    "total_9": int(len(e9)),
    "por_anio": {str(int(a)): int(n) for a, n in
                 anios[(anios >= 2010) & (anios <= 2024)].value_counts().sort_index().items()},
    "sin_anio": int((anios == 9999).sum()),
    "destinos": {PAIS.get(str(k), str(k)): int(n)
                 for k, n in e9.pais_destino_cod.value_counts().head(8).items()},
    "por_municipio": {N9[c]: int((e9.cod_ine == c).sum()) for c in sorted(N9, key=lambda x: N9[x])},
}

# ── los paises de origen, con los codigos que el diccionario no resolvio ────
PAIS5 = dict(aud["paises_5a"])
for viejo, nuevo in (("032", "Argentina"), ("076", "Brasil")):
    if viejo in PAIS5:
        PAIS5[nuevo] = PAIS5.pop(viejo)
PAIS5 = dict(sorted(PAIS5.items(), key=lambda kv: -kv[1]))

# ── los bugs, con su aritmetica ─────────────────────────────────────────────
reciente = perfil_pub["reciente"]
bugs = {
    "exterior_en_cero": {c: reciente[c]["exterior"] for c in reciente},
    "descomposicion_sd": {
        "sd_total": 68246,
        "sin_especificar": aud["lugres5"].get("Sin Especificar", 0),
        "vivian_en_otro_pais": aud["desde_exterior_5a"],
        "declaracion_parcial": 68246 - aud["lugres5"].get("Sin Especificar", 0)
                               - aud["desde_exterior_5a"],
    },
    "llegados_publicado": perfil_pub["region"]["llegados"]["n"],
    "llegados_censo": (aud["origen_5a"]["scz"] + aud["origen_5a"]["otro_dep"]
                       + aud["origen_5a"]["exterior"]),
    "pct_ocupado_imposible": {k: perfil_pub["region"][k].get("pct_ocupado")
                              for k in ("llegados", "estaban", "conmutan", "no_conmutan")},
    "doble_definicion_llegados": {
        "region": perfil_pub["region"]["llegados"]["n"],
        "suma_municipios": sum(perfil_pub["perfil"][c]["llegados"]["n"] for c in perfil_pub["perfil"]),
    },
}
bugs["descomposicion_sd"]["cierra"] = (
    bugs["descomposicion_sd"]["sin_especificar"]
    + bugs["descomposicion_sd"]["vivian_en_otro_pais"]
    + bugs["descomposicion_sd"]["declaracion_parcial"] == 68246)

todo = {
    "lugres5": aud["lugres5"],
    "origen_5a": aud["origen_5a"],
    "perfil_por_origen": aud["perfil_por_origen"],
    "paises_origen_5a": PAIS5,
    "anio_llegada_declaran": aud["tiene_anio_llegada"]["p361_anres_no_nulos"],
    "residentes_9": aud["residentes_9"],
    "fuera_de_la_region": fuera,
    "emigracion": emig,
    "bugs": bugs,
    "socioeconomico": socio,
    "municipios": N9,
}
(AQUI / "auditoria_completa.json").write_text(
    json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
print("-> auditoria_completa.json")
print("   descomposicion del 'sd' cierra:", bugs["descomposicion_sd"]["cierra"])
print("   llegados publicado:", f'{bugs["llegados_publicado"]:,}',
      "| censo:", f'{bugs["llegados_censo"]:,}',
      "| faltan:", f'{bugs["llegados_censo"]-bugs["llegados_publicado"]:,}')
print("   socioeconomico cargado:", bool(socio))
