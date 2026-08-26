# -*- coding: utf-8 -*-
"""PASO 4 — EL PAQUETE PARA LA WEB.

Los siete JSON del paso 3 pesan 12 MB: sirven para analizar, no para servir una
página. Acá se arma un paquete compacto con lo que el explorador necesita y
NADA más, sin recalcular nunca un número: todo se lee de `salida/`.

Qué entra:
  · las tres matrices 9×9 (residencia · nacimiento · trabajo)
  · las referencias: región, cada municipio, y el que ya estaba en cada municipio
  · las familias de origen y los orígenes de fuera con n suficiente
  · los corredores de conmutación
  · las cohortes (la curva de asimilación)
  · el exterior partido en retornados y extranjeros

★ Se recorta por RELEVANCIA, no por casualidad, y **se declara lo que quedó
  afuera**: cada bloque anota cuántas celdas y cuántas personas no entraron. Un
  recorte silencioso se lee como «esto es todo», y no lo es.
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

AQUI = pathlib.Path(__file__).resolve().parent
SAL = AQUI / "salida"
DESTINO = AQUI / "web"
DESTINO.mkdir(exist_ok=True)

MIN_ORIGEN_EXTERNO = 150     # orígenes de fuera de la región que se listan aparte
MIN_CORREDOR = 30            # corredores de conmutación que se muestran

cargar = lambda n: json.loads((SAL / f"{n}.json").read_text(encoding="utf-8"))
res, nac, con = cargar("mig_residencia"), cargar("mig_nacimiento"), cargar("conmutacion")
ext, coh = cargar("exterior"), cargar("cohortes")
ref, eti = cargar("referencias"), cargar("etiquetas")

N9 = eti["municipios"]
COD9 = list(N9)

# los indicadores que viajan a la web: todos los escalares, y sólo las
# distribuciones que la ficha realmente dibuja
DIST_WEB = {"edad_tramo", "nivel_educativo", "rama", "ocupacion",
            "categoria_ocupacional", "lugar_de_trabajo", "quintil", "tenencia",
            "saneamiento", "agua_fuente", "combustible", "tipo_hogar",
            "afiliacion_salud"}


def podar(celda):
    """Se queda con los escalares y con las distribuciones que la ficha usa."""
    out = {}
    for k, v in celda.items():
        if isinstance(v, dict):
            if k in DIST_WEB:
                # Sólo las categorías con peso; el resto se junta en «Otros».
                # `rama` tiene 22 secciones: con un tope de 8 el residuo llegaba
                # al 24% y «Otros» terminaba siendo la categoría más grande de
                # la ficha, que es justo lo que un lector no puede interpretar.
                tope = 14 if k in ("rama", "ocupacion") else 8
                top = {a: b for a, b in sorted(v.items(), key=lambda t: -t[1])[:tope]
                       if b >= 0.5}
                resto = round(sum(v.values()) - sum(top.values()), 1)
                if resto >= 0.5:
                    top["Otros"] = resto
                out[k] = top
        else:
            out[k] = v
    return out


def bloque(celdas, campos, filtro=None, etiqueta=None):
    """Poda + informe de lo que quedó afuera, que se publica al lado."""
    dentro, fuera_n, fuera_p = [], 0, 0
    for c in celdas:
        if filtro and not filtro(c):
            fuera_n += 1
            fuera_p += c["n"]
            continue
        d = {k: c[k] for k in campos}
        d.update(podar({k: v for k, v in c.items() if k not in campos}))
        if etiqueta:
            d.update(etiqueta(c))
        dentro.append(d)
    return {"celdas": dentro,
            "no_listadas": {"celdas": fuera_n, "personas": fuera_p}}


tiene_perfil = lambda c: "anios_estudio" in c
en9 = lambda k: k.startswith("mun:") and k[4:] in N9

# ═══════════════ 1 · las tres matrices 9×9 ═══════════════
def matriz(celdas, cor, cdes, transformar_destino=lambda x: x):
    M = {}
    for c in celdas:
        o, d = transformar_destino(c[cor]), c[cdes]
        if not (o in N9 or en9(o)) or not (d in N9 or en9(d)):
            continue
        o = o[4:] if o.startswith("mun:") else o
        d = d[4:] if d.startswith("mun:") else d
        if o == d:
            continue
        M.setdefault(o, {})[d] = {k: v for k, v in c.items()
                                  if not isinstance(v, dict)
                                  and k not in (cor, cdes)}
    return M


# migración: la celda es (destino, origen) → la matriz va origen → destino
mat_res = {}
for c in res["celdas"]:
    if not en9(c["origen"]):
        continue
    o, d = c["origen"][4:], c["destino"]
    if o == d:
        continue
    mat_res.setdefault(o, {})[d] = {k: v for k, v in c.items()
                                    if not isinstance(v, dict)
                                    and k not in ("origen", "destino")}
mat_nac = {}
for c in nac["celdas"]:
    if not en9(c["origen"]):
        continue
    o, d = c["origen"][4:], c["destino"]
    if o == d:
        continue
    mat_nac.setdefault(o, {})[d] = {k: v for k, v in c.items()
                                    if not isinstance(v, dict)
                                    and k not in ("origen", "destino")}
# conmutación: la celda es (residencia, trabajo) → ya va en el sentido correcto
mat_con = {}
for c in con["celdas"]:
    if not en9(c["trabajo"]):
        continue
    o, d = c["residencia"], c["trabajo"][4:]
    if o == d:
        continue
    mat_con.setdefault(o, {})[d] = {k: v for k, v in c.items()
                                    if not isinstance(v, dict)
                                    and k not in ("residencia", "trabajo")}
print(f"matrices · residencia {sum(len(v) for v in mat_res.values())} pares · "
      f"nacimiento {sum(len(v) for v in mat_nac.values())} · "
      f"conmutación {sum(len(v) for v in mat_con.values())}")

# ═══════════════ 2 · las fichas de par completas ═══════════════
fichas = {}
for dim, celdas, cor, cdes in [("res", res["celdas"], "origen", "destino"),
                               ("nac", nac["celdas"], "origen", "destino"),
                               ("con", con["celdas"], "residencia", "trabajo")]:
    for c in celdas:
        if not tiene_perfil(c):
            continue
        o = c[cor][4:] if c[cor].startswith("mun:") else c[cor]
        d = c[cdes][4:] if c[cdes].startswith("mun:") else c[cdes]
        if dim == "con":
            o, d = c[cor], (c[cdes][4:] if c[cdes].startswith("mun:") else c[cdes])
        if not (o in N9 and d in N9) or o == d:
            continue
        fichas[f"{dim}|{o}|{d}"] = podar(
            {k: v for k, v in c.items() if k not in (cor, cdes)})
print(f"fichas de par completas: {len(fichas)}")

# ═══════════════ 3 · orígenes de fuera de la región ═══════════════
externos_res = bloque(
    [c for c in res["region"] if not en9(c["origen"]) and c["origen"] != "aqui"],
    ["origen"], filtro=lambda c: c["n"] >= MIN_ORIGEN_EXTERNO and tiene_perfil(c),
    etiqueta=lambda c: {"nombre": eti["lugares"].get(c["origen"], c["origen"])})
print(f"orígenes externos listados: {len(externos_res['celdas'])} · "
      f"fuera {externos_res['no_listadas']['personas']:,} personas")

# ═══════════════ 4 · corredores de conmutación ═══════════════
corredores = bloque(
    con["celdas"], ["residencia", "trabajo"],
    filtro=lambda c: c["n"] >= MIN_CORREDOR and tiene_perfil(c),
    etiqueta=lambda c: {"nom_res": N9.get(c["residencia"], c["residencia"]),
                        "nom_tra": eti["lugares"].get(c["trabajo"], c["trabajo"])})
print(f"corredores listados: {len(corredores['celdas'])} · "
      f"fuera {corredores['no_listadas']['personas']:,} personas")

# ═══════════════ 5 · el paquete ═══════════════
paquete = {
    "meta": {
        "fuente": "Censo de Población y Vivienda 2024 (INE Bolivia), microdato",
        "universo": ref["region"]["n"],
        "municipios": N9,
        "generado_por": "analisis/flujos/01→04",
        "umbral_perfil": 40,
        "advertencia_vivienda":
            "Los indicadores de vivienda se leen como PERSONAS: «38% con "
            "alcantarillado» significa que el 38% de esas personas vive en un "
            "hogar que lo tiene, no que el 38% de las viviendas lo tenga.",
        "advertencia_no_respuesta":
            "Quienes no declararon origen (43.574 en residencia 2019) tienen 17,5% "
            "con educación superior contra 35,7% de la región: la no respuesta no "
            "es aleatoria y sesga hacia abajo cualquier total que los incluya.",
    },
    "indicadores": eti["indicadores"],
    "familias_de_indicadores": eti["familias_de_indicadores"],
    "huella": eti["huella"],
    "familias_de_origen": eti["familias"],
    "referencias": ref,
    "matrices": {"res": mat_res, "nac": mat_nac, "con": mat_con},
    "fichas": fichas,
    "familias_por_municipio": {
        "res": [{k: c[k] for k in ("destino", "familia", "n")} | podar(
            {k: v for k, v in c.items() if k not in ("destino", "familia")})
            for c in res["familias"]],
        "nac": [{k: c[k] for k in ("destino", "familia", "n")} | podar(
            {k: v for k, v in c.items() if k not in ("destino", "familia")})
            for c in nac["familias"]],
    },
    "externos": externos_res,
    "corredores": corredores,
    "estados_de_trabajo": [dict(c) for c in con["estados"]],
    "exterior": {"subgrupo": ext["subgrupo"],
                 "por_municipio": ext["por_municipio"],
                 "por_pais": [c | {"nombre": eti["lugares"].get(c["pais"], c["pais"])}
                              for c in ext["por_pais"] if c["n"] >= 60]},
    "cohortes": {"celdas": coh["celdas"], "region": coh["region"]},
    "etiquetas_lugar": eti["lugares"],
}

p = DESTINO / "flujos_metro.json"
p.write_text(json.dumps(paquete, ensure_ascii=False, separators=(",", ":")),
             encoding="utf-8")
print(f"\n✔ {p}  ·  {p.stat().st_size/1024:.0f} KB")
