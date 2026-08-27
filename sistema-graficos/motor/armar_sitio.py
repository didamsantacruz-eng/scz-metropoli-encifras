# -*- coding: utf-8 -*-
"""
EL SITIO DEL BANCO — índice navegable de las 375 láminas.
=========================================================

Genera `docs/banco/index.html` a partir de lo que HAY EN EL DISCO: recorre los
PNG, cruza cada archivo con el catálogo para sacarle título, bloque temático y
municipio, y arma el índice. Si mañana se agrega un indicador y se regenera el
banco, este script vuelve a correr y la página se entera sola.

⚠️ LAS MINIATURAS NO SON UN LUJO, SON EL REQUISITO. Las láminas pesan entre 400
   KB y 1 MB cada una: una grilla de 375 con los PNG completos serían ~230 MB
   por visita. Se genera una miniatura de 400 px por lámina —unos 15 KB— y el
   PNG entero sólo viaja cuando alguien lo abre o lo descarga.

⚠️ EL NOMBRE DEL RECORTE SE DICE ENTERO. Son nueve municipios: seis de la Región
   Metropolitana y tres de su área de influencia. La página no dice «la región» a
   secas en ningún lado, porque dejaría fuera del nombre a un tercio de lo que
   está mostrando.

    python sistema-graficos/motor/armar_sitio.py
"""
import json, pathlib, re, sys, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
DATOS = RAIZ / "docs" / "datos"
BANCO = RAIZ / "docs" / "banco"
MINIS = BANCO / "mini"
PLANTILLA = pathlib.Path(__file__).resolve().parent / "plantilla_sitio.html"

# Los indicadores que se turnan en el hero. Elegidos para que el mapa CAMBIE de
# verdad entre uno y otro —si todos pintaran parecido, la animación no diría
# nada— y para que se vea la variedad de bloques que tiene el banco.
HERO = ["pct_edu_superior", "pob_total", "pct_sin_seguro", "pct_agua_caneria",
        "pct_alcantarillado", "densidad", "pct_gas_red", "pct_basura_formal"]

ANCHO_MINI = 400


def slug(nombre):
    s = unicodedata.normalize("NFD", nombre.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "_")


def miniaturas(pngs, destino):
    """Una miniatura por lámina, sólo si falta o si la lámina es más nueva."""
    from PIL import Image
    destino.mkdir(parents=True, exist_ok=True)
    hechas, saltadas = 0, 0
    for p in pngs:
        m = destino / (p.stem + ".webp")
        if m.exists() and m.stat().st_mtime >= p.stat().st_mtime:
            saltadas += 1
            continue
        im = Image.open(p).convert("RGB")
        im = im.resize((ANCHO_MINI, round(ANCHO_MINI * im.height / im.width)),
                       Image.LANCZOS)
        im.save(m, "WEBP", quality=74, method=5)
        hechas += 1
    return hechas, saltadas


def main():
    cat_mun = json.loads((DATOS / "catalogo_municipal.json").read_text(encoding="utf-8"))
    cat_mz = json.loads((DATOS / "catalogo_manzana.json").read_text(encoding="utf-8"))
    munis = json.loads((DATOS / "municipios_municipal.json").read_text(encoding="utf-8"))
    mini_geo = json.loads((DATOS / "mini.json").read_text(encoding="utf-8"))

    ind_mun, gru_mun = {}, {}
    for g in cat_mun["grupos"]:
        for i in g["indicadores"]:
            ind_mun[i["key"]] = i
            gru_mun[i["key"]] = g["label"]
    ind_mz, gru_mz = {}, {}
    for g in cat_mz["grupos"]:
        for i in g["indicadores"]:
            ind_mz[i["key"]] = i
            gru_mz[i["key"]] = g["label"]

    por_slug = {slug(m["nombre"]): m["nombre"] for m in munis}
    # ★ EL ÍNDICE GUARDA LA CLAVE Y EL CÓDIGO, no sólo las etiquetas. Con el
    #   título y el nombre del municipio alcanzaba para BUSCAR, pero no para
    #   ENLAZAR: el tablero se dirige por `#i=<clave>&m=<código INE>`, y ni la
    #   clave ni el código se pueden deducir de un rótulo en castellano.
    #   ⚠️ En el enlace va el código INE («070104»), no el `sigep` interno:
    #   es el mismo criterio que usa el tablero al escribir su propia URL.
    cod_slug = {slug(m["nombre"]): m["cod_ine"] for m in munis}
    laminas = []

    # ── municipales: un archivo por indicador ────────────────────────────
    pngs = sorted((BANCO / "municipal").glob("*.png"))
    h, s = miniaturas(pngs, MINIS / "municipal")
    print(f"  miniaturas municipales: {h} nuevas, {s} ya estaban")
    for p in pngs:
        i = ind_mun.get(p.stem)
        if not i:
            print("  ⚠️ sin catálogo:", p.name)
            continue
        laminas.append({"n": "municipal", "t": i["label"], "g": gru_mun[p.stem],
                        "m": "", "k": p.stem, "f": "municipal/" + p.name,
                        "mi": "mini/municipal/" + p.stem + ".webp",
                        "kb": round(p.stat().st_size / 1024)})

    # ── manzana: municipio + indicador, separados por doble guion bajo ───
    pngs = sorted((BANCO / "manzana").glob("*.png"))
    h, s = miniaturas(pngs, MINIS / "manzana")
    print(f"  miniaturas de manzana: {h} nuevas, {s} ya estaban")
    for p in pngs:
        if "__" not in p.stem:
            print("  ⚠️ nombre inesperado:", p.name)
            continue
        sl, clave = p.stem.split("__", 1)
        i = ind_mz.get(clave)
        if not i:
            print("  ⚠️ sin catálogo:", p.name)
            continue
        laminas.append({"n": "manzana", "t": i["label"], "g": gru_mz[clave],
                        "m": por_slug.get(sl, sl), "k": clave,
                        "ci": cod_slug.get(sl, ""), "f": "manzana/" + p.name,
                        "mi": "mini/manzana/" + p.stem + ".webp",
                        "kb": round(p.stat().st_size / 1024)})

    # ── el hero: valores reales para que el mapa se repinte ──────────────
    hero = []
    for k in HERO:
        i = ind_mun.get(k)
        if not i:
            continue
        v = {m["sigep"]: m["municipal"].get(k) for m in munis}
        if sum(1 for x in v.values() if x is not None) < 9:
            continue
        et = i["label"]
        hero.append({"label": et, "unit": i["unit"], "dir": i.get("dir", 0), "v": v})

    # ★ EL viewBox SE AJUSTA AL CONTORNO REAL. `mini.json` viene con un lienzo
    #   cuadrado (0 0 100 100) y la región es apaisada —dos de ancho por uno de
    #   alto—, así que la mitad del alto del hero era aire y el pie del mapa
    #   quedaba flotando lejos de la figura.
    nums = [float(t) for d in mini_geo["paths"].values()
            for t in re.findall(r"-?\d+(?:\.\d+)?", d)]
    xs, ys = nums[0::2], nums[1::2]
    m = (max(xs) - min(xs)) * .02
    caja = "%.2f %.2f %.2f %.2f" % (min(xs)-m, min(ys)-m,
                                    max(xs)-min(xs)+2*m, max(ys)-min(ys)+2*m)

    datos = {"laminas": laminas, "hero": hero, "siluetas": mini_geo["paths"],
             "caja": caja}
    # la paleta se inyecta desde el contrato único: ver `scripts/paleta.py`
    paleta = json.loads((RAIZ / "assets" / "paleta.json").read_text(encoding="utf-8"))["pinta"]
    html = (PLANTILLA.read_text(encoding="utf-8")
            .replace("/*__DATOS__*/", json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
            .replace("/*__PALETA__*/", json.dumps(paleta, ensure_ascii=False, separators=(",", ":"))))
    (BANCO / "index.html").write_text(html, encoding="utf-8")

    peso = sum(f.stat().st_size for f in MINIS.rglob("*.webp")) / 1e6
    print(f"\n{len(laminas)} láminas indexadas "
          f"({sum(1 for l in laminas if l['n']=='municipal')} municipales + "
          f"{sum(1 for l in laminas if l['n']=='manzana')} manzana)")
    print(f"miniaturas: {peso:.1f} MB · hero con {len(hero)} indicadores")
    print("->", BANCO / "index.html")


if __name__ == "__main__":
    main()
