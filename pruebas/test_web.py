import csv
import io
import unittest
from decimal import Decimal
from pathlib import Path

from vista import filtrar_transacciones, filas_presentacion, generar_csv, procesar_contenido

RAIZ = Path(__file__).resolve().parents[1]


class WebDatosTests(unittest.TestCase):
    def test_archivos_y_totales_separados(self):
        for nombre, validos, invalidos in [('validos', 3, 0), ('invalidos', 0, 6), ('mixtos', 3, 7)]:
            with self.subTest(nombre=nombre):
                r = procesar_contenido((RAIZ / 'datos' / (nombre + '.json')).read_bytes())
                self.assertEqual(len(r['validos']), validos)
                self.assertEqual(len(r['invalidos']), invalidos)
                self.assertEqual(r['metricas']['montos_por_moneda'], {'USD': Decimal('10150.50'), 'EUR': Decimal('99.99')} if validos else {})

    def test_busqueda_y_filtros_combinados_csv(self):
        r = procesar_contenido((RAIZ / 'datos/mixtos.json').read_bytes())
        visibles = filtrar_transacciones(r['validos'], estado='SUCCESS', moneda='USD', fuente='SOURCE_2', busqueda=' 204 ')
        filas = list(csv.DictReader(io.StringIO(generar_csv(visibles).decode('utf-8-sig'))))
        self.assertEqual([v['id'] for v in filas], ['204'])
        self.assertEqual(filas[0]['amount'], '10050.00')
        self.assertEqual(filas[0]['timestamp'], '2025-03-10T14:22:00')
        self.assertEqual(len(r['invalidos']), 7)
        self.assertEqual(len(filtrar_transacciones(r['validos'], busqueda='TX_')), 1)
        self.assertEqual(filtrar_transacciones(r['validos'], estado='FAILED'), [])

    def test_json_decimal_exacto_y_presentacion(self):
        contenido = b'[{"id":"x","amount":1234567890.123456789,"currency":"USD","timestamp":"2025-03-10 14:22:00","status":"OK"}]'
        r = procesar_contenido(contenido)
        self.assertEqual(r['validos'][0]['amount'], Decimal('1234567890.123456789'))
        self.assertEqual(filas_presentacion(r['validos'])[0]['amount'], '1234567890.123456789')

    def test_errores_y_vacio(self):
        for contenido in [b'{mal', b'{}', b'\xff']:
            with self.subTest(contenido=contenido), self.assertRaises((ValueError, UnicodeError)):
                procesar_contenido(contenido)
        self.assertEqual(procesar_contenido(b'[]')['metricas']['total_procesado'], 0)
        self.assertEqual(len(list(csv.reader(io.StringIO(generar_csv([]).decode('utf-8-sig'))))), 1)


class DashboardTests(unittest.TestCase):
    def crear(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(str(RAIZ / 'main.py')).run(timeout=20)

    def cargar(self, nombre='mixtos'):
        at = self.crear()
        at.file_uploader[0].set_value((nombre + '.json', (RAIZ / 'datos' / (nombre + '.json')).read_bytes(), 'application/json')).run()
        at.button[0].click().run(timeout=20)
        self.assertEqual(len(at.exception), 0)
        return at

    def test_inicio_y_carga_tres_archivos(self):
        for nombre, total in [('validos', '3'), ('invalidos', '6'), ('mixtos', '10')]:
            with self.subTest(nombre=nombre):
                at = self.cargar(nombre)
                self.assertEqual(at.metric[0].value, total)
                self.assertEqual(len(at.tabs), 3)

    def test_filtros_y_limpieza_dashboard(self):
        at = self.cargar()
        at.selectbox(key='estado').select('SUCCESS')
        at.selectbox(key='moneda').select('USD')
        at.selectbox(key='fuente').select('SOURCE_2')
        at.text_input(key='busqueda').set_value('204').run()
        self.assertEqual(at.dataframe[0].value['id'].tolist(), ['204'])
        self.assertEqual(len(at.session_state['resultado']['invalidos']), 7)
        self.assertEqual(at.metric[0].value, '10')
        at.button[1].click().run()
        self.assertEqual(len(at.dataframe[0].value), 3)
        self.assertEqual(len(at.exception), 0)

    def test_cambio_archivo_limpia_resultados_y_error(self):
        at = self.cargar()
        at.file_uploader[0].set_value(('error.json', b'{mal', 'application/json')).run()
        self.assertEqual(len(at.metric), 0)
        at.button[0].click().run()
        self.assertEqual(len(at.error), 1)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.metric), 0)


if __name__ == '__main__':
    unittest.main()
