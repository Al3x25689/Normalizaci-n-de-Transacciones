import copy
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from normalizador import cargar_reglas, procesar, procesar_archivo, serializar

RAIZ = Path(__file__).resolve().parents[1]


def registro(**cambios):
    base = dict(id='uno', amount='100.50', currency='USD',
                timestamp='2025-03-10 14:22:00', status='completed')
    base.update(cambios)
    return base


class SistemaTests(unittest.TestCase):
    def valido(self, **cambios):
        resultado = procesar([registro(**cambios)])
        self.assertEqual(resultado['invalidos'], [])
        return resultado['validos'][0]

    def invalido(self, **cambios):
        resultado = procesar([registro(**cambios)])
        self.assertEqual(len(resultado['invalidos']), 1)
        return resultado['invalidos'][0]

    def test_originales_y_metricas(self):
        r = procesar_archivo(RAIZ / 'datos/validos.json')
        self.assertEqual([v['id'] for v in r['validos']], ['tx_001', '204', 'A-77'])
        self.assertEqual(r['metricas'], {
            'total_procesado': 3, 'validos': 3, 'invalidos': 0,
            'porcentaje_validos': 100.0, 'porcentaje_invalidos': 0.0,
            'por_estado': {'SUCCESS': 3, 'FAILED': 0, 'PENDING': 0},
            'por_fuente': {'SOURCE_1': 1, 'SOURCE_2': 1, 'SOURCE_3': 1},
            'montos_por_moneda': {'USD': Decimal('10150.50'), 'EUR': Decimal('99.99')}})

    def test_id_numerico_y_vacio(self):
        for valor, esperado in [(0, '0'), (204, '204'), (12.5, '12.5')]:
            with self.subTest(valor=valor):
                self.assertEqual(self.valido(id=valor)['id'], esperado)
        for valor in ['', '  ', None, True, [], float('nan')]:
            with self.subTest(valor=valor):
                self.invalido(id=valor)

    def test_montos(self):
        for valor, esperado in [(10050, '10050'), (0, '0'), ('€99,99', '99.99'),
                                ('1.2345', '1.2345'), (12.25, '12.25')]:
            with self.subTest(valor=valor):
                moneda = 'EUR' if valor == '€99,99' else 'USD'
                self.assertEqual(self.valido(amount=valor, currency=moneda)['amount'], Decimal(esperado))
        for valor in [-1, '-0.01', 'NaN', 'Infinity', float('inf'), True, None, 'abc', '1,2.3']:
            with self.subTest(valor=valor):
                self.invalido(amount=valor)

    def test_codigos_y_simbolos_configurados(self):
        reglas = cargar_reglas()
        self.assertEqual(set(reglas['monedas']), {'USD', 'EUR', 'GBP', 'JPY', 'MXN', 'CAD', 'BRL', 'CHF', 'CNY', 'KRW'})
        for moneda, simbolos in reglas['monedas'].items():
            with self.subTest(moneda=moneda):
                self.assertEqual(self.valido(currency=moneda.lower())['currency'], moneda)
            for simbolo in simbolos:
                with self.subTest(simbolo=simbolo):
                    self.assertEqual(self.valido(amount=simbolo + '10', currency=None)['currency'], moneda)
                    self.assertEqual(self.valido(amount='10' + simbolo, currency=moneda)['currency'], moneda)
                    otra = 'USD' if moneda != 'USD' else 'EUR'
                    self.invalido(amount=simbolo + '10', currency=otra)

    def test_monedas_ambiguas_y_desconocidas(self):
        for simbolo in ['$', '¥']:
            self.invalido(amount=simbolo + '10', currency=None)
            moneda = 'USD' if simbolo == '$' else 'JPY'
            self.assertEqual(self.valido(amount=simbolo + '10', currency=moneda)['currency'], moneda)
        for moneda in ['XYZ', '', 123]:
            self.invalido(currency=moneda)
        self.invalido(currency=None)
        self.invalido(amount='€10', currency='XYZ')
        self.invalido(amount='?10')

    def test_fechas(self):
        for entrada, esperado in [
            ('2025-03-10 14:22:00', '2025-03-10T14:22:00'),
            ('10/03/2025 14:22', '2025-03-10T14:22:00'),
            ('2025-03-10T14:22:00Z', '2025-03-10T14:22:00+00:00'),
            ('2025-03-10T14:22:00-06:00', '2025-03-10T14:22:00-06:00')]:
            with self.subTest(entrada=entrada):
                self.assertEqual(self.valido(timestamp=entrada)['timestamp'], esperado)
        for valor in ['2025-02-30 14:22:00', '2025-03-10', 'ayer', None, '2025-03-10T25:22:00Z']:
            self.invalido(timestamp=valor)

    def test_estados(self):
        for entrada, esperado in [('completed', 'SUCCESS'), ('OK', 'SUCCESS'), ('success', 'SUCCESS'),
                                  ('FaIlEd', 'FAILED'), ('pEnDiNg', 'PENDING')]:
            self.assertEqual(self.valido(status=entrada)['status'], esperado)
        self.invalido(status='unknown')
        self.invalido(status=None)

    def test_duplicados_primer_valido_global(self):
        otro = dict(transaction_id=204, total=5, currency_code='USD', created_at='10/03/2025 14:22', state='OK')
        resultado = procesar([registro(id=204, amount=-1), registro(id='204'), otro])
        self.assertEqual(len(resultado['validos']), 1)
        self.assertEqual(len(resultado['invalidos']), 2)
        self.assertIn('ID duplicado', resultado['invalidos'][1]['motivos'])
        self.assertEqual(resultado['validos'][0]['amount'], Decimal('100.50'))

    def test_fuentes_invalidos_y_continuidad(self):
        ambiguo = registro(ref='r', date='2025-03-10T14:22:00Z', result='success')
        entradas = [registro(amount=-1), {}, ambiguo, None, registro(id='dos', status='FAILED'),
                    registro(id='tres', status='PENDING')]
        copia = copy.deepcopy(entradas)
        r = procesar(entradas)
        self.assertEqual(entradas, copia)
        self.assertEqual(r['invalidos'][0]['original'], entradas[0])
        self.assertIn('Fuente ambigua', r['invalidos'][2]['motivos'])
        self.assertEqual(r['metricas']['por_fuente'], {'SOURCE_1': 3, 'UNKNOWN': 3})
        self.assertEqual(r['metricas']['por_estado'], {'SUCCESS': 0, 'FAILED': 1, 'PENDING': 1})
        self.assertEqual(r['metricas']['montos_por_moneda'], {'USD': Decimal('201.00')})

    def test_configuracion_realmente_utilizada(self):
        reglas = cargar_reglas()
        reglas['estados'] = {'nuevo': 'PENDING'}
        reglas['monedas']['USD'] = ['U!']
        reglas['formatos_fecha'] = ['%Y.%m.%d']
        reglas['fuentes']['SOURCE_1']['id'] = 'identificador'
        r = registro(amount='U!10', currency=None, status='nuevo', timestamp='2025.03.10')
        r['identificador'] = r.pop('id')
        salida = procesar([r], reglas)
        self.assertEqual(len(salida['validos']), 1)
        self.assertEqual(salida['validos'][0]['status'], 'PENDING')

    def test_precision_decimal_y_serializacion(self):
        with localcontext() as contexto:
            contexto.prec = 6
            r = procesar([registro(amount='123456789012345678901234567890.12'), registro(id='dos', amount='0.01')])
        self.assertEqual(r['metricas']['montos_por_moneda']['USD'], Decimal('123456789012345678901234567890.13'))
        self.assertEqual(serializar(Decimal('10050')), '10050.00')
        self.assertEqual(serializar(Decimal('1.2345')), '1.2345')

    def test_archivos_y_vacio(self):
        self.assertEqual(procesar_archivo(RAIZ / 'datos/invalidos.json')['validos'], [])
        mixtos = procesar_archivo(RAIZ / 'datos/mixtos.json')
        self.assertEqual(mixtos['metricas']['validos'], 3)
        self.assertEqual(mixtos['metricas']['invalidos'], 7)
        self.assertEqual(procesar([])['metricas']['total_procesado'], 0)
        with self.assertRaises(ValueError):
            procesar({})


if __name__ == '__main__':
    unittest.main()
