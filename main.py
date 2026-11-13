"""Dashboard web local. Ejecutar: python -m streamlit run main.py."""
import hashlib
import json

import streamlit as st

from normalizador import serializar
from vista import filtrar_transacciones, filas_presentacion, generar_csv, procesar_contenido


def limpiar_filtros():
    for clave in ('estado', 'moneda', 'fuente', 'busqueda'):
        st.session_state[clave] = ''


def main():
    st.set_page_config(page_title='Transacciones | Dashboard académico', page_icon='📊', layout='wide')
    st.markdown('''<style>
    [data-testid="stMainBlockContainer"] {max-width:1450px;padding-top:5rem;padding-bottom:2rem;}
    @media (max-width:640px) {
      [data-testid="stMainBlockContainer"] {padding-top:4.5rem;padding-left:1rem;padding-right:1rem;}
      h1 {font-size:2rem;}
    }
    [data-testid="stMetric"] {border:1px solid #dce4ec;border-radius:12px;padding:18px;}
    h1 {letter-spacing:-.035em;}
    </style>''', unsafe_allow_html=True)
    st.caption('SISTEMA ACADÉMICO · NORMALIZACIÓN MULTIFUENTE')
    st.title('Una vista clara de tus transacciones')
    st.write('Carga un JSON, revisa su calidad y explora los resultados por estado, moneda y fuente.')
    with st.container(border=True):
        archivo = st.file_uploader('Selecciona un archivo JSON', type=['json'], key='archivo')
        contenido = archivo.getvalue() if archivo is not None else None
        identidad = (archivo.name, hashlib.sha256(contenido).hexdigest()) if archivo is not None else None
        if identidad != st.session_state.get('identidad'):
            st.session_state.identidad = identidad
            st.session_state.pop('resultado', None)
            st.session_state.pop('error', None)
            limpiar_filtros()
        if archivo is not None:
            st.caption(f'Archivo seleccionado: {archivo.name} · {len(contenido):,} bytes')
        if st.button('Procesar transacciones', type='primary', disabled=archivo is None):
            st.session_state.pop('resultado', None)
            st.session_state.pop('error', None)
            limpiar_filtros()
            try:
                with st.spinner('Normalizando y validando registros…'):
                    st.session_state.resultado = procesar_contenido(contenido)
            except Exception as exc:
                st.session_state.error = f'No se pudo leer o procesar el archivo: {exc}'
        if st.session_state.get('error'):
            st.error(st.session_state.error)
    resultado = st.session_state.get('resultado')
    if resultado is None:
        st.info('Selecciona un archivo y pulsa Procesar transacciones. Los resultados aparecerán aquí.')
        return
    m = resultado['metricas']
    st.success(f"Procesamiento completo: {m['total_procesado']} registros revisados.")
    tarjetas = st.columns(3)
    tarjetas[0].metric('Procesados', m['total_procesado'])
    tarjetas[1].metric('Válidos', m['validos'], delta=f"{m['porcentaje_validos']:.2f} % del total", delta_color='off')
    tarjetas[2].metric('Inválidos', m['invalidos'], delta=f"{m['porcentaje_invalidos']:.2f} % del total", delta_color='off')
    validos, invalidos, metricas = st.tabs(['Transacciones válidas', f"Registros inválidos ({m['invalidos']})", 'Análisis y métricas'])
    with validos:
        st.subheader('Explora las transacciones válidas')
        st.caption('Los filtros se combinan. Las métricas siempre describen el archivo completo.')
        columnas = st.columns(4)
        opciones = [('estado', 'Estado', ['SUCCESS', 'FAILED', 'PENDING']),
                    ('moneda', 'Moneda', sorted({r['currency'] for r in resultado['validos']})),
                    ('fuente', 'Fuente', sorted({r['source'] for r in resultado['validos']}))]
        filtros = {}
        for columna, (clave, etiqueta, valores) in zip(columnas, opciones):
            filtros[clave] = columna.selectbox(etiqueta, ['', *valores], format_func=lambda v: v or 'Todos', key=clave)
        filtros['busqueda'] = columnas[3].text_input('Buscar identificador', key='busqueda', placeholder='Coincidencia parcial…')
        st.button('Limpiar filtros', on_click=limpiar_filtros)
        visibles = filtrar_transacciones(resultado['validos'], **filtros)
        st.caption(f"{len(visibles)} de {m['validos']} transacciones válidas visibles")
        if visibles:
            seleccion = st.dataframe(filas_presentacion(visibles), hide_index=True, width='stretch', on_select='rerun', selection_mode='single-row', key='tabla_validos')
            indices = seleccion.selection.rows
            if indices and indices[0] < len(visibles):
                with st.expander('Detalle de la transacción seleccionada', expanded=True):
                    st.json(json.loads(json.dumps(visibles[indices[0]], default=serializar)))
        else:
            st.info('No hay transacciones que coincidan con los filtros actuales.')
        try:
            csv = generar_csv(visibles)
            st.download_button('Descargar válidos visibles · CSV', data=csv, file_name='transacciones_visibles.csv', mime='text/csv', key='descarga', on_click='ignore')
            st.caption('CSV con encabezados y montos exactos. Una vista vacía descarga solo encabezados.')
        except (OSError, ValueError, TypeError) as exc:
            st.error(f'No se pudo preparar la exportación: {exc}')
    with invalidos:
        st.subheader('Revisión de registros inválidos')
        st.caption('Esta sección siempre incluye todos los inválidos; los filtros de válidos no los ocultan.')
        if not resultado['invalidos']:
            st.success('No se encontraron registros inválidos.')
        else:
            filas = [{'N.º': i + 1, 'Fuente': r['source'], 'Motivos': ' · '.join(r['motivos'])} for i, r in enumerate(resultado['invalidos'])]
            st.dataframe(filas, hide_index=True, width='stretch')
            indice = st.selectbox('Consultar JSON original del registro inválido', range(len(filas)), format_func=lambda i: f"Registro {i + 1} · {resultado['invalidos'][i]['source']}", key='invalido')
            registro = resultado['invalidos'][indice]
            for motivo in registro['motivos']:
                st.write('• ' + motivo)
            st.code(json.dumps(registro['original'], ensure_ascii=False, indent=2, default=serializar), language='json')
    with metricas:
        st.subheader('Calidad y distribución del archivo')
        izquierda, derecha = st.columns(2)
        with izquierda:
            st.markdown('#### Conteos por estado')
            st.bar_chart([{'Estado': k, 'Cantidad': v} for k, v in m['por_estado'].items()], x='Estado', y='Cantidad', color='#28788e')
            st.dataframe([{'Estado': k, 'Cantidad': v} for k, v in m['por_estado'].items()], hide_index=True, width='stretch')
        with derecha:
            st.markdown('#### Conteos por fuente')
            if m['por_fuente']:
                st.bar_chart([{'Fuente': k, 'Cantidad': v} for k, v in m['por_fuente'].items()], x='Fuente', y='Cantidad', color='#52769c')
            st.dataframe([{'Fuente': k, 'Cantidad': v} for k, v in m['por_fuente'].items()], hide_index=True, width='stretch')
        st.markdown('#### Totales monetarios por moneda')
        if m['montos_por_moneda']:
            st.dataframe([{'Moneda': k, 'Monto total': serializar(v)} for k, v in sorted(m['montos_por_moneda'].items())], hide_index=True, width='stretch')
        else:
            st.info('No hay importes válidos para sumar.')
        st.caption('Estados y montos: solo válidos. Fuentes: todos los registros. No se suman ni convierten monedas distintas.')


if __name__ == '__main__':
    main()
