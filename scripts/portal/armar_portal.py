# -*- coding: utf-8 -*-
"""
EL PORTAL — la puerta de entrada a Santa Cruz Metrópoli En Cifras.
==================================================================

Arma `docs/index.html`: la portada que explica las cuatro herramientas y manda
a cada una. Las cifras que muestra NO se escriben a mano — salen de los mismos
catálogos y datos que alimentan los tableros, así que el día que se agregue un
indicador la portada dice el número nuevo sin que nadie se acuerde de tocarla.

⚠️ LA PLANTILLA DE LOS TABLEROS YA NO VIVE EN `docs/index.html`. Estaba ahí, así
   que la raíz del sitio publicaba un tablero que en realidad era el insumo del
   que se derivan los dos. Se mudó a `plantilla/tablero.html` y `generar_sitios.py`
   apunta ahí; los dos tableros derivados salieron byte por byte iguales.

★ EL HERO ES EL TERRITORIO DE VERDAD. En vez de una animación decorativa, el
  fondo dibuja las 38.892 manzanas censadas y las hace aparecer y desaparecer
  contra la silueta de los nueve municipios: en cinco segundos el visitante ve
  las dos escalas que el sitio cubre, que es exactamente lo que hay que
  explicarle. El enjambre va en un archivo aparte —303 KB, 92 comprimido— para
  que la página pinte primero y el territorio llegue después.

    python scripts/portal/armar_portal.py
"""
import json, math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "banco"))

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
DATOS = RAIZ / "docs" / "datos"
PLANTILLA = pathlib.Path(__file__).resolve().parent / "plantilla_portal.html"

REJILLA = 2047          # el enjambre se cuantiza a enteros: la mitad de peso


def anillos(g):
    if not g:
        return []
    t = g.get("type")
    if t == "Polygon":
        return [g["coordinates"][0]] if g["coordinates"] else []
    if t == "MultiPolygon":
        return [p[0] for p in g["coordinates"] if p]
    if t == "GeometryCollection":
        out = []
        for x in g.get("geometries", []):
            out += anillos(x)
        return out
    return []


def simplificar(anillo, tol):
    """Douglas-Peucker sencillo. La silueta del hero se dibuja a 900 px de
    ancho: guardar los 4.000 vértices originales de un municipio es mandar
    precisión que la pantalla no puede mostrar."""
    if len(anillo) < 3:
        return anillo
    def dist(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2-x1, y2-y1
        if dx == dy == 0:
            return math.hypot(x-x1, y-y1)
        t = max(0, min(1, ((x-x1)*dx + (y-y1)*dy) / (dx*dx + dy*dy)))
        return math.hypot(x - (x1+t*dx), y - (y1+t*dy))
    def dp(pts):
        if len(pts) < 3:
            return pts
        i, d = max(((k, dist(p, pts[0], pts[-1])) for k, p in enumerate(pts[1:-1], 1)),
                   key=lambda kv: kv[1])
        if d <= tol:
            return [pts[0], pts[-1]]
        return dp(pts[:i+1])[:-1] + dp(pts[i:])
    sys.setrecursionlimit(10000)
    return dp(anillo)


def main():
    geo9 = json.loads((DATOS / "municipios.geojson").read_text(encoding="utf-8"))
    cat_m = json.loads((DATOS / "catalogo_municipal.json").read_text(encoding="utf-8"))
    cat_z = json.loads((DATOS / "catalogo_manzana.json").read_text(encoding="utf-8"))
    muni = json.loads((DATOS / "municipios_manzana.json").read_text(encoding="utf-8"))

    # ── el enjambre: una manzana, un punto ───────────────────────────────
    pts = []
    for f in sorted(DATOS.glob("geo_*.geojson")):
        g = json.loads(f.read_text(encoding="utf-8"))
        for ft in g["features"]:
            an = anillos(ft.get("geometry"))
            if not an:
                continue
            a = max(an, key=len)
            pts.append((sum(p[0] for p in a)/len(a), sum(p[1] for p in a)/len(a)))

    # el encuadre lo fijan LOS MUNICIPIOS, no las manzanas: si lo fijara el
    # enjambre, la silueta de Pailón se saldría del cuadro al aparecer
    todos = [p for f in geo9["features"] for a in anillos(f["geometry"]) for p in a]
    X0 = min(p[0] for p in todos); X1 = max(p[0] for p in todos)
    Y0 = min(p[1] for p in todos); Y1 = max(p[1] for p in todos)
    esc = REJILLA / (X1 - X0)
    q = lambda x, y: (round((x - X0) * esc), round((Y1 - y) * esc))   # y hacia abajo

    plano = []
    for x, y in pts:
        a, b = q(x, y)
        plano += [a, b]
    (DATOS / "portal_enjambre.json").write_text(
        json.dumps({"alto": round((Y1 - Y0) * esc), "ancho": REJILLA, "p": plano},
                   separators=(",", ":")), encoding="utf-8")

    # ── las siluetas, simplificadas ──────────────────────────────────────
    tol = (X1 - X0) * .0009
    siluetas = []
    for f in geo9["features"]:
        for a in anillos(f["geometry"]):
            if len(a) < 12:
                continue
            s = simplificar(a, tol)
            siluetas.append([c for x, y in s for c in q(x, y)])

    n_mun_ind = sum(len(g["indicadores"]) for g in cat_m["grupos"])
    n_mz_ind = sum(len(g["indicadores"]) for g in cat_z["grupos"])
    n_laminas = len(list((RAIZ / "docs" / "banco" / "municipal").glob("*.png"))) + \
                len(list((RAIZ / "docs" / "banco" / "manzana").glob("*.png")))

    datos = {
        "siluetas": siluetas,
        "ancho": REJILLA,
        "alto": round((Y1 - Y0) * esc),
        "n": {
            "manzanas": sum(m["manzanas"] for m in muni),
            "conficha": sum(m["con_ficha"] for m in muni),
            "poblacion": sum(m["municipal"].get("pob_total", 0) for m in muni),
            "mun_ind": n_mun_ind,
            "mun_bloques": len(cat_m["grupos"]),
            "mz_ind": n_mz_ind,
            "mz_bloques": len(cat_z["grupos"]),
            "laminas": n_laminas,
        },
    }
    html = PLANTILLA.read_text(encoding="utf-8").replace(
        "/*__DATOS__*/", json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    (RAIZ / "docs" / "index.html").write_text(html, encoding="utf-8")

    kb = (DATOS / "portal_enjambre.json").stat().st_size / 1024
    print(f"enjambre: {len(pts):,} manzanas · {kb:.0f} KB".replace(",", "."))
    print(f"siluetas: {len(siluetas)} anillos simplificados")
    print(f"cifras  : {n_mun_ind} municipales · {n_mz_ind} por manzana · {n_laminas} láminas")
    print("->", RAIZ / "docs" / "index.html")


if __name__ == "__main__":
    main()
