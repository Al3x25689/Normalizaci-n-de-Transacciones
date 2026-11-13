"""Métricas con suma decimal exacta, independiente de la precisión global."""
from collections import Counter
from decimal import Decimal, localcontext


def calcular_metricas(validos, invalidos, fuentes):
    totales = {}
    for registro in validos:
        moneda, monto = registro['currency'], registro['amount']
        anterior = totales.get(moneda, Decimal(0))
        escala = min(anterior.as_tuple().exponent, monto.as_tuple().exponent)
        precision = max(anterior.adjusted(), monto.adjusted(), 0) - escala + 3
        with localcontext() as contexto:
            contexto.prec = max(28, precision)
            totales[moneda] = anterior + monto
    total = len(validos) + len(invalidos)
    return {
        'total_procesado': total,
        'porcentaje_validos': len(validos) / total * 100 if total else 0.0,
        'porcentaje_invalidos': len(invalidos) / total * 100 if total else 0.0,
        'validos': len(validos), 'invalidos': len(invalidos),
        'por_estado': {s: sum(r['status'] == s for r in validos) for s in ('SUCCESS', 'FAILED', 'PENDING')},
        'por_fuente': dict(Counter(fuentes)), 'montos_por_moneda': totales,
    }
