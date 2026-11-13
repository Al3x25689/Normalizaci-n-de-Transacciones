"""Conversiones estrictas sin dependencias externas."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def validar_id(valor):
    if isinstance(valor, bool) or not isinstance(valor, (str, int, float, Decimal)):
        raise ValueError('ID no textual ni numérico')
    if not str(valor).strip():
        raise ValueError('ID vacío')
    if not isinstance(valor, str) and not Decimal(str(valor)).is_finite():
        raise ValueError('ID numérico no finito')
    return str(valor).strip()


def validar_monto_moneda(valor, codigo, reglas):
    if isinstance(valor, bool) or not isinstance(valor, (str, int, float, Decimal)):
        raise ValueError('Monto no numérico')
    texto = str(valor).strip()
    simbolos = {s: c for c, lista in reglas['monedas'].items() for s in lista}
    candidatos = sorted([*simbolos, *reglas['simbolos_ambiguos']], key=len, reverse=True)
    simbolo = None
    for candidato in candidatos:
        if texto.startswith(candidato):
            simbolo = candidato
            texto = texto[len(candidato):].strip()
            break
        if texto.endswith(candidato):
            simbolo = candidato
            texto = texto[:-len(candidato)].strip()
            break
    if not re.fullmatch(r'[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)', texto):
        raise ValueError('Monto no numérico o no finito')
    try:
        monto = Decimal(texto.replace(',', '.'))
    except InvalidOperation as exc:
        raise ValueError('Monto no numérico') from exc
    if not monto.is_finite() or monto < 0:
        raise ValueError('Monto negativo o no finito')
    if codigo is not None:
        if not isinstance(codigo, str) or codigo.strip().upper() not in reglas['monedas']:
            raise ValueError('Código de moneda desconocido')
        moneda = codigo.strip().upper()
        if simbolo in reglas['simbolos_ambiguos'] and moneda not in reglas['simbolos_ambiguos'][simbolo]:
            raise ValueError('Símbolo ambiguo incompatible con el código de moneda')
        if simbolo in simbolos and simbolos[simbolo] != moneda:
            raise ValueError('Contradicción entre símbolo y código de moneda')
    else:
        if simbolo not in simbolos:
            raise ValueError('Moneda ausente, desconocida o ambigua')
        moneda = simbolos[simbolo]
    return monto, moneda


def validar_fecha(valor, reglas):
    if not isinstance(valor, str):
        raise ValueError('Fecha no textual')
    for formato in reglas['formatos_fecha']:
        try:
            return datetime.strptime(valor, formato).isoformat()
        except ValueError:
            pass
    if reglas['fecha_iso8601'] and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?', valor
    ):
        try:
            return datetime.fromisoformat(valor).isoformat()
        except ValueError:
            pass
    raise ValueError('Fecha inválida o formato no admitido')


def validar_estado(valor, reglas):
    if not isinstance(valor, str) or valor.strip().lower() not in reglas['estados']:
        raise ValueError('Estado desconocido')
    return reglas['estados'][valor.strip().lower()]
