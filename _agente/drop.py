#!/usr/bin/env python3
"""Herramienta del Agente Web de mwichys.

Edita SOLO el bloque `const DROP = {...}` de index.html, valida los valores
y deja el resto de la página intacto. No publica: eso lo hace el agente con git.

Uso (desde la raíz del repo):
  python3 _agente/drop.py estado
  python3 _agente/drop.py vendidos 7            # total confirmado (lo que dice la hoja)
  python3 _agente/drop.py venta [2]             # suma ventas (1 por defecto)
  python3 _agente/drop.py agotado               # muestra la versión "agotado" (pedir OK a la dueña antes)
  python3 _agente/drop.py reabrir               # quita la versión "agotado"
  python3 _agente/drop.py fechas --abre "1 de diciembre" --entrega "15 de diciembre"
  python3 _agente/drop.py nuevo-drop --numero 2 --abre "..." --entrega "..." [--cupos 25]
"""
import argparse
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INDEX = RAIZ / "index.html"
BLOQUE = re.compile(r"const DROP = \{\n(?P<cuerpo>.*?)\n\};", re.S)
CAMPO = re.compile(r'^(?P<ind>\s*)(?P<k>\w+):\s*(?P<v>"(?:[^"\\]|\\.)*"|-?\d+|true|false)(?P<coma>,?)(?P<resto>\s*//.*)?$')
ORDEN = ["numero", "abre", "entrega", "cupos", "vendidos", "agotado"]


def leer():
    html = INDEX.read_text(encoding="utf-8")
    m = BLOQUE.search(html)
    if not m:
        sys.exit("ERROR: no encuentro el bloque `const DROP = {...}` en index.html")
    lineas, datos = m.group("cuerpo").split("\n"), {}
    for ln in lineas:
        c = CAMPO.match(ln)
        if c:
            datos[c["k"]] = json.loads(c["v"])
    falta = [k for k in ORDEN if k not in datos]
    if falta:
        sys.exit(f"ERROR: al bloque DROP le faltan campos: {falta}")
    return html, m, lineas, datos


def validar(d):
    if not (isinstance(d["numero"], int) and d["numero"] >= 1):
        sys.exit("ERROR: numero debe ser un entero >= 1")
    if not (isinstance(d["cupos"], int) and 1 <= d["cupos"] <= 10000):
        sys.exit("ERROR: cupos debe ser un entero entre 1 y 10000")
    if not (isinstance(d["vendidos"], int) and d["vendidos"] >= 0):
        sys.exit("ERROR: vendidos debe ser un entero >= 0")
    if d["vendidos"] > d["cupos"]:
        print(f"AVISO: vendidos ({d['vendidos']}) supera los cupos ({d['cupos']}); se deja en {d['cupos']}.")
        d["vendidos"] = d["cupos"]
    for k in ("abre", "entrega"):
        if not isinstance(d[k], str) or len(d[k]) > 40 or re.search(r'[<>"\\`$]', d[k]):
            sys.exit(f"ERROR: {k} debe ser texto corto sin < > \" \\ ` $")
    if not isinstance(d["agotado"], bool):
        sys.exit("ERROR: agotado debe ser true o false")


def escribir(html, m, lineas, d):
    validar(d)
    nuevas = []
    for ln in lineas:
        c = CAMPO.match(ln)
        if c and c["k"] in d:
            nuevas.append(f'{c["ind"]}{c["k"]}: {json.dumps(d[c["k"]], ensure_ascii=False)}{c["coma"]}{c["resto"] or ""}')
        else:
            nuevas.append(ln)
    nuevo = html[: m.start("cuerpo")] + "\n".join(nuevas) + html[m.end("cuerpo"):]
    INDEX.write_text(nuevo, encoding="utf-8")


def disponible(d):
    if d["agotado"]:
        return 0
    return round((d["cupos"] - d["vendidos"]) / d["cupos"] * 100)


def resumen(d):
    nn = f'{d["numero"]:02d}'
    est = "AGOTADO (versión agotado visible)" if d["agotado"] else (
        "LLENO: pedidos bloqueados, falta confirmar 'agotado' con la dueña" if d["vendidos"] >= d["cupos"] else "abierto")
    return (f"Drop {nn} · abre {d['abre']} · entrega {d['entrega']}\n"
            f"Vendidos {d['vendidos']}/{d['cupos']} · disponible {disponible(d)}% · estado: {est}")


def main():
    p = argparse.ArgumentParser(description="Agente Web mwichys: edita el bloque DROP de index.html")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("estado")
    v = sub.add_parser("vendidos"); v.add_argument("total", type=int)
    s = sub.add_parser("venta"); s.add_argument("cantidad", type=int, nargs="?", default=1)
    sub.add_parser("agotado")
    sub.add_parser("reabrir")
    f = sub.add_parser("fechas"); f.add_argument("--abre"); f.add_argument("--entrega")
    n = sub.add_parser("nuevo-drop")
    n.add_argument("--numero", type=int, required=True)
    n.add_argument("--abre", required=True); n.add_argument("--entrega", required=True)
    n.add_argument("--cupos", type=int)
    a = p.parse_args()

    html, m, lineas, d = leer()
    antes = dict(d)
    if a.cmd == "vendidos":
        d["vendidos"] = a.total
    elif a.cmd == "venta":
        if a.cantidad < 1:
            sys.exit("ERROR: la cantidad debe ser 1 o más")
        d["vendidos"] += a.cantidad
    elif a.cmd == "agotado":
        d["agotado"] = True
    elif a.cmd == "reabrir":
        d["agotado"] = False
    elif a.cmd == "fechas":
        if a.abre: d["abre"] = a.abre
        if a.entrega: d["entrega"] = a.entrega
    elif a.cmd == "nuevo-drop":
        d.update(numero=a.numero, abre=a.abre, entrega=a.entrega, vendidos=0, agotado=False)
        if a.cupos: d["cupos"] = a.cupos

    if a.cmd != "estado":
        escribir(html, m, lineas, d)
        if d == antes:
            print("Sin cambios.")
    print(resumen(d))
    if not d["agotado"] and d["vendidos"] >= d["cupos"]:
        print("ACCIÓN: el drop está lleno. Pide confirmación a la dueña antes de correr `agotado`.")


if __name__ == "__main__":
    main()
