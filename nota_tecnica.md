# Nota técnica — Normalización y Exploración de Transacciones Multifuente

## Diseño y arquitectura

Desarrollé una aplicación en **Python 3.14** para procesar transacciones JSON de tres fuentes con nombres de campos diferentes. Definí un esquema común con los campos `id`, `amount`, `currency`, `timestamp`, `status` y `source`. Organicé la solución en módulos independientes: `normalizador.py` para transformar registros, `validador.py` para comprobar reglas, `metricas.py` para calcular resultados y `main.py`/`vista.py` para la interfaz web en **Streamlit**. Centralicé los mapeos de fuentes, estados, monedas y fechas en `configuracion/reglas.json`.

## Decisiones de normalización y validación

Definí que los identificadores numéricos se conviertan a texto y que los vacíos se rechacen. Los montos enteros representan unidades monetarias; utilizo `Decimal` para evitar errores de precisión, permito el valor cero y rechazo montos negativos o no válidos. Admito diez monedas (USD, EUR, GBP, JPY, MXN, CAD, BRL, CHF, CNY y KRW), sin convertir ni sumar monedas distintas. Los símbolos ambiguos (`$` y `¥`) requieren un código de moneda explícito y compatible; los símbolos contradictorios se rechazan. Normalizo los estados a `SUCCESS`, `FAILED` y `PENDING`, y las fechas a ISO 8601 sin inventar zonas horarias. Conservo el primer registro válido de cada identificador y marco como inválidos los duplicados posteriores. Los registros rechazados mantienen sus datos originales y motivos de rechazo.

La identificación de la fuente es independiente de la validación: un registro incompleto puede conservar su fuente si es reconocible; si resulta ambiguo, se clasifica como `UNKNOWN`. Los conteos por fuente consideran todos los registros; los conteos por estado y los importes por moneda consideran solo los válidos.

## Uso de inteligencia artificial y ajustes realizados

Utilicé **Codex** como apoyo para implementar el código, estructurar módulos, desarrollar pruebas y construir la interfaz. **Las reglas de negocio y los criterios de validez fueron decisiones mías**, no de la IA. Tras revisar los primeros resultados, solicité corregir la identificación de fuentes incompletas, impedir combinaciones incompatibles como `¥` con `USD` y añadir porcentajes de válidos e inválidos, incluso cuando no hay registros. Inicialmente desarrollé una interfaz con Tkinter, pero decidí sustituirla por Streamlit para facilitar la exploración de datos. Posteriormente pedí corregir el encabezado y mejorar la carga de la interfaz sin alterar la lógica.

## Verificación

Durante el desarrollo, Codex reportó una progresión de **12, 19, 29 y 36 pruebas automatizadas**. También comprobé manualmente un archivo de ocho transacciones (cinco válidas y tres inválidas), los filtros combinados, la búsqueda por ID, los motivos de rechazo, las métricas, la exportación CSV y el manejo de un archivo vacío. El conjunto de pruebas puede ejecutarse con `python -m unittest discover -s pruebas -v`.
