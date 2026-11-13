"""Procesamiento multifuente y ejecución desde línea de comandos."""
import argparse
import json
from decimal import Decimal
from pathlib import Path

from metricas import calcular_metricas
from validador import validar_estado, validar_fecha, validar_id, validar_monto_moneda

REGLAS = Path(__file__).parent / 'configuracion' / 'reglas.json'


def cargar_reglas(ruta=REGLAS):
    with Path(ruta).open(encoding='utf-8') as archivo:
        return json.load(archivo)


def detectar_fuente(registro, reglas):
    """Identifica por campos exclusivos derivados del mapeo configurado."""
    if not isinstance(registro, dict):
        return 'UNKNOWN', 'Fuente no identificable'
    campos = {nombre: set(mapeo.values()) for nombre, mapeo in reglas['fuentes'].items()}
    coincidencias = []
    for nombre, propios in campos.items():
        ajenos = set().union(*(otros for fuente, otros in campos.items() if fuente != nombre))
        if (propios - ajenos) & registro.keys():
            coincidencias.append(nombre)
    if len(coincidencias) == 1:
        return coincidencias[0], None
    return 'UNKNOWN', 'Fuente ambigua' if coincidencias else 'Fuente no identificable'


def procesar(registros, reglas=None):
    if not isinstance(registros, list):
        raise ValueError('La raíz del JSON debe ser una lista de registros')
    if reglas is None:
        reglas = cargar_reglas()
    validos, invalidos, fuentes, ids = [], [], [], set()
    for original in registros:
        fuente, error_fuente = detectar_fuente(original, reglas)
        fuentes.append(fuente)
        motivos, normalizado = [], {'source': fuente}
        if fuente == 'UNKNOWN':
            motivos.append(error_fuente)
        else:
            campos = reglas['fuentes'][fuente]
            faltantes = [campo for campo in campos.values() if campo not in original]
            motivos.extend(f'Campo obligatorio faltante: {campo}' for campo in faltantes)
            for campo, funcion in (('id', validar_id),
                                   ('timestamp', lambda v: validar_fecha(v, reglas)),
                                   ('status', lambda v: validar_estado(v, reglas))):
                if campos[campo] not in original:
                    continue
                try:
                    normalizado[campo] = funcion(original[campos[campo]])
                except ValueError as exc:
                    motivos.append(str(exc))
            try:
                if campos['amount'] not in original:
                    raise ValueError('No se puede validar el monto ausente')
                normalizado['amount'], normalizado['currency'] = validar_monto_moneda(
                    original[campos['amount']], original.get(campos.get('currency')), reglas)
            except ValueError as exc:
                motivos.append(str(exc))
            if normalizado.get('id') in ids:
                motivos.append('ID duplicado')
        if motivos:
            invalidos.append({'original': original, 'motivos': motivos, 'source': fuente})
        else:
            ids.add(normalizado['id'])
            validos.append(normalizado)
    return {'validos': validos, 'invalidos': invalidos,
            'metricas': calcular_metricas(validos, invalidos, fuentes)}


def procesar_archivo(ruta, ruta_reglas=REGLAS):
    with Path(ruta).open(encoding='utf-8') as archivo:
        registros = json.load(archivo, parse_float=Decimal)
    return procesar(registros, cargar_reglas(ruta_reglas))


def serializar(valor):
    if isinstance(valor, Decimal):
        return format(valor, '.2f') if valor.as_tuple().exponent >= -2 else format(valor, 'f')
    raise TypeError(f'Tipo no serializable: {type(valor).__name__}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('--reglas', type=Path, default=REGLAS)
    parser.add_argument('--salida', type=Path)
    args = parser.parse_args()
    try:
        resultado = procesar_archivo(args.entrada, args.reglas)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Error: {exc}\n')
    texto = json.dumps(resultado, ensure_ascii=False, indent=2, default=serializar)
    if args.salida:
        args.salida.write_text(texto + '\n', encoding='utf-8')
    else:
        print(texto)


if __name__ == '__main__':
    main()
