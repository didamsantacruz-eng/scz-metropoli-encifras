# -*- coding: utf-8 -*-
"""PASO 2 — NIVEL DE VIDA DE CADA HOGAR: ÍNDICE DE RIQUEZA Y PRIVACIONES.

⛔ EL LÍMITE QUE MANDA SOBRE TODO LO DEMÁS
   El Censo 2024 **no pregunta ingreso**. Se revisaron las 114 variables de
   persona y las 44 de vivienda: no hay ninguna. Por lo tanto, cualquier cifra en
   bolivianos tendría que venir de fuera del censo (ver el escalón 3 al final).
   Lo que sigue mide **nivel de vida material**, que es lo que el censo sí sabe.

═══════════════════════════════════════════════════════════════════════════════
A · ÍNDICE DE RIQUEZA POR COMPONENTES PRINCIPALES
    Filmer & Pritchett (2001), «Estimating wealth effects without expenditure
    data — or tears», Demography 38(1). Es el método diseñado justamente para
    fuentes sin ingreso, y es el que usa el índice de riqueza del DHS.

    Idea: los activos, materiales y servicios del hogar son manifestaciones de
    una misma variable latente — el nivel de vida. El primer componente principal
    de esa batería es la mejor estimación lineal de esa variable latente.

★ LA CORRECCIÓN URBANO/RURAL — Rutstein (2008), DHS Working Paper 60.
  Un ACP único sobre una región mixta tiene sesgo urbano: los activos urbanos
  (internet fijo, alcantarillado, TV cable) dominan el primer componente y el
  hogar rural sale artificialmente pobre porque se lo mide con una vara que no
  es la suya. El procedimiento del DHS, que es el que se aplica acá:
     1. ACP «común» sobre las variables comparables entre las dos áreas.
     2. ACP propio del área urbana y ACP propio del área rural.
     3. Se regresa el puntaje común sobre el puntaje del área, dentro del área,
        y el VALOR PREDICHO es el puntaje combinado. Así los dos quedan en la
        misma escala sin borrar la vara propia de cada área.
     4. Quintiles sobre el puntaje combinado de toda la región.

  ⚠️ El índice es **ORDINAL**. Ubica hogares en una escala, no dice bolivianos.
     «Quintil 5» significa «entre el 20% con más activos de esta región», no un
     monto. Decir lo contrario sería inventar.

═══════════════════════════════════════════════════════════════════════════════
B · PRIVACIONES, EN LAS DIMENSIONES DEL NBI
    El NBI oficial del INE Bolivia (adaptado de CEPAL) normaliza cada dimensión
    contra una norma mínima y agrega en un índice con cinco estratos.

★ ACÁ NO SE CALCULA «EL NBI OFICIAL», Y ES A PROPÓSITO.
  Los umbrales y las normas exactas del INE no están en el diccionario del censo,
  y ponerles un número inventado para poder rotular el resultado «NBI» sería
  exactamente el error de deducir en vez de declarar. Lo que se publica acá son
  las **privaciones una por una, con su umbral escrito al lado**, en las mismas
  seis dimensiones del NBI, más su conteo. Es transparente, es auditable y no
  se disfraza de oficial.

═══════════════════════════════════════════════════════════════════════════════
C · CAPACIDAD DE PAGO REVELADA
    En vez de estimar un ingreso y aplicarle un umbral de asequibilidad, se lee
    lo que el hogar **ya sostiene de hecho**. Internet fijo, TV por cable, aire
    acondicionado y lavadora no son necesidades: son gastos voluntarios y
    recurrentes. Sostenerlos es evidencia directa de capacidad de pago, y no
    necesita ningún supuesto sobre el ingreso.
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

RAW = pathlib.Path(r"C:\Users\HP\cpv2024")
AQUI = pathlib.Path(__file__).resolve().parent
BASE = RAW / "base9_metro.parquet"
SALIDA = RAW / "base9_metro_nivelvida.parquet"

b = pd.read_parquet(BASE)
print(f"base: {len(b):,} personas × {len(b.columns)} columnas")

# ═══════════════════ el hogar, que es la unidad del índice ═══════════════════
# El índice de riqueza es una propiedad del HOGAR, no de la persona: se calcula
# una vez por hogar y después se le reparte a cada uno de sus miembros.
COLS_HOG = ["hogar", "urbano", "tot_pers_hog", "pers_por_dormitorio",
            "v01_tipoviv", "v03_pared", "v05_techo", "v06_piso", "v07_aguapro",
            "v10_combus", "v11_basura", "v16_desague", "v17_tenencia",
            "agua_dentro", "alcantarillado", "sin_bano", "bano_compartido",
            "desague_superficie", "energia_red", "sin_energia", "cocina_lena",
            "basura_quema", "basura_calle", "basura_servicio", "piso_tierra",
            "pared_precaria", "pared_ladrillo", "techo_precario",
            "sin_cuarto_cocina", "hacinamiento", "agua_red", "agua_insegura",
            "propia", "alquila", "prestada", "bici", "moto", "auto", "refri",
            "lavadora", "aire", "compu", "inet_movil", "inet_fijo", "tv"]
h = b[COLS_HOG].drop_duplicates(subset="hogar").reset_index(drop=True)
print(f"hogares: {len(h):,}  ·  urbanos {100*h.urbano.mean():.1f}%")

# ── la batería de variables del índice ──────────────────────────────────────
# Todas entran como 0/1 salvo el hacinamiento, que entra estandarizado.
def d(serie, *valores):
    return serie.isin([str(v) for v in valores]).astype(float)


X = pd.DataFrame(index=h.index)
# bienes durables — el corazón del índice
for c in ["bici", "moto", "auto", "refri", "lavadora", "aire", "compu",
          "inet_movil", "inet_fijo", "tv"]:
    X[f"bien_{c}"] = h[c].astype(float)
# materiales
X["pared_ladrillo"] = h.pared_ladrillo.astype(float)
X["pared_adobe"] = d(h.v03_pared, 2)
X["pared_precaria"] = h.pared_precaria.astype(float)
X["techo_losa"] = d(h.v05_techo, 3)
X["techo_teja"] = d(h.v05_techo, 2)
X["techo_precario"] = h.techo_precario.astype(float)
X["piso_tierra"] = h.piso_tierra.astype(float)
X["piso_ceramica"] = d(h.v06_piso, 4, 6, 8)
X["piso_cemento"] = d(h.v06_piso, 5)
# servicios
X["agua_red"] = h.agua_red.astype(float)
X["agua_dentro"] = h.agua_dentro.astype(float)
X["agua_insegura"] = h.agua_insegura.astype(float)
X["alcantarillado"] = h.alcantarillado.astype(float)
X["camara_septica"] = d(h.v16_desague, 2)
X["sin_bano"] = h.sin_bano.astype(float)
X["energia_red"] = h.energia_red.astype(float)
X["cocina_gas_red"] = d(h.v10_combus, 2)
X["cocina_lena"] = h.cocina_lena.astype(float)
X["basura_servicio"] = h.basura_servicio.astype(float)
# espacio y tenencia
X["sin_cuarto_cocina"] = h.sin_cuarto_cocina.astype(float)
X["propia"] = h.propia.astype(float)
X["alquila"] = h.alquila.astype(float)
pd_ = h.pers_por_dormitorio.clip(upper=10)
X["pers_dormitorio"] = pd_.fillna(pd_.median())

# ★ las «comunes»: las que significan lo mismo en la ciudad y en el campo.
#   Internet fijo, TV cable o alcantarillado NO son comunes — su ausencia en el
#   campo dice más de la red que del hogar.
COMUNES = [c for c in X.columns if c.startswith("bien_")] + [
    "pared_ladrillo", "pared_precaria", "techo_precario", "piso_tierra",
    "piso_ceramica", "agua_insegura", "sin_bano", "energia_red",
    "cocina_lena", "sin_cuarto_cocina", "pers_dormitorio"]
COMUNES = [c for c in COMUNES if c not in ("bien_inet_fijo",)]
print(f"\nvariables del índice: {len(X.columns)}  ·  comunes: {len(COMUNES)}")


def acp_primer_componente(M):
    """Primer componente principal sobre variables ESTANDARIZADAS.

    Es la descomposición propia de la matriz de correlación — que es lo que hace
    el ACP del DHS. Se escribe a mano en numpy en vez de traer una dependencia,
    para que el método quede a la vista y sea auditable.
    """
    M = M.astype(float).to_numpy()
    mu = M.mean(0)
    sd = M.std(0, ddof=1)
    sd[sd == 0] = 1.0                       # una constante no aporta varianza
    Z = (M - mu) / sd
    C = np.cov(Z, rowvar=False)
    val, vec = np.linalg.eigh(C)            # eigh: matriz simétrica, valores ↑
    orden = np.argsort(val)[::-1]
    val, vec = val[orden], vec[:, orden]
    v1 = vec[:, 0]
    # el signo del autovector es arbitrario: se ancla a que «más activos = más
    # riqueza» usando el auto, que es inequívocamente un bien de nivel alto
    puntaje = Z @ v1
    explicada = val[0] / val.sum()
    return puntaje, v1, explicada, mu, sd


# ── 1 · el ACP común ────────────────────────────────────────────────────────
com, cargas_com, exp_com, _, _ = acp_primer_componente(X[COMUNES])
if np.corrcoef(com, X["bien_auto"])[0, 1] < 0:
    com, cargas_com = -com, -cargas_com
print(f"ACP común     · varianza explicada por el 1er componente: {100*exp_com:.1f}%")

# ── 2 · un ACP para cada área, con TODAS las variables ──────────────────────
h["riqueza"] = np.nan
for area, es in [("urbana", h.urbano), ("rural", ~h.urbano)]:
    idx = h.index[es]
    if len(idx) < 200:
        continue
    p, cg, ex, _, _ = acp_primer_componente(X.loc[idx])
    if np.corrcoef(p, X.loc[idx, "bien_auto"])[0, 1] < 0:
        p = -p
    # ── 3 · anclaje del DHS: se regresa el común sobre el propio del área,
    #        DENTRO del área, y el valor predicho es el puntaje combinado.
    a, c0 = np.polyfit(p, com[idx], 1)
    h.loc[idx, "riqueza"] = a * p + c0
    print(f"ACP {area:8} · n={len(idx):>7,} · 1er comp. {100*ex:4.1f}% "
          f"· anclaje: común = {a:+.3f}·propio {c0:+.3f}")

# ── 4 · quintiles regionales, ponderados por PERSONAS ───────────────────────
# El quintil se define sobre la población, no sobre los hogares: si no, un
# quintil de hogares chicos representa menos gente que uno de hogares grandes.
h = h.sort_values("riqueza").reset_index(drop=True)
acum = h.tot_pers_hog.fillna(1).cumsum()
h["quintil"] = np.ceil(5 * acum / acum.iloc[-1]).clip(1, 5).astype(int)
print("\nreparto de PERSONAS por quintil de riqueza:")
print((h.groupby("quintil").tot_pers_hog.sum() / h.tot_pers_hog.sum() * 100)
      .round(1).to_string())

# ═══════════════════ B · PRIVACIONES, con el umbral declarado ═══════════════
# Cada línea es: nombre → (condición, umbral escrito para publicar al lado).
P = pd.DataFrame(index=h.index)
UMBRALES = {}


def priv(nombre, cond, umbral, dimension):
    P[nombre] = cond.astype(bool)
    UMBRALES[nombre] = {"umbral": umbral, "dimension": dimension}


priv("mat_pared", h.pared_precaria, "pared de tabique, quinche, caña, palma o tronco",
     "Vivienda · materiales")
priv("mat_techo", h.techo_precario, "techo de paja, palma, caña, barro, jatata o motacú",
     "Vivienda · materiales")
priv("mat_piso", h.piso_tierra, "piso de tierra", "Vivienda · materiales")
priv("esp_hacinamiento", h.hacinamiento, "más de 3 personas por dormitorio",
     "Vivienda · espacio")
priv("esp_sin_cocina", h.sin_cuarto_cocina, "sin un cuarto exclusivo para cocinar",
     "Vivienda · espacio")
priv("srv_agua", h.agua_insegura | (~h.agua_red & ~h.agua_dentro),
     "el agua no llega por cañería de red ni se distribuye dentro del lote",
     "Servicios básicos")
priv("srv_saneamiento", h.sin_bano | h.desague_superficie,
     "sin baño ni letrina, o desagüe a la calle, quebrada o río", "Servicios básicos")
priv("srv_energia", h.sin_energia, "sin energía eléctrica de ninguna fuente",
     "Servicios básicos")
priv("srv_basura", h.basura_calle,
     "la basura se bota a un terreno baldío, la calle o el río", "Servicios básicos")
priv("ins_combustible", h.cocina_lena, "cocina con leña, guano, bosta o taquia",
     "Insumos energéticos")
h["privaciones_vivienda"] = P.sum(axis=1).astype(int)
print("\nprivaciones del hogar (sobre 10):")
print((h.privaciones_vivienda.value_counts(normalize=True).sort_index() * 100)
      .round(1).to_string())
for c in P.columns:
    h[c] = P[c]

# ═══════════════════ C · CAPACIDAD DE PAGO REVELADA ═════════════════════════
# Gastos recurrentes y VOLUNTARIOS: no son necesidades, se sostienen o no.
VOLUNTARIOS = ["inet_fijo", "aire", "lavadora", "compu"]
h["pagos_voluntarios"] = h[VOLUNTARIOS].sum(axis=1).astype(int)
h["paga_alguno"] = h.pagos_voluntarios.gt(0)
h["paga_tres_o_mas"] = h.pagos_voluntarios.ge(3)
print(f"\ncapacidad de pago revelada · sostiene al menos un servicio voluntario: "
      f"{100*h.paga_alguno.mean():.1f}%  ·  tres o más: {100*h.paga_tres_o_mas.mean():.1f}%")

# ═══════════════════ se pega a las personas ═════════════════════════════════
COLS_NUEVAS = (["hogar", "riqueza", "quintil", "privaciones_vivienda",
                "pagos_voluntarios", "paga_alguno", "paga_tres_o_mas"]
               + list(P.columns))
b = b.merge(h[COLS_NUEVAS], on="hogar", how="left", validate="m:1")
b.to_parquet(SALIDA, index=False)
print(f"\n✔ {SALIDA.name} · {len(b):,} × {len(b.columns)} "
      f"· {SALIDA.stat().st_size/1e6:.0f} MB")

# ── la ficha del método, para publicar al lado del dato ─────────────────────
cargas = (pd.Series(cargas_com, index=COMUNES).sort_values(ascending=False)
          .round(3).to_dict())
ficha = {
    "indice_riqueza": {
        "metodo": "Componentes principales sobre variables estandarizadas",
        "referencia": "Filmer & Pritchett (2001), Demography 38(1); "
                      "corrección urbano/rural de Rutstein (2008), DHS WP 60",
        "variables": len(X.columns),
        "variables_comunes": len(COMUNES),
        "varianza_explicada_comun": round(100 * exp_com, 1),
        "cargas_del_componente_comun": cargas,
        "es_ordinal": True,
        "advertencia": "El índice ordena hogares; NO expresa ingreso. "
                       "«Quintil 5» es «entre el 20% con más activos de la región», "
                       "no un monto en bolivianos.",
    },
    "privaciones": {
        "metodo": "Privaciones declaradas una por una, en las dimensiones del NBI",
        "por_que_no_es_el_nbi_oficial":
            "Los umbrales y normas exactas del NBI del INE no están en el "
            "diccionario del censo. Rotular «NBI» un cálculo con umbrales propios "
            "sería presentar como oficial algo que no lo es.",
        "umbrales": UMBRALES,
    },
    "capacidad_de_pago": {
        "metodo": "Capacidad revelada: servicios de pago voluntario y recurrente "
                  "que el hogar sostiene de hecho",
        "servicios": ["internet fijo", "aire acondicionado", "lavadora de ropa",
                      "computadora"],
        "por_que": "No son necesidades. Sostenerlos es evidencia directa de "
                   "capacidad de pago y no requiere estimar un ingreso.",
    },
    "lo_que_el_censo_no_tiene": {
        "ingreso": "El CPV 2024 no pregunta ingreso ni gasto. Ninguna de sus 114 "
                   "variables de persona ni de sus 44 de vivienda lo mide.",
        "como_se_obtendria": "Estimación por áreas pequeñas (Elbers, Lanjouw & "
                             "Lanjouw 2003): modelo de consumo ajustado en la "
                             "Encuesta de Hogares con variables idénticas al censo, "
                             "predicho sobre el censo, con error estándar por "
                             "bootstrap. Requiere el microdato de la EH (ANDA).",
    },
}
(AQUI / "ficha_metodo_nivelvida.json").write_text(
    json.dumps(ficha, ensure_ascii=False, indent=1), encoding="utf-8")
print("✔ ficha_metodo_nivelvida.json")

# ── validación: el índice tiene que ordenar como ordena la realidad ─────────
print("\n── validación del índice contra variables que NO entraron en él ──")
v = b[b.quintil.notna()]
for col, et in [("sin_seguro", "% sin seguro de salud"),
                ("anios_estudio", "años de estudio (19+)"),
                ("analfabeto", "% analfabeto 15+"),
                ("superior", "% con superior")]:
    s = v.groupby("quintil")[col].mean()
    s = s * 100 if col != "anios_estudio" else s
    print(f"  {et:28} " + " ".join(f"Q{int(q)}:{x:6.1f}" for q, x in s.items()))
