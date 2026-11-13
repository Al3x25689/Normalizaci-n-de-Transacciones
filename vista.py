"""Filtros y exportación compartidos por las interfaces, sin reglas de negocio."""
import csv
import io
import json
from decimal import Decimal
from pathlib import Path

from normalizador import cargar_reglas, procesar, serializar

CAMPOS = ('id', 'amount', 'currency', 'timestamp', 'status', 'source')


def filtrar_transacciones(registros, estado='', moneda='', fuente='', busqueda=''):
    consulta = busqueda.strip().casefold()
    return [r for r in registros
            if (not estado or r['status'] == estado)
            and (not moneda or r['currency'] == moneda)
            and (not fuente or r['source'] == fuente)
            and consulta in r['id'].casefold()]


def filas_presentacion(registros):
    return [{c: serializar(r[c]) if c == 'amount' else r[c] for c in CAMPOS} for r in registros]


def generar_csv(registros):
    salida = io.StringIO(newline='')
    escritor = csv.DictWriter(salida, fieldnames=CAMPOS)
    escritor.writeheader()
    escritor.writerows(filas_presentacion(registros))
    return salida.getvalue().encode('utf-8-sig')


def exportar_csv(ruta, registros):
    Path(ruta).write_bytes(generar_csv(registros))
    return len(registros)


def procesar_contenido(contenido):
    """Adapta la carga web a la misma API del núcleo, conservando Decimal."""
    registros = json.loads(contenido.decode('utf-8'), parse_float=Decimal)
    return procesar(registros, cargar_reglas())
