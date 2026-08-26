# -*- coding: utf-8 -*-
"""
REGENERA EL BANCO ENTERO — un solo comando.
===========================================

Encadena los cuatro pasos en el orden en que dependen unos de otros y se planta
en el primero que falle. Existe porque el orden no es evidente y equivocarlo no
da un error: da un banco que se ve bien y miente.

  1. `scripts/paleta.py --verificar`  →  que el tablero y el banco pinten igual.
     Va PRIMERO. Si la rampa se desvió, las 375 láminas salen con el color
     equivocado y no hay nada en el PNG que lo delate.
  2. `motor/lamina_municipal.py --todas`  →  213 PNG, uno por indicador.
  3. `motor/lamina_manzana.py --todas`    →  162 PNG, uno por municipio×indicador.
  4. `motor/armar_sitio.py`               →  el índice + las miniaturas.
     Va ÚLTIMO porque recorre lo que hay en el disco: si corre antes, arma el
     índice de las láminas viejas.

    python sistema-graficos/generar_todo.py
    python sistema-graficos/generar_todo.py --solo municipal
    python sistema-graficos/generar_todo.py --saltear-paleta

⚠️ La corrida completa son 375 láminas y ~233 MB. Para probar un cambio de
   diseño NO se usa esto: se genera una sola lámina con `--indicador`.
"""
import argparse
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
MOTOR = AQUI / "motor"
BANCO = RAIZ / "docs" / "banco"


def paso(titulo, args, obligatorio=True):
    """Corre un paso y devuelve si salió bien. Muestra su salida tal cual."""
    print(f"\n{'─' * 70}\n▶ {titulo}\n{'─' * 70}")
    t0 = time.time()
    r = subprocess.run([sys.executable, *[str(a) for a in args]], cwd=RAIZ)
    seg = time.time() - t0
    if r.returncode == 0:
        print(f"  ✔ {titulo} · {seg:.0f}s")
        return True
    print(f"  ✘ {titulo} · terminó con código {r.returncode}")
    if obligatorio:
        print("\n⛔ Se corta acá. Los pasos siguientes dependen de éste.")
        sys.exit(r.returncode)
    return False


def contar():
    m = len(list((BANCO / "municipal").glob("*.png"))) if (BANCO / "municipal").exists() else 0
    z = len(list((BANCO / "manzana").glob("*.png"))) if (BANCO / "manzana").exists() else 0
    return m, z


def main():
    ap = argparse.ArgumentParser(description="Regenera el banco de láminas.")
    ap.add_argument("--solo", choices=["municipal", "manzana", "sitio"],
                    help="corre un solo generador (igual verifica la paleta)")
    ap.add_argument("--saltear-paleta", action="store_true",
                    help="⚠️ sólo si ya se verificó en esta sesión")
    a = ap.parse_args()

    antes = contar()
    print(f"banco actual: {antes[0]} láminas municipales · {antes[1]} por manzana")

    if not a.saltear_paleta:
        # No es obligatorio: `--verificar` devuelve ≠0 cuando encuentra una
        # desviación, y lo que hace falta es que se VEA, no que se corte. Quien
        # esté cambiando la identidad a propósito necesita seguir.
        ok = paso("1/4 · paleta: ¿tablero y banco pintan igual?",
                  [RAIZ / "scripts" / "paleta.py", "--verificar"], obligatorio=False)
        if not ok:
            print("  ⚠️ LA RAMPA SE DESVIÓ. Las láminas van a salir con un color que\n"
                  "     el tablero no usa, y el PNG no lo va a delatar. Corregir con\n"
                  "     `python scripts/paleta.py` antes de seguir, o seguir a sabiendas.")

    if a.solo in (None, "municipal"):
        paso("2/4 · láminas municipales (una por indicador)",
             [MOTOR / "lamina_municipal.py", "--todas"])
    if a.solo in (None, "manzana"):
        paso("3/4 · láminas por manzana (una por municipio × indicador)",
             [MOTOR / "lamina_manzana.py", "--todas"])
    if a.solo in (None, "sitio", "municipal", "manzana"):
        # Siempre, incluso con `--solo municipal`: el índice recorre el disco, y
        # dejarlo sin correr deja la página describiendo el banco anterior.
        paso("4/4 · índice navegable + miniaturas",
             [MOTOR / "armar_sitio.py"])

    despues = contar()
    print(f"\n{'═' * 70}")
    print(f"banco: {despues[0]} municipales + {despues[1]} por manzana = "
          f"{sum(despues)} láminas")
    if despues != antes:
        print(f"  (antes: {antes[0]} + {antes[1]} = {sum(antes)})")
    print("  índice → docs/banco/index.html")


if __name__ == "__main__":
    main()
