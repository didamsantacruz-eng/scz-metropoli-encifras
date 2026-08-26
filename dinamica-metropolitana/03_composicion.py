# -*- coding: utf-8 -*-
"""PASO 3 — LA COMPOSICIÓN DE CADA RELACIÓN.

Una «relación» es una terna **(dimensión, origen, destino)**. Las tres dimensiones
tienen universos distintos y NO se suman entre sí:

    nacimiento   `p35_lugnac`   stock sin fecha        2.282.770 residentes
    residencia   `p37_lugres5`  flujo fechado 19→24    excluye 173.255 no nacidos
    trabajo      `p52_mov`      desplazamiento diario  NO es migración

Para cada relación se calculan las SEIS FAMILIAS de descriptivos:
    1 quién es      · 2 qué sabe      · 3 de qué vive
    4 cómo vive     · 5 con qué cuenta · 6 qué le falta

★ CADA INDICADOR CON SU UNIVERSO, Y EL MISMO ARRIBA Y ABAJO.
  Éste es el error nº3 de la auditoría, que dio porcentajes de ocupados de
  100,8% y 102,1%: el numerador contaba ocupados de cualquier edad y el
  denominador sólo los de 15 o más. Acá cada indicador restringido se construye
  como una columna con NaN fuera de su universo, de modo que el promedio del
  grupo use exactamente el mismo denominador que su numerador. Si el universo
  está vacío sale nulo, no un número inventado.

★ LOS INDICADORES DE VIVIENDA SE LEEN COMO PERSONAS, NO COMO HOGARES.
  «38% con alcantarillado» en un flujo significa «el 38% de esas personas vive en
  un hogar con alcantarillado». Es la lectura correcta para un flujo de gente, y
  hay que escribirla así en la página para que nadie la confunda con un
  porcentaje de viviendas.
"""
import os
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

# ⚠️ RUTAS PORTABLES (2026-08-26). Acá vivían clavadas la ruta del repo en
#    OneDrive y la del microdato en el disco de Carlos. El repo pasó a manos de
#    más gente: con la ruta clavada, este script sólo corría en la máquina donde
#    se escribió.
#    · REPO se deduce del propio archivo; no hace falta configurarlo.
#    · RAW es microdato del INE y VIVE FUERA DEL REPO por definición, así que no
#      se puede deducir: sale de la variable de entorno CPV2024 y, si no está,
#      cae en la ruta de siempre para no romper esta máquina.
RAW = pathlib.Path(os.environ.get("CPV2024", r"C:\Users\HP\cpv2024"))
REPO = pathlib.Path(__file__).resolve().parent.parent
AQUI = pathlib.Path(__file__).resolve().parent
SAL = AQUI / "salida"
SAL.mkdir(exist_ok=True)

MIN_PERFIL = 40          # bajo esto, los porcentajes son ruido: sólo se guarda n

N9 = {m["cod_ine"]: m["nombre"] for m in
      json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))}
DIC = json.loads((RAW / "diccionario.json").read_text(encoding="utf-8"))
DP, DV = DIC["PERSONA"], DIC["VIVIENDA"]
ET_MUN = DP["mun_nac_cod"]["categorias"]
ET_DEP = DP["dep_nac_cod"]["categorias"]
ET_PAIS = DP["p353_paisnac_cod"]["categorias"]
ET_PROV = DP["prov_nac_cod"]["categorias"]

b = pd.read_parquet(RAW / "base9_metro_nivelvida.parquet")
print(f"base: {len(b):,} personas × {len(b.columns)} columnas")


# ═══════════════════ etiquetas de lugar ═══════════════════
def etiqueta_lugar(clave):
    """`mun:070104` → «La Guardia» · `dep:03` → «Cochabamba» · `pais:032` → «Argentina»."""
    if clave in ("aqui", "nonato", "sd"):
        return {"aqui": "Ya estaba aquí", "nonato": "Aún no había nacido",
                "sd": "Sin especificar"}[clave]
    tipo, cod = clave.split(":", 1)
    if tipo == "mun":
        return N9.get(cod) or ET_MUN.get(cod.lstrip("0"), f"Municipio {cod}")
    if tipo == "prov":
        return ET_PROV.get(cod.lstrip("0"), f"Provincia {cod}")
    if tipo == "dep":
        return ET_DEP.get(cod.lstrip("0"), f"Departamento {cod}")
    if tipo == "pais":
        return "País sin precisar" if cod == "sd" else \
            ET_PAIS.get(cod.lstrip("0"), f"País {cod}")
    return clave


def familia_lugar(clave, propio=None):
    """A qué gran grupo pertenece un origen. Es lo que permite agregar sin mezclar."""
    if clave in ("aqui", "nonato", "sd"):
        return clave
    tipo, cod = clave.split(":", 1)
    if tipo == "pais":
        return "exterior"
    if tipo == "mun":
        if cod == propio:
            return "aqui"
        return "region" if cod in N9 else ("scz" if cod.startswith("07") else "dep")
    if tipo in ("prov", "dep"):                    # declaración parcial
        return "scz_parcial" if cod.startswith("07") else "dep_parcial"
    return "sd"


# ═══════════════════ los indicadores ═══════════════════
nan_si_no = lambda cond, val: np.where(cond, val.astype(float), np.nan)

print("armando universos…")
b["u_superior"] = nan_si_no(b.edad.ge(19), b.superior)
b["u_sin_nivel"] = nan_si_no(b.edad.ge(19), b.sin_nivel)
b["u_analfabeto"] = nan_si_no(b.edad.ge(15), b.analfabeto)
b["u_asiste"] = nan_si_no(b.edad.between(6, 17), b.asiste_si)
b["u_asiste_privado"] = nan_si_no(b.edad.between(6, 17) & b.asiste_si, b.asiste_privado)
b["u_ocupado"] = nan_si_no(b.pet, b.ocupado)
b["u_desocupado"] = nan_si_no(b.pet, b.desocupado)
b["u_conmuta"] = nan_si_no(b.ocupado, b.conmuta)
b["u_trabaja_en_casa"] = nan_si_no(b.ocupado, b.trab_donde.eq("en_la_vivienda"))
b["u_sin_cedula"] = nan_si_no(b.edad.ge(18), b.sin_cedula)
b["u_cedula_extranjero"] = nan_si_no(b.edad.ge(18), b.cedula_extranjero)
b["edad_num"] = b.edad

# ⛔⛔ EL TAMAÑO DEL HOGAR TAMBIÉN TIENE UNIVERSO, Y NO LO TENÍA (2026-08-26).
#    Salía 40,54 personas por hogar en la región. El tamaño real es 3,58
#    —2.282.770 personas entre 637.667 hogares, y el promedio POR HOGAR de esta
#    misma columna da 3,58—, así que la columna estaba bien y el promedio, mal.
#    Dos cosas se sumaban:
#    1. Es un atributo del HOGAR promediado sobre PERSONAS. Eso da Σn²/Σn, «el
#       tamaño del hogar de la persona promedio», que está sesgado por tamaño
#       por construcción. Es el mismo error que `lamina_municipal.py` ya tiene
#       documentado un nivel más arriba, con municipios en vez de hogares.
#    2. Y lo vuelve absurdo la cola: las viviendas COLECTIVAS entraban como si
#       fueran hogares. `v01_tipoviv` 12 es «recinto penitenciario» y promedia
#       7.318 personas — ese único registro de 8.645 es Palmasola—; la 8 es
#       hospital con internación (263) y la 9 cuartel (202). Son 279 viviendas
#       sobre 20 personas, el 0,04% de los hogares, y solas levantaban la media
#       de 3,58 a 40,54.
#    ⇒ Se restringe a vivienda PARTICULAR, que es el universo con el que el INE
#      publica todo lo de vivienda y el que ya declara el tablero («sobre las
#      viviendas particulares»). Medido: fuera del universo queda el 1,86% de
#      las personas, y de los otros doce indicadores de vivienda ninguno se
#      mueve más de 1,2 puntos —`pers_por_dormitorio` y `pers_por_habitacion`
#      no se mueven nada, porque los dormitorios de un cuartel escalan con su
#      gente—. O sea que el defecto era de ESTE campo, no del recorte.
#    ⚠️ La restricción NO se aplica a los demás indicadores a propósito: quien
#      vive en un cuartel o en un penal sigue siendo una persona y su edad, su
#      educación y su origen son datos válidos. Lo que no es válido es tratar a
#      ese edificio como un hogar.
PARTICULAR = b.v01_tipoviv.isin(["1", "2", "3", "4", "5", "6"])
b["u_tam_hogar"] = nan_si_no(PARTICULAR, b.tot_pers_hog)
print(f"  vivienda particular: {int(PARTICULAR.sum()):,} de {len(b):,} personas "
      f"({(~PARTICULAR).mean() * 100:.2f}% fuera del universo del hogar)")

# (nombre publicable, columna, familia)  —  las booleanas salen como %
ESCALARES = [
    # 1 · quién es
    ("pct_mujer", "mujer", 1), ("pct_jefe", "jefe", 1),
    ("pct_indigena", "indigena", 1), ("pct_discapacidad", "discap", 1),
    ("tam_hogar", "u_tam_hogar", 1),      # ⚠️ restringido: ver PARTICULAR arriba
    # 2 · qué sabe
    ("anios_estudio", "anios_estudio", 2), ("pct_superior", "u_superior", 2),
    ("pct_sin_nivel", "u_sin_nivel", 2), ("pct_analfabeto", "u_analfabeto", 2),
    ("pct_asiste_6_17", "u_asiste", 2), ("pct_asiste_privado", "u_asiste_privado", 2),
    # 3 · de qué vive
    ("pct_ocupado", "u_ocupado", 3), ("pct_desocupado", "u_desocupado", 3),
    ("pct_conmuta", "u_conmuta", 3), ("pct_trabaja_en_casa", "u_trabaja_en_casa", 3),
    # 4 · cómo vive
    ("pct_urbano", "urbano", 4), ("pct_agua_red", "agua_red", 4),
    ("pct_agua_dentro", "agua_dentro", 4), ("pct_alcantarillado", "alcantarillado", 4),
    ("pct_energia_red", "energia_red", 4), ("pct_cocina_lena", "cocina_lena", 4),
    ("pct_basura_servicio", "basura_servicio", 4), ("pct_piso_tierra", "piso_tierra", 4),
    ("pct_pared_ladrillo", "pared_ladrillo", 4),
    ("pct_hacinamiento", "hacinamiento", 4),
    ("pers_por_dormitorio", "pers_por_dormitorio", 4),
    ("pct_propia", "propia", 4), ("pct_alquila", "alquila", 4),
    # 5 · con qué cuenta
    ("quintil_medio", "quintil", 5), ("riqueza_media", "riqueza", 5),
    ("pct_auto", "auto", 5), ("pct_moto", "moto", 5), ("pct_bici", "bici", 5),
    ("pct_refri", "refri", 5), ("pct_lavadora", "lavadora", 5),
    ("pct_aire", "aire", 5), ("pct_compu", "compu", 5),
    ("pct_inet_fijo", "inet_fijo", 5), ("pct_inet_movil", "inet_movil", 5),
    ("pagos_voluntarios", "pagos_voluntarios", 5),
    ("pct_paga_alguno", "paga_alguno", 5), ("pct_paga_tres", "paga_tres_o_mas", 5),
    # 6 · qué le falta
    ("privaciones", "privaciones_vivienda", 6),
    ("pct_sin_seguro", "sin_seguro", 6),
    ("pct_sin_cedula", "u_sin_cedula", 6),
    ("pct_cedula_extranjero", "u_cedula_extranjero", 6),
    ("pct_sin_registro", "sin_registro", 6),
    ("pct_priv_pared", "mat_pared", 6), ("pct_priv_techo", "mat_techo", 6),
    ("pct_priv_piso", "mat_piso", 6), ("pct_priv_hacina", "esp_hacinamiento", 6),
    ("pct_priv_agua", "srv_agua", 6), ("pct_priv_saneamiento", "srv_saneamiento", 6),
    ("pct_priv_energia", "srv_energia", 6), ("pct_priv_basura", "srv_basura", 6),
    ("pct_priv_combustible", "ins_combustible", 6),
    ("pct_salud_publica", "salud_publica", 6), ("pct_salud_caja", "salud_caja", 6),
    ("pct_salud_privada", "salud_privada", 6),
    ("pct_salud_automedica", "salud_automedica", 6),
    ("pct_hogar_emigro", "hogar_emigro", 6),
]
NO_PORCENTAJE = {"anios_estudio", "tam_hogar", "pers_por_dormitorio", "quintil_medio",
                 "riqueza_media", "pagos_voluntarios", "privaciones"}
COLS_ESC = [c for _, c, _ in ESCALARES]

# distribuciones: (nombre, columna, etiquetas, universo o None)
et = lambda v, blq=DP: {k: x.split(". ", 1)[-1].split(";")[0].split(",")[0].strip()
                        for k, x in blq[v]["categorias"].items()}
DISTRIB = [
    ("edad_tramo", "edad_tramo", None, None),
    ("nivel_educativo", "nivel_edu", et("nivel_edu"), "edad>=19"),
    ("tipo_hogar", "tip_hog", et("tip_hog", DV), None),
    ("estado_civil", "p53_ecivil", et("p53_ecivil"), "edad>=15"),
    ("rama", "rama", et("act_eco_2d_13"), "ocupado"),
    ("ocupacion", "ocu1d", et("ocu_1d_13"), "ocupado"),
    ("categoria_ocupacional", "catocu", et("p50_catocu_13"), "ocupado"),
    ("lugar_de_trabajo", "trab_donde", None, "ocupado"),
    ("inactividad", "p48_nocu", et("p48_nocu"), "inactivo"),
    ("quintil", "quintil", None, None),
    ("tenencia", "v17_tenencia", et("v17_tenencia", DV), None),
    ("agua_fuente", "v07_aguapro", et("v07_aguapro", DV), None),
    ("agua_distribucion", "v08_aguadist", et("v08_aguadist", DV), None),
    ("saneamiento", "v16_desague", et("v16_desague", DV), None),
    ("energia", "v09_energia", et("v09_energia", DV), None),
    ("combustible", "v10_combus", et("v10_combus", DV), None),
    ("basura", "v11_basura", et("v11_basura", DV), None),
    ("pared", "v03_pared", et("v03_pared", DV), None),
    ("techo", "v05_techo", et("v05_techo", DV), None),
    ("piso", "v06_piso", et("v06_piso", DV), None),
    ("afiliacion_salud", "p31_afiliado", et("p31_afiliado"), None),
]
b["edad_tramo"] = pd.cut(b.edad, [-1, 14, 24, 39, 64, 200],
                         labels=["0-14", "15-24", "25-39", "40-64", "65+"])

# la HUELLA: diez indicadores, siempre los mismos y en el mismo orden, para que
# cada flujo tenga una forma reconocible y dos se comparen sin leer la tabla
HUELLA = ["anios_estudio", "pct_superior", "quintil_medio", "privaciones",
          "pct_sin_seguro", "pct_hacinamiento", "pct_alcantarillado",
          "pct_propia", "pct_ocupado", "pct_conmuta"]

UNIVERSOS = {"edad>=19": lambda d: d.edad.ge(19), "edad>=15": lambda d: d.edad.ge(15),
             "ocupado": lambda d: d.ocupado, "inactivo": lambda d: d.inactivo}


def calcular(df, claves):
    """Todas las familias, para todos los grupos definidos por `claves`, de una."""
    g = df.groupby(claves, observed=True)
    out = {}
    n = g.size()
    esc = g[COLS_ESC].mean()
    for k, tam in n.items():
        k = k if isinstance(k, tuple) else (k,)
        out[k] = {"n": int(tam)}
    for k, fila in esc.iterrows():
        k = k if isinstance(k, tuple) else (k,)
        if out[k]["n"] < MIN_PERFIL:
            continue
        d = {}
        for nom, col, _fam in ESCALARES:
            v = fila[col]
            if pd.isna(v):
                continue
            d[nom] = round(float(v) * (1 if nom in NO_PORCENTAJE else 100),
                           2 if nom in NO_PORCENTAJE else 1)
        out[k].update(d)
    for nom, col, etiq, uni in DISTRIB:
        sub = df if uni is None else df[UNIVERSOS[uni](df)]
        if not len(sub):
            continue
        vc = (sub.groupby(claves, observed=True)[col]
              .value_counts(normalize=True).mul(100).round(1))
        for idx, val in vc.items():
            k, cat = (idx[:-1], idx[-1])
            if k not in out or out[k]["n"] < MIN_PERFIL or val < 0.05:
                continue
            cat = str(cat)
            # "4.0" -> "4": las categoricas numericas llegan como float y sin
            # esto la etiqueta no resuelve y sale el numero crudo en la pagina
            entero = cat
            try:                      # "4.0" -> "4"; "0-14" no es un numero
                entero = str(int(float(cat)))
                if not etiq:
                    cat = entero
            except ValueError:
                pass
            if etiq:
                cat = etiq.get(entero, cat)
            out[k].setdefault(nom, {})[cat] = float(val)
    for k in out:
        if "edad_num" in out[k]:
            del out[k]["edad_num"]
    # la mediana de edad va aparte: no es un promedio
    med = g.edad_num.median()
    for k, v in med.items():
        k = k if isinstance(k, tuple) else (k,)
        if out[k]["n"] >= MIN_PERFIL and pd.notna(v):
            out[k]["edad_mediana"] = float(v)
    return out


def a_lista(d, campos):
    return [dict(zip(campos, k)) | v for k, v in sorted(d.items(), key=lambda t: -t[1]["n"])]


# ═══════════════════ REFERENCIAS ═══════════════════
print("\nreferencias…")
b["_todo"] = "region"
ref_region = calcular(b, ["_todo"])[("region",)]
ref_mun = calcular(b, ["cod_ine"])
ref_nativo = calcular(b[b.orig_res5.eq("aqui")], ["cod_ine"])
referencias = {
    "region": ref_region,
    "municipio": {k[0]: v for k, v in ref_mun.items()},
    "nativo_del_municipio": {k[0]: v for k, v in ref_nativo.items()},
}
print(f"  región n={ref_region['n']:,} · {ref_region['anios_estudio']} años de estudio "
      f"· quintil medio {ref_region['quintil_medio']}")

# ═══════════════════ A · MIGRACIÓN 2019 → 2024 ═══════════════════
print("\nA · migración por residencia hace 5 años…")
mig = b[~b.orig_res5.isin(["aqui", "nonato"])].copy()
mig["fam"] = [familia_lugar(o, c) for o, c in zip(mig.orig_res5, mig.cod_ine)]
cel_res = calcular(mig, ["cod_ine", "orig_res5"])
fam_res = calcular(mig, ["cod_ine", "fam"])
reg_res = calcular(mig, ["orig_res5"])
print(f"  celdas municipio×origen: {len(cel_res):,} "
      f"(con perfil completo: {sum(1 for v in cel_res.values() if v['n']>=MIN_PERFIL):,})")

# ═══════════════════ B · MIGRACIÓN DE TODA LA VIDA ═══════════════════
print("B · migración por lugar de nacimiento…")
nac = b[~b.orig_nac.isin(["aqui"])].copy()
nac["fam"] = [familia_lugar(o, c) for o, c in zip(nac.orig_nac, nac.cod_ine)]
cel_nac = calcular(nac, ["cod_ine", "orig_nac"])
fam_nac = calcular(nac, ["cod_ine", "fam"])
print(f"  celdas: {len(cel_nac):,} "
      f"(con perfil: {sum(1 for v in cel_nac.values() if v['n']>=MIN_PERFIL):,})")

# ═══════════════════ C · CONMUTACIÓN ═══════════════════
print("C · conmutación…")
tra = b[b.ocupado & b.trab_donde.ne("sd")].copy()
cel_tra = calcular(tra, ["cod_ine", "dest_trab"])
est_tra = calcular(tra, ["cod_ine", "trab_donde"])
print(f"  celdas residencia×trabajo: {len(cel_tra):,} "
      f"(con perfil: {sum(1 for v in cel_tra.values() if v['n']>=MIN_PERFIL):,})")

# ═══════════════════ C-bis · EL EXTERIOR SON DOS MIGRACIONES ═══════════════
# ★ HALLAZGO 2026-08-26. Los 24.672 que vivían en otro país en 2019 no son un
#   grupo: son dos que no tienen nada que ver entre sí.
#     · 11.931 (48,4%) NACIERON EN BOLIVIA — son retornados.
#     · 12.741 (51,6%) nacieron afuera — son extranjeros.
#   Promediarlos es el mismo error que promediar los cinco orígenes, un nivel
#   más abajo. Y arruina justo el indicador más fuerte:
#
#   ⛔ `p28_cn` pregunta si el nacimiento está inscrito en el registro civil
#      **BOLIVIANO**. Que un peruano conteste «no» es la respuesta correcta y
#      esperable, NO una carencia. Publicar «31,5% del exterior sin registro
#      civil» sería convertir el enunciado de una pregunta en un problema social
#      inexistente. El indicador que SÍ dice algo es `p29_ci`, la cédula: entre
#      los nacidos afuera y mayores de edad, el 24,1% no tiene NINGÚN documento
#      de identidad boliviano — ni cédula nacional ni cédula de extranjero.
print("C-bis · el exterior, partido en retornados y extranjeros…")
ext = b[b.orig_res5.str.startswith("pais:")].copy()
ext["subgrupo"] = np.where(ext.orig_nac.str.startswith("pais:"),
                           "extranjero", "retornado")
ext["pais"] = ext.orig_res5
sub_ext = calcular(ext, ["subgrupo"])
sub_ext_mun = calcular(ext, ["cod_ine", "subgrupo"])
sub_ext_pais = calcular(ext, ["subgrupo", "pais"])
print(f"  retornados {sub_ext[('retornado',)]['n']:,} · "
      f"extranjeros {sub_ext[('extranjero',)]['n']:,}")

# ═══════════════════ D · COHORTES: LA CURVA DE ASIMILACIÓN ═══════════════════
print("D · cohortes de llegada…")
llg = b[b.anio_llegada.notna() & ~b.orig_res5.eq("nonato")].copy()
llg["cohorte"] = pd.cut(llg.anio_llegada, [1929, 1999, 2009, 2014, 2019, 2022, 2024],
                        labels=["antes de 2000", "2000-2009", "2010-2014",
                                "2015-2019", "2020-2022", "2023-2024"])
llg["fam_nac"] = [familia_lugar(o, c) for o, c in zip(llg.orig_nac, llg.cod_ine)]
# el retornado es boliviano de nacimiento: su cohorte no dice lo mismo que la de
# un extranjero, así que se separa también acá
llg.loc[llg.orig_res5.str.startswith("pais:") & llg.fam_nac.ne("exterior"),
        "fam_nac"] = "retornado"
coh = calcular(llg[llg.fam_nac.ne("aqui")], ["fam_nac", "cohorte"])
coh_reg = calcular(llg, ["cohorte"])
print(f"  celdas de cohorte: {len(coh):,}  ·  con año declarado: {len(llg):,}")

# ═══════════════════ salidas ═══════════════════
etiquetas = {
    "municipios": N9,
    "lugares": {c: etiqueta_lugar(c) for c in sorted(
        {k[1] for k in list(cel_res) + list(cel_nac) + list(cel_tra)}
        | {k[0] for k in list(reg_res)})},
    "familias": {"aqui": "Ya estaba aquí", "region": "Otro municipio de la región",
                 "scz": "Resto de Santa Cruz", "scz_parcial": "Santa Cruz, sin precisar",
                 "dep": "Otro departamento", "dep_parcial": "Otro departamento, sin precisar",
                 "exterior": "Otro país", "nonato": "Aún no había nacido",
                 "sd": "Sin especificar"},
    "huella": HUELLA,
    "familias_de_indicadores": {
        "1": "Quién es", "2": "Qué sabe", "3": "De qué vive",
        "4": "Cómo vive", "5": "Con qué cuenta", "6": "Qué le falta"},
    "indicadores": {nom: {"familia": fam, "es_porcentaje": nom not in NO_PORCENTAJE}
                    for nom, _c, fam in ESCALARES},
}

def guardar(nombre, obj):
    p = SAL / f"{nombre}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                 encoding="utf-8")
    print(f"  ✔ {p.name:34} {p.stat().st_size/1024:8.0f} KB")


print("\nescribiendo…")
guardar("referencias", referencias)
guardar("etiquetas", etiquetas)
guardar("mig_residencia", {
    "celdas": a_lista(cel_res, ["destino", "origen"]),
    "familias": a_lista(fam_res, ["destino", "familia"]),
    "region": a_lista(reg_res, ["origen"])})
guardar("mig_nacimiento", {
    "celdas": a_lista(cel_nac, ["destino", "origen"]),
    "familias": a_lista(fam_nac, ["destino", "familia"])})
guardar("conmutacion", {
    "celdas": a_lista(cel_tra, ["residencia", "trabajo"]),
    "estados": a_lista(est_tra, ["residencia", "estado"])})
guardar("exterior", {
    "subgrupo": a_lista(sub_ext, ["subgrupo"]),
    "por_municipio": a_lista(sub_ext_mun, ["destino", "subgrupo"]),
    "por_pais": a_lista(sub_ext_pais, ["subgrupo", "pais"])})
guardar("cohortes", {
    "celdas": a_lista(coh, ["origen", "cohorte"]),
    "region": a_lista(coh_reg, ["cohorte"])})
print("\nlisto.")
