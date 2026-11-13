"""Regresiones para fuentes incompletas, símbolos compatibles y porcentajes."""
import copy
import unittest

from normalizador import cargar_reglas, procesar, procesar_archivo
from pruebas.test_sistema import RAIZ, registro


class CasosAdicionalesTests(unittest.TestCase):
    def test_fuentes_con_cualquier_campo_obligatorio_ausente(self):
        originales = procesar_archivo(RAIZ / 'datos/validos.json')
        import json
        entradas = json.loads((RAIZ / 'datos/validos.json').read_text(encoding='utf-8'))
        reglas = cargar_reglas()
        for fuente, original in zip(reglas['fuentes'], entradas):
            for campo in reglas['fuentes'][fuente].values():
                with self.subTest(fuente=fuente, campo=campo):
                    incompleto = dict(original)
                    del incompleto[campo]
                    copia = copy.deepcopy(incompleto)
                    r = procesar([incompleto])
                    self.assertEqual(r['validos'], [])
                    self.assertEqual(r['invalidos'][0]['source'], fuente)
                    self.assertIn(f'Campo obligatorio faltante: {campo}', r['invalidos'][0]['motivos'])
                    self.assertEqual(r['invalidos'][0]['original'], copia)
                    self.assertEqual(r['metricas']['por_fuente'], {fuente: 1})

    def test_campos_caracteristicos_sin_resto_del_registro(self):
        for campo, fuente in [('id', 'SOURCE_1'), ('timestamp', 'SOURCE_1'),
                              ('transaction_id', 'SOURCE_2'), ('state', 'SOURCE_2'),
                              ('ref', 'SOURCE_3'), ('result', 'SOURCE_3')]:
            with self.subTest(campo=campo):
                r = procesar([{campo: None}])
                self.assertEqual(r['invalidos'][0]['source'], fuente)
                self.assertTrue(any('Campo obligatorio faltante' in m for m in r['invalidos'][0]['motivos']))

    def test_fuente_desconocida_o_ambigua(self):
        for original in [{}, {'amount': 100}, {'otra': 1}, None, [],
                         {'id': 'a', 'ref': 'b'}, {'timestamp': None, 'state': None}]:
            with self.subTest(original=original):
                r = procesar([original])
                self.assertEqual(r['invalidos'][0]['source'], 'UNKNOWN')
                self.assertEqual(r['metricas']['por_fuente'], {'UNKNOWN': 1})
                if isinstance(original, dict) and ('ref' in original or 'state' in original):
                    self.assertIn('Fuente ambigua', r['invalidos'][0]['motivos'])

    def test_matriz_completa_simbolos_ambiguos(self):
        reglas = cargar_reglas()
        compatibles = {'$': {'USD', 'MXN', 'CAD'}, '¥': {'JPY', 'CNY'}}
        for simbolo, monedas in compatibles.items():
            for codigo in reglas['monedas']:
                for monto in [simbolo + '100', '100' + simbolo]:
                    with self.subTest(monto=monto, codigo=codigo):
                        r = procesar([registro(amount=monto, currency=codigo.lower())])
                        self.assertEqual(len(r['validos']), int(codigo in monedas))
                        self.assertEqual(len(r['invalidos']), int(codigo not in monedas))
            for codigo in [None, '', 'XYZ']:
                self.assertEqual(len(procesar([registro(amount=simbolo + '100', currency=codigo)])['invalidos']), 1)

    def test_compatibilidad_se_lee_de_configuracion(self):
        reglas = cargar_reglas()
        reglas['simbolos_ambiguos']['¥'] = ['USD']
        self.assertEqual(len(procesar([registro(amount='¥100')], reglas)['validos']), 1)
        self.assertEqual(len(procesar([registro(amount='¥100', currency='JPY')], reglas)['invalidos']), 1)

    def test_porcentajes_vacio_validos_invalidos_y_mixtos(self):
        casos = [([], 0.0, 0.0), ([registro()], 100.0, 0.0),
                 ([{}], 0.0, 100.0), ([registro(), {}, None], 100 / 3, 200 / 3)]
        for entradas, validos, invalidos in casos:
            with self.subTest(entradas=entradas):
                m = procesar(entradas)['metricas']
                self.assertAlmostEqual(m['porcentaje_validos'], validos)
                self.assertAlmostEqual(m['porcentaje_invalidos'], invalidos)
                self.assertEqual(m['total_procesado'], len(entradas))

    def test_continuidad_y_metricas_de_incompletos(self):
        incompleto = registro()
        del incompleto['amount']
        r = procesar([incompleto, registro(), {'ref': 'r'}, {'amount': 5}, {'id': 'a', 'ref': 'b'}])
        self.assertEqual(len(r['validos']), 1)
        self.assertEqual(r['metricas']['por_fuente'], {'SOURCE_1': 2, 'SOURCE_3': 1, 'UNKNOWN': 2})
        self.assertEqual(r['metricas']['porcentaje_validos'], 20.0)
        self.assertEqual(r['metricas']['porcentaje_invalidos'], 80.0)
        self.assertEqual(r['metricas']['por_estado']['SUCCESS'], 1)


if __name__ == '__main__':
    unittest.main()
