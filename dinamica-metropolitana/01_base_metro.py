# -*- coding: utf-8 -*-
"""PASO 1 — LA TABLA BASE DE LA REGIÓN METROPOLITANA.

Una sola pasada por `Persona_CPV-2024.csv` (3,1 GB, 11.365.333 filas) quedándose
con los residentes de los NUEVE municipios, unida a `Vivienda_CPV-2024.csv` por la
llave `hogar`. Sale `base9_metro.parquet`, de donde salen TODOS los cortes de
composición sin volver a tocar el crudo.

★ POR QUÉ NO ALCANZA `persona_full.parquet`
  Ese parquet tiene 51 columnas ya derivadas y es rapidísimo, pero le faltan
  justamente las que necesita un análisis de composición de flujos:
    · `p361_anres` — el año desde el que reside (habilita COHORTES de llegada)
    · `p373_paisres5_cod` / `p353_paisnac_cod` — el país de origen
    · `dep_res5_cod` / `prov_res5_cod` — sin ellos NO se pueden rescatar los
      parciales (`XX9999`, `XXYY99`), que es el error nº2 de la auditoría
    · `p52_mov` — colapsado; por eso hoy es invisible quien trabaja EN su vivienda
    · `condact_13` — sin él no hay desocupados
    · TODA la Vivienda: materiales, agua, saneamiento, energía, combustible,
      basura, hacinamiento y los 18 bienes. Es decir: las «necesidades».

★ LAS TRES DIMENSIONES DE FLUJO, y sus universos, que NO son intercambiables
    nacimiento  `p35_lugnac`   stock sin fecha       — 2.282.770 residentes
    residencia  `p37_lugres5`  flujo fechado 19→24   — excluye a los no nacidos
    trabajo     `p52_mov`      desplazamiento diario — NO es migración
  Ver [[reference_conmutacion-universos]].

★ NADA SE DESCARTA POR SER PARCIAL. `XX9999` y `XXYY99` son códigos VÁLIDOS del
  INE, no datos faltantes. Cada dimensión guarda además su `*_nivel`
  (municipio / provincia / departamento / pais / sd) para que la precisión de la
  respuesta sea un dato explícito y no una pérdida silenciosa.
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

RAW = pathlib.Path(r"C:\Users\HP\cpv2024")
REPO = pathlib.Path(r"C:\Users\HP\OneDrive\Desktop\Proyectos\scz-metropolitana-gobernacion")
SALIDA = RAW / "base9_metro.parquet"          # fuera del repo: es microdato

N9 = {m["cod_ine"]: m["nombre"] for m in
      json.loads((REPO / "datos" / "municipios.json").read_text(encoding="utf-8"))}
print(f"los nueve: {', '.join(N9.values())}")

# ── columnas del censo de personas ──────────────────────────────────────────
COLS_P = [
    # llaves
    "idep", "iprov", "imun", "i00",
    # demografía y hogar
    "p24_parentes", "p25_sexo", "p26_edad", "p53_ecivil",
    # documentación
    "p28_cn", "p29_ci",
    # salud: a dónde acude y con qué cobertura
    "p30a_public", "p30b_caja", "p30c_privad", "p30d_atedom",
    "p30e_tradic", "p30f_autome", "p30g_casera",
    "p31_afiliado", "p31_cobersalud",
    # identidad
    "p32_pueblos", "idioma_mat", "idioma_mayor_uso",
    # NACIMIENTO
    "p35_lugnac", "dep_nac_cod", "prov_nac_cod", "mun_nac_cod",
    "p353_paisnac_cod", "p354_anllega",
    # residencia habitual y año desde el que reside
    "p36_lugres", "p361_anres",
    # RESIDENCIA HACE 5 AÑOS
    "p37_lugres5", "dep_res5_cod", "prov_res5_cod", "mun_res5_cod",
    "p373_paisres5_cod",
    # educación
    "p38_asiste", "p39_tipoest", "p40_lee", "p41a_nivel_act",
    "nivel_edu", "aestudio", "asiste",
    # discapacidad
    "p42_discap",
    # TRABAJO
    "p46_dest", "p48_nocu", "p52_mov",
    "dep_lab_cod", "prov_lab_cod", "mun_lab_cod", "p52_pais_mov_cod",
    "condact_13", "pet_13", "ocu_1d_13", "p50_catocu_13", "act_eco_2d_13",
]

# ── columnas de la vivienda: acá viven las NECESIDADES ──────────────────────
COLS_V = [
    "idep", "iprov", "imun", "i00", "urbrur",
    "v01_tipoviv", "v02_condocup",
    "v03_pared", "v04_revoq", "v05_techo", "v06_piso",          # materiales
    "v07_aguapro", "v08_aguadist",                              # agua
    "v09_energia", "v10_combus", "v11_basura",                  # energía y residuos
    "v12_cocina", "v13_habitac", "v14_dormit",                  # espacio
    "v15_servsan", "v16_desague",                               # saneamiento
    "v17_tenencia",                                             # tenencia
    "v18a_bici", "v18b_moto", "v18c_auto", "v18d_carreta",
    "v18f_refri", "v18g_micro", "v18h_calefon", "v18i_aire", "v18j_lavadora",
    "v19a_radio", "v19b_tv", "v19c_compu", "v19d_celular",
    "v19e_inetfijo", "v19f_inetmovil", "v19g_tvcable",
    "v20a_emi", "v20b_totemi", "tot_pers", "tip_hog",
]


def llave_hogar(df):
    """dep sin cero + prov + mun + i00, como entero. Es la llave que ya usa el
    parquet del censo y pega el 97,8% (verificado con assert más abajo)."""
    return (df.idep.astype(int).astype(str)
            + df.iprov.str.zfill(2)
            + df.imun.str.zfill(2)
            + df.i00.str.zfill(8)).astype("int64")


# ═══════════════════════ 1 · PERSONAS ═══════════════════════
print("\nleyendo Persona_CPV-2024.csv (3,1 GB)…", flush=True)
trozos, leidas = [], 0
for ch in pd.read_csv(RAW / "Persona_CPV-2024.csv", sep=";", usecols=COLS_P,
                      dtype=str, chunksize=600_000, low_memory=False):
    leidas += len(ch)
    ch["cod_ine"] = (ch.idep.str.zfill(2) + ch.iprov.str.zfill(2)
                     + ch.imun.str.zfill(2))
    ch = ch[ch.cod_ine.isin(N9)]
    if len(ch):
        ch["hogar"] = llave_hogar(ch)
        trozos.append(ch.drop(columns=["idep", "iprov", "imun", "i00"]))
    print(f"  {leidas:>11,} filas leídas · {sum(map(len, trozos)):>9,} en los nueve",
          end="\r", flush=True)
p = pd.concat(trozos, ignore_index=True)
del trozos
print(f"\npersonas censadas en los nueve municipios: {len(p):,}")

# ═══════════════════════ 2 · VIVIENDAS ═══════════════════════
print("\nleyendo Vivienda_CPV-2024.csv (490 MB) por trozos…", flush=True)
trozos = []
for ch in pd.read_csv(RAW / "Vivienda_CPV-2024.csv", sep=";", usecols=COLS_V,
                      dtype=str, chunksize=300_000, low_memory=False):
    ch["c"] = ch.idep.str.zfill(2) + ch.iprov.str.zfill(2) + ch.imun.str.zfill(2)
    ch = ch[ch.c.isin(N9)]
    if len(ch):
        ch["hogar"] = llave_hogar(ch)
        trozos.append(ch.drop(columns=["idep", "iprov", "imun", "i00", "c"]))
v = pd.concat(trozos, ignore_index=True)
del trozos
v = v.drop_duplicates(subset="hogar")
print(f"viviendas en los nueve municipios: {len(v):,}")

b = p.merge(v, on="hogar", how="left", validate="m:1")
del p, v
pegue = 100 * b.urbrur.notna().mean()
print(f"pegue Persona × Vivienda: {pegue:.2f}%")
assert pegue > 95, f"el pegue cayó a {pegue:.1f}% — la llave `hogar` cambió"

# ═══════════════════════ 3 · DERIVADAS ═══════════════════════
print("\nderivando…", flush=True)
num = lambda s: pd.to_numeric(s, errors="coerce")
si = lambda s: s.eq("1")          # las dicotómicas del censo son 1=Sí 2=No

b["edad"] = num(b.p26_edad)
b["mujer"] = b.p25_sexo.eq("2")
b["jefe"] = b.p24_parentes.eq("1")
b["anios_estudio"] = num(b.aestudio)

# ── clasificación de los TRES flujos ────────────────────────────────────────
#   ⛔ LOS DOS CÓDIGOS QUE PARECEN GEOGRAFÍA Y NO LO SON
#   `999995` (lugar de trabajo) y `999999` (nacimiento y residencia-5) son
#   «Sin especificar» en el diccionario del INE. Con zfill(6) el segundo pasa el
#   patrón `XX9999` y sale clasificado como **departamento 99**: son 27.720
#   personas que aparecerían «trabajando en otro municipio» sin trabajar en
#   ninguno declarado. Ojo que `099999` SÍ es geografía — «Pando sin provincia y
#   municipio especificado» — así que el filtro va sobre el código crudo, no
#   sobre los dos primeros dígitos.
SIN_ESPECIFICAR = {"999995", "999999"}


def cod6(s):
    """Los códigos de municipio vienen sin el cero de adelante (21701 → 021701)."""
    c = num(s).astype("Int64").astype(str).str.zfill(6).where(s.notna())
    return c.where(~c.isin(SIN_ESPECIFICAR))


b["mun_nac"] = cod6(b.mun_nac_cod)
b["mun_res5"] = cod6(b.mun_res5_cod)
b["mun_lab"] = cod6(b.mun_lab_cod)


def clasificar(lugar, mun, pais, cod_ine, cod_nonato=None):
    """Devuelve (origen, nivel_de_precisión).

    ⚠️ ESTE ES EL ARREGLO DEL ERROR Nº1 Y Nº2 DE LA AUDITORÍA. La versión vieja
    miraba SÓLO el código de municipio: quien vivía en otro país no tiene ninguno
    (`mun_res5` viene vacío para los 24.672) y caía en «sin dato», igual que los
    11.163 que declararon departamento sin municipio. Acá el país se lee de su
    propia variable y el parcial se reconoce por el patrón del código.
    """
    origen = pd.Series(pd.NA, index=lugar.index, dtype="object")
    nivel = pd.Series(pd.NA, index=lugar.index, dtype="object")

    if cod_nonato is not None:                       # sólo residencia-5
        m = lugar.eq(cod_nonato)
        origen[m], nivel[m] = "nonato", "nonato"

    m = lugar.eq("1")                                # aquí, en este municipio
    origen[m], nivel[m] = "aqui", "municipio"

    # otro país. Los 472 que vivían afuera y NO precisaron cuál siguen siendo
    # exterior: lo que falta es el país, no el hecho de haber estado afuera.
    # Mandarlos a «sd» rompería el total de 24.672 que cierra contra el censo.
    m = lugar.eq("3")
    origen[m] = np.where(pais[m].notna() & ~pais[m].isin(["999", "998"]),
                         "pais:" + pais[m].fillna("999").str.zfill(3), "pais:sd")
    nivel[m] = np.where(pais[m].notna() & ~pais[m].isin(["999", "998"]),
                        "pais", "pais_sin_precisar")

    m = lugar.eq("2") & mun.notna()                  # otro municipio del país
    cod = mun[m]
    dep_sd = cod.str[2:].eq("9999")                  # XX9999 · dep sin más detalle
    prov_sd = ~dep_sd & cod.str[4:].eq("99")         # XXYY99 · prov sin municipio
    exacto = ~dep_sd & ~prov_sd
    origen.loc[m] = np.where(dep_sd, "dep:" + cod.str[:2],
                    np.where(prov_sd, "prov:" + cod.str[:4], "mun:" + cod))
    nivel.loc[m] = np.where(dep_sd, "departamento",
                   np.where(prov_sd, "provincia", "municipio"))
    _ = exacto

    origen = origen.fillna("sd")
    nivel = nivel.fillna("sd")
    # quien declaró el propio municipio por la vía larga
    propio = origen.eq("mun:" + cod_ine)
    origen[propio] = "aqui"
    return origen, nivel


b["orig_nac"], b["nivel_nac"] = clasificar(
    b.p35_lugnac, b.mun_nac, b.p353_paisnac_cod, b.cod_ine)
b["orig_res5"], b["nivel_res5"] = clasificar(
    b.p37_lugres5, b.mun_res5, b.p373_paisres5_cod, b.cod_ine, cod_nonato="4")

# ── trabajo: p52_mov manda, el municipio precisa ────────────────────────────
b["trab_donde"] = b.p52_mov.map({"1": "en_la_vivienda", "2": "mismo_municipio",
                                 "3": "otro_municipio", "4": "otro_pais"}).fillna("sd")
dst = pd.Series(pd.NA, index=b.index, dtype="object")
niv = pd.Series(pd.NA, index=b.index, dtype="object")
m = b.trab_donde.isin(["en_la_vivienda", "mismo_municipio"])
dst[m], niv[m] = "mun:" + b.cod_ine[m], "municipio"
m = b.trab_donde.eq("otro_municipio") & b.mun_lab.notna()
cod = b.mun_lab[m]
dep_sd = cod.str[2:].eq("9999")
prov_sd = ~dep_sd & cod.str[4:].eq("99")
dst.loc[m] = np.where(dep_sd, "dep:" + cod.str[:2],
              np.where(prov_sd, "prov:" + cod.str[:4], "mun:" + cod))
niv.loc[m] = np.where(dep_sd, "departamento",
             np.where(prov_sd, "provincia", "municipio"))
m = b.trab_donde.eq("otro_pais")
dst[m], niv[m] = "pais:" + b.p52_pais_mov_cod[m].fillna("999").str.zfill(3), "pais"
b["dest_trab"] = dst.fillna("sd")
b["nivel_trab"] = niv.fillna("sd")

# ── condición laboral ───────────────────────────────────────────────────────
b["ocupado"] = b.condact_13.eq("1")
b["desocupado"] = b.condact_13.isin(["2", "3"])
b["pet"] = b.pet_13.eq("1") & b.edad.ge(15)          # ⚠️ el error nº3: MISMO
b["inactivo"] = b.condact_13.eq("4")                 #    universo arriba y abajo
b["rama"] = num(b.act_eco_2d_13)
b["ocu1d"] = num(b.ocu_1d_13)
b["catocu"] = num(b.p50_catocu_13)
b["conmuta"] = b.trab_donde.eq("otro_municipio")

# ── educación ───────────────────────────────────────────────────────────────
b["superior"] = b.nivel_edu.eq("4")
b["sin_nivel"] = b.nivel_edu.eq("1")
b["asiste_si"] = b.asiste.eq("1")
b["asiste_privado"] = b.p39_tipoest.eq("2")
b["analfabeto"] = b.p40_lee.eq("2") & b.edad.ge(15)

# ── salud, documentación, identidad ─────────────────────────────────────────
b["sin_seguro"] = b.p31_cobersalud.eq("2")
b["sin_cedula"] = b.p29_ci.eq("2")
b["cedula_extranjero"] = b.p29_ci.eq("3")
b["sin_registro"] = b.p28_cn.eq("2")
b["discap"] = b.p42_discap.eq("1")
# ⚠️ `p32_pueblos` NO es un sí/no: su 1 es *Afroboliviano* y su 98 «no se
#    autoidentifica». Medirlo como == "1" da 0,2% y es basura.
b["indigena"] = (~b.p32_pueblos.isin(["98", "99"])) & b.p32_pueblos.notna()
b["salud_publica"] = si(b.p30a_public)
b["salud_caja"] = si(b.p30b_caja)
b["salud_privada"] = si(b.p30c_privad)
b["salud_tradicional"] = si(b.p30e_tradic)
b["salud_automedica"] = si(b.p30f_autome) | si(b.p30g_casera)

# ── vivienda y NECESIDADES ──────────────────────────────────────────────────
b["urbano"] = b.urbrur.eq("1")
b["agua_red"] = b.v07_aguapro.eq("1")
b["agua_dentro"] = b.v08_aguadist.eq("1")
b["agua_insegura"] = b.v07_aguapro.isin(["5", "7"])         # pozo sin proteger, río
b["alcantarillado"] = b.v16_desague.eq("1")
b["sin_bano"] = b.v15_servsan.eq("3")
b["bano_compartido"] = b.v15_servsan.eq("2")
b["desague_superficie"] = b.v16_desague.eq("5")
b["energia_red"] = b.v09_energia.eq("1")
b["sin_energia"] = b.v09_energia.eq("5")
b["cocina_lena"] = b.v10_combus.isin(["3", "4"])            # leña, guano
b["basura_quema"] = b.v11_basura.isin(["5", "6"])
b["basura_calle"] = b.v11_basura.isin(["3", "4"])
b["basura_servicio"] = b.v11_basura.isin(["1", "2"])
b["piso_tierra"] = b.v06_piso.eq("1")
b["pared_precaria"] = b.v03_pared.isin(["3", "6"])          # tabique/quinche, caña
b["pared_ladrillo"] = b.v03_pared.eq("1")
b["techo_precario"] = b.v05_techo.eq("4")                   # paja, palma, barro
b["sin_cuarto_cocina"] = b.v12_cocina.eq("2")

dorm = num(b.v14_dormit)
tot = num(b.tot_pers)
b["pers_por_dormitorio"] = (tot / dorm.replace(0, np.nan))
b["hacinamiento"] = b.pers_por_dormitorio.gt(3)             # umbral clásico del INE
b["pers_por_habitacion"] = tot / num(b.v13_habitac)
b["tot_pers_hog"] = tot

b["propia"] = b.v17_tenencia.isin(["1", "2"])
b["alquila"] = b.v17_tenencia.eq("4")
b["prestada"] = b.v17_tenencia.eq("3")
for col, nom in [("v18a_bici", "bici"), ("v18b_moto", "moto"), ("v18c_auto", "auto"),
                 ("v18f_refri", "refri"), ("v18j_lavadora", "lavadora"),
                 ("v18i_aire", "aire"), ("v19c_compu", "compu"),
                 ("v19f_inetmovil", "inet_movil"), ("v19e_inetfijo", "inet_fijo"),
                 ("v19b_tv", "tv")]:
    b[nom] = si(b[col])
b["hogar_emigro"] = si(b.v20a_emi)

# ── cohorte de llegada ──────────────────────────────────────────────────────
anio = num(b.p361_anres)
b["anio_llegada"] = anio.where(anio.between(1930, 2024))
b["anio_llega_bolivia"] = num(b.p354_anllega).where(
    num(b.p354_anllega).between(1930, 2024))

# ── se guarda ───────────────────────────────────────────────────────────────
# Las CRUDAS que se conservan son las que hacen falta como DISTRIBUCIÓN
# completa (no alcanza el booleano derivado): el reparto por nivel educativo,
# por fuente de agua, por tipo de desagüe, por combustible, por material.
CONSERVAR = {
    "p24_parentes", "p31_afiliado", "p32_pueblos", "p35_lugnac", "p36_lugres",
    "p37_lugres5", "p38_asiste", "p39_tipoest", "p41a_nivel_act", "p46_dest",
    "p48_nocu", "p52_mov", "p53_ecivil",
    "v01_tipoviv", "v02_condocup", "v03_pared", "v04_revoq", "v05_techo",
    "v06_piso", "v07_aguapro", "v08_aguadist", "v09_energia", "v10_combus",
    "v11_basura", "v15_servsan", "v16_desague", "v17_tenencia",
}
CRUDAS = [c for c in b.columns if c.startswith(("p2", "p3", "p4", "p5", "v0", "v1", "v2"))
          and c not in CONSERVAR]
b = b.drop(columns=CRUDAS + ["mun_nac_cod", "mun_res5_cod", "mun_lab_cod",
                             "dep_nac_cod", "prov_nac_cod", "dep_res5_cod",
                             "prov_res5_cod", "dep_lab_cod", "prov_lab_cod",
                             "aestudio", "asiste", "condact_13",
                             "pet_13", "ocu_1d_13", "p50_catocu_13",
                             "act_eco_2d_13", "urbrur", "tot_pers",
                             "idioma_mayor_uso"], errors="ignore")
b.to_parquet(SALIDA, index=False)
print(f"\n✔ {SALIDA}  ·  {len(b):,} filas × {len(b.columns)} columnas "
      f"· {SALIDA.stat().st_size/1e6:.0f} MB")

# ── controles que tienen que cerrar ─────────────────────────────────────────
print("\n── controles ──")
print(f"residentes habituales (p36_lugres=1): {b.p36_lugres.eq('1').sum():,}")
print("\nnacimiento:"); print(b.nivel_nac.value_counts().to_string())
print("\nresidencia 2019:"); print(b.nivel_res5.value_counts().to_string())
print(b.orig_res5.str.split(":").str[0].value_counts().to_string())
print("\nlugar de trabajo:"); print(b.trab_donde.value_counts().to_string())
exterior = b.orig_res5.str.startswith("pais:").sum()
print(f"\n★ llegados del exterior 2019→2024: {exterior:,}  (la web publica 0)")
