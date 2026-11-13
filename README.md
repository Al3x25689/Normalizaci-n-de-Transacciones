# Normalización y Exploración de Transacciones Multifuente

## 1. Descripción del proyecto

Proyecto académico desarrollado en **Python 3.14** para leer transacciones JSON provenientes de tres fuentes, normalizarlas a un esquema común, validar sus datos y explorar los resultados mediante una interfaz web local creada con **Streamlit**.

La interfaz permite cargar archivos, consultar transacciones válidas e inválidas, combinar filtros, revisar métricas y exportar registros válidos a CSV. Las reglas de negocio ya fueron definidas; Codex se utilizó como apoyo para implementarlas y probarlas.

## 2. Objetivo

Normalizar transacciones heterogéneas, identificar inconsistencias y presentar información comprensible mediante una interfaz interactiva, separando la lógica de negocio de la visualización.

## 3. Tecnologías utilizadas

- Python 3.14 (64 bits).
- Streamlit (interfaz web local).
- JSON (datos y configuración).
- `decimal.Decimal` (importes monetarios).
- `unittest` (pruebas automatizadas).
- Tkinter/ttk (utilizado inicialmente para desarrollar
  un prototipo de escritorio, posteriormente reemplazado
  por Streamlit).
- Codex (asistencia al desarrollo).

## 4. Esquema normalizado y decisiones 

**Esquema:** `id`, `amount`, `currency`, `timestamp`, `status`, `source`.

**Fuentes:**

| Fuente | Campos de entrada |
|---|---|
| SOURCE_1 | `id`, `amount`, `currency`, `timestamp`, `status` |
| SOURCE_2 | `transaction_id`, `total`, `currency_code`, `created_at`, `state` |
| SOURCE_3 | `ref`, `amount`, `date`, `result` |

**Reglas definidas:** identificación de fuente mediante campos característicos; identificación y validación de campos obligatorios por separado; IDs numéricos convertidos a texto; IDs vacíos rechazados; montos enteros interpretados como unidades; importes decimales con `Decimal`; aceptación de cero y rechazo de negativos/no finitos; monedas ISO soportadas (USD, EUR, GBP, JPY, MXN, CAD, BRL, CHF, CNY y KRW); símbolos monetarios compatibles con códigos explícitos; estados normalizados a `SUCCESS`, `FAILED` o `PENDING`; fechas normalizadas a ISO 8601 sin inventar zona horaria; duplicados posteriores al primer ID válido marcados como inválidos; conservación de registros rechazados y motivos.

Los conteos por fuente incluyen válidos e inválidos (o `UNKNOWN` si no puede determinarse); conteos por estado y totales monetarios incluyen únicamente válidos. No se suman ni convierten monedas diferentes.

---

## 5. Primera etapa — Implementación de la lógica

### Primer prompt utilizado — Normalización y validación

**Contexto:** Se solicitó a Codex desarrollar el sistema académico en Python 3.14 con biblioteca estándar, sin interfaz todavía, para las tres estructuras SOURCE_1, SOURCE_2 y SOURCE_3.

**Prompt utilizado:**

Actúa como desarrollador Python senior. Vamos a crear un sistema académico de normalización de transacciones multifuente usando Python 3.14 y únicamente la biblioteca estándar.

Objetivo de esta primera etapa: implementar la lógica de procesamiento, sin interfaz gráfica todavía.

Los datos llegan desde un archivo JSON con tres estructuras:
- SOURCE_1: id, amount, currency, timestamp, status.
- SOURCE_2: transaction_id, total, currency_code, created_at, state.
- SOURCE_3: ref, amount, date, result.
Esquema normalizado:

id, amount, currency, timestamp, status, source.

Reglas obligatorias:
1. Detectar automáticamente la fuente por sus campos.
2. Convertir identificadores numéricos a texto. Rechazar ID vacíos.
3. Los montos enteros representan unidades: 10050 = 10050.00.
4. Aceptar montos decimales, incluido €99,99. Permitir cero y rechazar negativos, valores no numéricos o no finitos.
5. Utilizar Decimal para cálculos monetarios.
6. Normalización de monedas:
- Soportar USD, EUR, GBP, JPY, MXN, CAD, BRL, CHF, CNY y KRW.
- Utilizar códigos ISO 4217 de tres letras, normalizados a mayúsculas.
- Reconocer símbolos inequívocos como €, £, R$ y ₩.
- Reconocer símbolos explícitos como US$, MX$, C$ y CN¥.
- No asumir una moneda cuando el símbolo sea ambiguo, como $ o ¥.
- Dar prioridad al código ISO explícito, pero validar que no contradiga el símbolo del monto.
- Marcar como inválidas las monedas desconocidas, ambiguas o contradictorias.
- Mantener los totales monetarios separados por moneda.
- No convertir importes entre monedas.
- Definir las monedas y sus símbolos en configuracion/reglas.json, evitando mapeos duplicados en el código.
desconocidas o contradicciones entre símbolo y código.
6. Mapear completed, OK y success a SUCCESS; reconocer FAILED y PENDING sin distinguir mayúsculas. Rechazar estados desconocidos.
7. Aceptar fechas YYYY-MM-DD HH:MM:SS, DD/MM/YYYY HH:MM e ISO 8601 con Z. Convertir a ISO 8601 conservando la hora y la información de zona original, sin asignar zonas ficticias.
8. Aceptar el primer registro válido de cada ID y marcar como inválidos los siguientes duplicados.
9. Separar los registros inválidos, conservando el original y sus motivos. Continuar procesando los demás registros.
Métricas: total procesado, válidos, inválidos, conteos por estado, conteos por fuente y suma de montos por moneda. Los totales monetarios y conteos por estado solo consideran registros válidos.

Arquitectura:
- normalizador.py
- validador.py
- metricas.py
- configuracion/reglas.json
- datos/ con archivos JSON válidos, inválidos y mixtos.
- pruebas/ con pruebas unittest.
El archivo de configuración debe contener mapeos de estados, monedas, formatos de fecha y campos por fuente, y utilizarse realmente.

Incluye los tres registros originales de la actividad en los datos de prueba. Crea pruebas para conversiones, fechas, duplicados, estados, monedas y métricas.

No desarrolles todavía la interfaz Tkinter.

Importante: las reglas anteriores fueron decididas por mi. No las modifiques. Si encuentras una ambigüedad de negocio, consúltala antes de implementar.

Al finalizar, ejecuta las pruebas e informa sus resultados.

### ¿Qué se solicitó a la IA?

Se pidió implementar los módulos de normalización, validación y métricas, con configuración centralizada y archivos de prueba. Se prohibió modificar unilateralmente las reglas.

### Resultado obtenido

Codex implementó la lógica inicial y reportó **12 pruebas correctas**. Antes de implementarla, consultó tres decisiones que no estaban totalmente resueltas: símbolos monetarios ambiguos, conteos por fuente y registros que coincidieran con varias fuentes.

### Decisiones que se le explicaron a la IA

1. Aceptar símbolos ambiguos cuando exista un código explícito compatible; rechazar contradicciones con símbolos inequívocos.
2. Contar todos los registros por fuente, válidos e inválidos, y utilizar `UNKNOWN` cuando no pueda determinarse.
3. Rechazar registros con fuentes ambiguas y contabilizarlos como `UNKNOWN`.

---

## 6. Segunda etapa — Correcciones y pruebas adicionales

### Segundo prompt utilizado — Casos límite

Revisé la primera etapa y las 12 pruebas existentes pasan correctamente. Sin embargo, detecté algunos casos adicionales que debemos corregir antes de desarrollar Tkinter.
1. Identificación de fuentes incompletas: actualmente, si a un registro de SOURCE_1 le falta amount, se clasifica como UNKNOWN. Quiero que la detección de fuente sea independiente de la validación de campos obligatorios. Si puede identificarse inequívocamente por sus campos característicos, debe conservar su fuente y marcarse inválido por el campo faltante. Si coincide con varias fuentes o no hay información suficiente, utilizar UNKNOWN.
2. Compatibilidad de símbolos monetarios: actualmente se acepta ¥100 con currency: "USD". Esto debe rechazarse porque ¥ corresponde a JPY o CNY, no a USD. Un símbolo ambiguo puede aceptarse únicamente cuando el código explícito corresponde a una de las monedas representadas por ese símbolo. Por ejemplo, $100 con USD, MXN o CAD es válido, mientras que ¥100 con USD no lo es.
3. Métricas: agregar porcentaje de transacciones válidas e inválidas, manejando correctamente el caso de cero registros.
Agrega pruebas automatizadas específicas para estos escenarios y comprueba que las 12 pruebas originales sigan funcionando.

No desarrolles todavía la interfaz gráfica ni cambies las demás reglas de negocio.

Al finalizar, informa los cambios realizados y los resultados de las pruebas.



### ¿Qué se solicitó a la IA?

Se pidió corregir tres casos de borde detectados al revisar el comportamiento del normalizador, sin cambiar las demás reglas.

### Resultado obtenido

Codex informó **19 pruebas correctas**: las 12 anteriores (con dos expectativas ajustadas) y 7 nuevas. También actualizó el proyecto en `sistema_academico` y creó un respaldo previo.

---

## 7. Tercera etapa — Prototipo de escritorio con Tkinter

### Tercer prompt utilizado — Interfaz interactiva

De acuerdo continuemos con el proyecto de normalización de transacciones multifuente desarrollado en la primera etapa.

La lógica de normalización, validación y métricas ya está implementada y cuenta con 19 pruebas automatizadas correctas.

Ahora necesito desarrollar una interfaz gráfica utilizando Python 3.14, Tkinter y ttk, integrándola con los módulos existentes.
1. Interfaz gráfica
Desarrolla una aplicación de escritorio con un diseño moderno, profesional, intuitivo y redimensionable.

Utiliza colores sobrios, buena distribución de elementos y tablas legibles.

La aplicación debe incluir:

Carga y procesamiento
- Botón para seleccionar archivos JSON.
- Mostrar el nombre del archivo seleccionado.
- Botón para procesar las transacciones.
- Mostrar mensajes claros cuando existan errores de lectura o procesamiento.
Tabla de transacciones
- Utilizar ttk.Treeview.
- Mostrar ID, monto, moneda, fecha, estado y fuente.
- Incluir barras de desplazamiento.
- Permitir seleccionar registros para consultar sus detalles.
Filtros y búsqueda
- Filtrar por estado (SUCCESS, FAILED, PENDING).
- Filtrar por moneda.
- Filtrar por fuente.
- Buscar transacciones por identificador.
- Permitir combinar filtros y búsqueda.
- Incluir botón para limpiar los filtros.
Panel de métricas
- Total de registros procesados.
- Cantidad y porcentaje de válidos.
- Cantidad y porcentaje de inválidos.
- Conteos por estado.
- Conteos por fuente.
- Totales monetarios separados por moneda.
Registros inválidos
- Crear una pestaña independiente.
- Mostrar la fuente y los motivos de invalidación.
- Permitir consultar el registro JSON original.
- No ocultar registros inválidos.
Exportación CSV
- Exportar únicamente las transacciones válidas visibles según los filtros activos.
- Incluir encabezados.
- Conservar los montos y fechas normalizados.
- Mostrar confirmación de exportación o errores cuando corresponda.
Crear interfaz.py y main.py, reutilizando los módulos existentes:
- normalizador.py
- validador.py
- metricas.py
- configuracion/reglas.json
No duplicar la lógica de normalización dentro de Tkinter.

Utilizar exclusivamente la biblioteca estándar de Python.
3. Documentación
Crear o actualizar:

README.md
- Descripción del proyecto.
- Requisitos.
- Estructura de archivos.
- Instrucciones para ejecutar la aplicación.
- Explicación de filtros, métricas y exportación.
- Instrucciones para ejecutar las pruebas.
nota_tecnica.md (máximo una página)
- Esquema de datos.
- Decisiones de normalización y validación.
- Justificación de Tkinter.
- Uso de IA como apoyo.
- Ajustes realizados durante el desarrollo.
No inventar decisiones ni intervenciones. Si falta información, dejarla indicada para completar manualmente.
4. Verificación final
- Mantener las 19 pruebas automatizadas existentes.
- No modificar las reglas de negocio previamente definidas.
- Agregar pruebas para los filtros, búsqueda y exportación CSV.
- Comprobar que la interfaz se inicia correctamente.
- Verificar el procesamiento de archivos válidos, inválidos y mixtos.
- Comprobar que los registros inválidos no afectan los totales monetarios.
- Verificar que los filtros combinados funcionen correctamente.
- No alterar las pruebas existentes únicamente para obtener resultados correctos.

### ¿Qué se solicitó a la IA?

Integrar el núcleo ya probado con una interfaz de escritorio sin duplicar la lógica de negocio.

### Resultado obtenido

Se creó una interfaz Tkinter funcional con carga, filtros, tablas, métricas y exportación. Codex reportó **29 pruebas correctas**. Se decidió conservar esta versión como antecedente, aunque dejó de ser la interfaz principal.

**Evidencia pendiente:** insertar captura de la interfaz Tkinter.

---

## 8. Cuarta etapa — Migración a Streamlit

### Cuarto prompt utilizado — Interfaz web

Continuemos con el proyecto académico de normalización de transacciones multifuente.

Después de evaluar la aplicación de escritorio desarrollada con Tkinter, he tomado la decisión de utilizar una interfaz web en lugar de una aplicación de escritorio, porque considero que permitirá una exploración más intuitiva, una mejor presentación de las métricas y una experiencia más moderna.

Para ello, utilizaremos Streamlit con Python.
1. Objetivo
Sustituir la interfaz Tkinter por una aplicación web local, conservando toda la lógica de negocio existente.

El proyecto ya cuenta con 29 pruebas automatizadas aprobadas.

No quiero desarrollar nuevamente el normalizador ni modificar las reglas definidas anteriormente.
2. Interfaz web
Desarrolla un dashboard moderno, profesional, responsivo y fácil de utilizar.

Debe incluir:
- Carga de archivos JSON mediante el navegador.
- Procesamiento de transacciones.
- Tarjetas con total procesado, válidos, inválidos y porcentajes.
- Tabla interactiva de transacciones normalizadas.
- Filtros combinables por estado, moneda y fuente.
- Búsqueda por identificador.
- Sección independiente para registros inválidos, mostrando sus motivos y JSON original.
- Conteos por estado y fuente.
- Totales monetarios separados por moneda.
- Exportación CSV de las transacciones válidas visibles según los filtros.
- Mensajes claros para errores y operaciones exitosas.
Organiza la interfaz mediante secciones o pestañas, evitando saturar la pantalla.

Puedes incorporar gráficos sencillos para visualizar las métricas, siempre que utilicen los datos calculados por los módulos existentes.
3. Arquitectura
- Utilizar Streamlit como interfaz.
- Reutilizar normalizador.py, validador.py, metricas.py y configuracion/reglas.json.
- Separar la lógica de negocio de la presentación.
- Evitar duplicar las reglas de normalización.
- Mantener el esquema normalizado y todos los criterios de validación definidos.
- Conservar la versión Tkinter como respaldo, sin utilizarla como interfaz principal.
4. Pruebas
- Conservar las 29 pruebas automatizadas existentes.
- Adaptar las pruebas de interfaz cuando corresponda.
- Agregar pruebas para los filtros, búsqueda y exportación web.
- Comprobar la carga de JSON válidos, inválidos y mixtos.
- Verificar que los totales monetarios no mezclen monedas.
- No modificar las reglas de negocio para conseguir que las pruebas pasen.

5. Ejecución
Preparar el proyecto para ejecutarse mediante:
python -m streamlit run main.py
Crear requirements.txt con las dependencias necesarias.
6. Condiciones finales
Antes de modificar archivos, realiza un respaldo de la versión actual.

No elimines los módulos funcionales ni alteres las reglas de negocio.

Al finalizar:
1. Ejecuta las pruebas automatizadas.
2. Comprueba que Streamlit inicia correctamente.
3. Verifica el procesamiento de los archivos de ejemplo.
4. Informa los archivos modificados.
5. Explica cómo ejecutar la aplicación web.

### ¿Qué se solicitó a la IA?

Se pidió cambiar exclusivamente la presentación, reutilizando normalizador, validador, métricas y reglas de configuración.

### Resultado obtenido

Se implementó un dashboard local en Streamlit con tres secciones: transacciones válidas, registros inválidos y análisis/métricas. Permite filtros combinados, búsqueda de ID y exportación de válidos visibles a CSV.

**Evidencias:**

- `evidencias/streamlit_inicio.png` — carga y resumen del archivo.
- `evidencias/streamlit_filtros.png` — filtros combinados y búsqueda.
- `evidencias/streamlit_invalidos.png` — motivos y JSON original.
- `evidencias/streamlit_metricas.png` — gráficos y totales por moneda.
- `evidencias/streamlit_csv.png` — exportación abierta en Excel.

*Las imágenes anteriores son rutas propuestas: crear la carpeta y añadir capturas con esos nombres antes de publicar.*

---

## 9. Quinta etapa — Optimización de carga y presentación

### Quinto prompt utilizado — Rendimiento y diseño

**Problema detectado:** la interfaz tardaba aproximadamente 20 segundos en cargar y el encabezado aparecía cortado.

**Solicitud a la IA (resumen; completar con el prompt literal si se conserva):** corregir el margen superior, revisar la recarga automática de archivos de OneDrive y optimizar el inicio sin modificar la lógica de negocio.

### Resultado obtenido

Codex informó que corrigió el margen superior, desactivó la vigilancia automática de archivos y reinició Streamlit. Reportó una generación inicial de **2.13 segundos** y otra de **0.85 segundos**; estas mediciones no equivalen necesariamente al tiempo total de carga del navegador. Indicó **36 pruebas correctas**.

---

## 10. Arquitectura del proyecto

```text
sistema_academico/
├── main.py                 # Dashboard Streamlit
├── vista.py                # Carga JSON, filtros y exportación CSV
├── normalizador.py         # Normalización de transacciones
├── validador.py            # Validaciones
├── metricas.py             # Cálculo de métricas
├── configuracion/
│   └── reglas.json         # Configuración de reglas
├── datos/
│   ├── validos.json
│   ├── invalidos.json
│   └── mixtos.json
├── pruebas/
│   ├── test_sistema.py
│   ├── test_casos_adicionales.py
│   ├── test_interfaz.py
│   └── test_web.py
├── .streamlit/
│   └── config.toml
├── requirements.txt
├── requirements-lock.txt
├── nota_tecnica.md
└── README.md
```

## 11. Instalación y ejecución

**Requisito:** Python 3.14 de 64 bits.

Desde la carpeta raíz del proyecto, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run main.py
```

Abrir `http://localhost:8501` si el navegador no se abre automáticamente. Para detener el servidor, presionar `Ctrl+C` en la terminal.

## 12. Uso del dashboard

1. Seleccionar un archivo JSON de `datos/` o un archivo propio con estructura compatible.
2. Pulsar **Procesar transacciones**.
3. Consultar total procesado, válidos, inválidos y porcentajes.
4. Explorar válidos mediante filtros por estado, moneda, fuente y búsqueda de ID.
5. Revisar inválidos, motivos y JSON original en su pestaña.
6. Consultar gráficos y totales monetarios separados por moneda.
7. Descargar las transacciones válidas visibles como CSV.

## 13. Pruebas y validación

Ejecutar:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

**Resultados informados durante el desarrollo:**

| Etapa | Pruebas reportadas |
|---|---:|
| Lógica inicial | 12 |
| Correcciones de reglas | 19 |
| Interfaz Tkinter | 29 |
| Versión web optimizada | 36 |

Los conteos anteriores proceden de los informes de Codex compartidos durante el desarrollo. **Antes de entregar, ejecutar nuevamente la suite y registrar el resultado final.**

**Pruebas manuales realizadas:** carga del archivo mixto, visualización de 8 registros (5 válidos y 3 inválidos), filtros combinados, búsqueda de identificador, revisión de inválidos, visualización de métricas y apertura del CSV exportado en Excel. Se comprobó también el mensaje de error al intentar procesar un JSON vacío.

## 14. Uso de inteligencia artificial y conclusiones

Se utilizó Codex como apoyo para generar código, proponer implementaciones, integrar interfaces, elaborar pruebas y corregir problemas técnicos.Se definió el esquema y las reglas de normalización, se resolvieron las ambigüedades consultadas por la IA, se pidió correcciones de casos límite y se decidió migrar de Tkinter a Streamlit tras evaluar la interfaz.

El desarrollo por etapas permitió mantener la lógica de negocio separada de la interfaz, revisar los resultados y documentar las decisiones. El sistema final facilita explorar transacciones de varias fuentes sin mezclar monedas y permite consultar las causas de rechazo de los registros inválidos.
