import csv
import json
import tempfile
import time
import tkinter as tk
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from interfaz import Aplicacion, CAMPOS, exportar_csv, filtrar_transacciones
from normalizador import procesar, procesar_archivo

RAIZ = Path(__file__).resolve().parents[1]


def datos():
    return [dict(id='Tx-A', amount=Decimal('10050'), currency='USD', timestamp='2025-03-10T14:22:00', status='SUCCESS', source='SOURCE_1'),
            dict(id='tx-B', amount=Decimal('99.99'), currency='EUR', timestamp='2025-03-10T14:22:00+00:00', status='FAILED', source='SOURCE_3'),
            dict(id='OTRO', amount=Decimal('1.2345'), currency='USD', timestamp='2025-03-10T14:22:00-06:00', status='PENDING', source='SOURCE_2')]


class FiltrosExportacionTests(unittest.TestCase):
    def test_sin_filtros_preserva_datos(self):
        registros = datos()
        self.assertEqual(filtrar_transacciones(registros), registros)
        self.assertEqual(filtrar_transacciones([]), [])

    def test_filtros_individuales(self):
        for opciones, ids in [({'estado': 'FAILED'}, ['tx-B']), ({'moneda': 'USD'}, ['Tx-A', 'OTRO']),
                              ({'fuente': 'SOURCE_2'}, ['OTRO']), ({'busqueda': ' TX- '}, ['Tx-A', 'tx-B'])]:
            with self.subTest(opciones=opciones):
                self.assertEqual([r['id'] for r in filtrar_transacciones(datos(), **opciones)], ids)

    def test_filtros_combinados_y_sin_coincidencias(self):
        self.assertEqual([r['id'] for r in filtrar_transacciones(datos(), estado='SUCCESS', moneda='USD', fuente='SOURCE_1', busqueda='a')], ['Tx-A'])
        self.assertEqual(filtrar_transacciones(datos(), estado='FAILED', moneda='USD'), [])
        self.assertEqual(filtrar_transacciones(datos(), busqueda='inexistente'), [])

    def test_csv_visibles_exactitud_encabezados_y_unicode(self):
        registros = datos()
        registros[0]['id'] = 'ñ, "uno"\nsiguiente'
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'salida.csv'
            visibles = filtrar_transacciones(registros, moneda='USD')
            self.assertEqual(exportar_csv(ruta, visibles), 2)
            with ruta.open(encoding='utf-8-sig', newline='') as archivo:
                lector = csv.DictReader(archivo)
                filas = list(lector)
                self.assertEqual(lector.fieldnames, list(CAMPOS))
            self.assertEqual([r['amount'] for r in filas], ['10050.00', '1.2345'])
            self.assertEqual(filas[0]['id'], registros[0]['id'])
            self.assertEqual(filas[1]['timestamp'], registros[2]['timestamp'])
            self.assertEqual(registros[0]['amount'], Decimal('10050'))

    def test_csv_vacio_y_error_de_escritura(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'vacio.csv'
            self.assertEqual(exportar_csv(ruta, []), 0)
            with ruta.open(encoding='utf-8-sig', newline='') as archivo:
                self.assertEqual(list(csv.reader(archivo)), [list(CAMPOS)])
            with self.assertRaises(OSError):
                exportar_csv(Path(carpeta) / 'no_existe' / 'salida.csv', datos())


class IntegracionTkTests(unittest.TestCase):
    def setUp(self):
        self.raiz = tk.Tk()
        self.raiz.withdraw()
        self.app = Aplicacion(self.raiz)
        self.raiz.update()

    def tearDown(self):
        self.app.cerrar()

    def esperar(self):
        limite = time.monotonic() + 5
        while self.app.ocupada and time.monotonic() < limite:
            self.raiz.update()
            time.sleep(0.01)
        self.assertFalse(self.app.ocupada)

    def test_ventana_inicio_redimension_y_archivos(self):
        self.raiz.deiconify()
        for nombre, validos, invalidos in [('validos', 3, 0), ('invalidos', 0, 6), ('mixtos', 3, 7)]:
            with self.subTest(nombre=nombre):
                ruta = RAIZ / 'datos' / (nombre + '.json')
                with patch('interfaz.filedialog.askopenfilename', return_value=str(ruta)):
                    self.app.seleccionar()
                self.assertEqual(self.app.nombre.get(), nombre + '.json')
                self.app.procesar()
                self.esperar()
                self.assertEqual(len(self.app.tabla.get_children()), validos)
                self.assertEqual(len(self.app.tabla_invalidos.get_children()), invalidos)
                self.assertEqual(self.app.resumen[0].get(), str(validos + invalidos))
        m = self.app.resultado['metricas']
        self.assertEqual(m['montos_por_moneda'], {'USD': Decimal('10150.50'), 'EUR': Decimal('99.99')})
        for ancho, alto in [(980, 700), (1400, 900)]:
            self.raiz.geometry(f'{ancho}x{alto}')
            self.raiz.update()
            self.assertTrue(self.app.tabla.winfo_ismapped())
            self.assertTrue(self.app.boton_procesar.winfo_ismapped())

    def test_filtros_detalles_invalidos_y_exportacion_integrados(self):
        r = procesar_archivo(RAIZ / 'datos/mixtos.json')
        self.app.mostrar_resultado(r)
        for clave, valor in [('estado', 'SUCCESS'), ('moneda', 'USD'), ('fuente', 'SOURCE_2'), ('busqueda', '204')]:
            self.app.filtros[clave].set(valor)
        self.assertEqual([v['id'] for v in self.app.visibles], ['204'])
        self.assertEqual(len(self.app.tabla_invalidos.get_children()), 7)
        self.assertEqual(self.app.resultado['metricas'], r['metricas'])
        self.app.tabla.selection_set('0')
        self.app.detalle_valido()
        self.assertIn('10050.00', self.app.detalle.get('1.0', 'end'))
        self.app.tabla_invalidos.selection_set('0')
        self.app.detalle_invalido()
        texto = self.app.original.get('1.0', 'end')
        self.assertIn('JSON original:', texto)
        self.assertIn('ID vacío', texto)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'vista.csv'
            with patch('interfaz.filedialog.asksaveasfilename', return_value=str(ruta)), patch('interfaz.messagebox.showinfo') as confirmar:
                self.app.exportar()
                confirmar.assert_called_once()
            with ruta.open(encoding='utf-8-sig', newline='') as archivo:
                filas = list(csv.DictReader(archivo))
            self.assertEqual([v['id'] for v in filas], ['204'])
        self.app.limpiar()
        self.assertEqual(len(self.app.visibles), 3)

    def test_errores_lectura_json_raiz_y_procesamiento(self):
        self.app.mostrar_resultado(procesar_archivo(RAIZ / 'datos/validos.json'))
        with tempfile.TemporaryDirectory() as carpeta:
            for contenido in ['{mal', '{}']:
                ruta = Path(carpeta) / 'error.json'
                ruta.write_text(contenido, encoding='utf-8')
                self.app.archivo = ruta
                with patch('interfaz.messagebox.showerror') as error:
                    self.app.procesar()
                    self.esperar()
                    error.assert_called_once()
                self.assertIsNone(self.app.resultado)
                self.assertEqual(len(self.app.tabla.get_children()), 0)
            self.app.archivo = Path(carpeta) / 'ausente.json'
            with patch('interfaz.messagebox.showerror') as error:
                self.app.procesar()
                self.esperar()
                error.assert_called_once()
            with patch('interfaz.procesar_archivo', side_effect=RuntimeError('fallo simulado')), patch('interfaz.messagebox.showerror') as error:
                self.app.procesar()
                self.esperar()
                error.assert_called_once()

    def test_cancelaciones_y_error_exportacion(self):
        with patch('interfaz.filedialog.askopenfilename', return_value=''):
            self.app.seleccionar()
        self.assertIsNone(self.app.archivo)
        self.app.mostrar_resultado(procesar([]))
        with patch('interfaz.filedialog.asksaveasfilename', return_value=''), patch('interfaz.exportar_csv') as exportar:
            self.app.exportar()
            exportar.assert_not_called()
        with patch('interfaz.filedialog.asksaveasfilename', return_value='ejemplo.csv'), patch('interfaz.exportar_csv', side_effect=OSError('Sin permiso')), patch('interfaz.messagebox.showerror') as error:
            self.app.exportar()
            error.assert_called_once()

    def test_main_inicia_bucle(self):
        import main_tkinter as main
        with patch.object(main, 'Aplicacion') as crear, patch.object(main.tk, 'Tk') as raiz:
            main.main()
            crear.assert_called_once_with(raiz.return_value)
            raiz.return_value.mainloop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
