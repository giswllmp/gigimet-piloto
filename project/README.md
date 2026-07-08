# GigiMET

Aplicacion profesional de escritorio para analizar reportes METAR/SPECI y vincularlos con informacion aeroportuaria local mediante codigos OACI.

## Caracteristicas

### Interfaz
- Tema oscuro profesional.
- Navegacion lateral por secciones.
- Tablero principal con metricas de reportes, periodo, tipos METAR/SPECI y calidad.
- Panel de resumen ejecutivo con categorias de vuelo, promedios y viento predominante.
- Ficha contextual del aeropuerto detectado, alimentada desde `resources/airports_peru.json`.
- Tabla interactiva con ordenamiento.
- Filtros por texto, tipo de reporte y categoria de vuelo.
- Procesamiento en segundo plano para evitar bloqueos.
- Graficos integrados con Matplotlib, incluyendo series individuales, series combinadas, control de tamano, control de grosor, paletas de color, colores personalizados, exportacion cientifica en blanco y negro y dona de categorias de vuelo.
- Exportacion a CSV y Excel.

### Procesamiento METAR/SPECI
La aplicacion cuenta como registro meteorologico cada linea que empieza con `METAR` o `SPECI`.
Las lineas de encabezado, por ejemplo las que empiezan con `SA` o `SP`, se ignoran para el conteo de reportes.
Antes de procesar, el usuario debe indicar el ano y mes de los reportes. El sistema combina ese contexto con el dia y hora incluidos en cada METAR/SPECI para construir fechas completas en formato `AAAA-MM-DD HH:MM`.

La deteccion de duplicados conserva reportes con distinta fecha, hora o estacion aunque tengan las mismas condiciones meteorologicas. Solo se elimina un registro cuando el reporte parseado completo es identico, incluida la fecha y hora.

La aplicacion extrae automaticamente:

| Variable | Descripcion |
| --- | --- |
| report_type | Tipo de reporte, METAR o SPECI |
| datetime | Fecha y hora de observacion |
| station | Codigo de estacion OACI, por ejemplo SPQT |
| wind_dir | Direccion del viento en ° |
| wind_speed | Velocidad del viento en kt |
| gust | Rafagas en kt |
| visibility | Visibilidad en km |
| temperature | Temperatura en °C |
| dewpoint | Punto de rocio en °C |
| humidity | Humedad relativa calculada en % |
| pressure | Presion QNH en hPa |
| weather | Fenomenos meteorologicos |
| clouds | Capas de nubes |
| ceiling_ft | Techo en pies |
| flight_category | Categoria VFR, MVFR, IFR, LIFR o UNKNOWN |
| delta_TTd | Diferencia entre temperatura y punto de rocio en °C |

### Catalogo de aeropuertos
GigiMET carga automaticamente `resources/airports_peru.json` al iniciar y mantiene el catalogo en memoria durante la ejecucion. El archivo contiene aeropuertos y aerodromos del Peru indexados por codigo OACI.

La columna principal `Estacion` mantiene unicamente el codigo OACI del reporte, por ejemplo `SPQT`, `SPJC` o `SPZO`. El nombre oficial, IATA, ciudad, departamento, elevacion, pista y tipo se usan como informacion complementaria en la tarjeta del aeropuerto.

Si un codigo OACI no esta registrado, la aplicacion muestra `Aeropuerto no registrado` o `No disponible` sin detener el procesamiento.

El catalogo oficial usa objetos por codigo OACI:

```json
{
  "airports": {
    "SPQT": {
      "name": "Aeropuerto Internacional Coronel FAP Francisco Secada Vignetta",
      "icao": "SPQT",
      "iata": "IQT",
      "city": "Iquitos",
      "department": "Loreto",
      "elevation_ft": 306,
      "runway": "06/24",
      "type": "Internacional"
    }
  }
}
```

## Secciones de la Aplicacion

1. Inicio: informacion general, metricas, diagnostico de calidad y ficha aeroportuaria.
2. Importar: seleccion de archivos TXT o carpetas completas.
3. Procesar: seleccion de ano/mes, lectura y conversion de reportes METAR/SPECI.
4. Variables: tabla con datos extraidos, busqueda, filtros y ficha del aeropuerto detectado.
5. Graficos: series temporales por variable, comparacion de varias variables en una sola grafica, paletas, colores personalizados, tamano de figura, grosor de linea, dona de categorias de vuelo, exportacion cientifica en blanco y negro y guardado. Usa la vista filtrada si hay filtros activos.
6. Exportar: salida a CSV o Excel. Exporta la vista filtrada cuando corresponde.
7. Configuracion: informacion general del proyecto.

## Estructura del Proyecto

```text
project/
|-- main.py
|-- requirements.txt
|-- README.md
|-- MEJORAS_INTERFAZ.txt
|-- sample_metar.txt
|-- ui/
|   |-- mainwindow.py
|   |-- dialogs.py
|   |-- components/
|   |   |-- widgets.py
|   |   `-- table.py
|   `-- styles/
|       `-- colors.py
|-- parser/
|   |-- metar_parser.py
|   |-- calculations.py
|   `-- classification.py
|-- graphics/
|   |-- canvas.py
|   |-- plots.py
|   `-- timeseries.py
|-- database/
|   `-- export.py
|-- utils/
|   |-- airports.py
|   |-- helpers.py
|   `-- config.py
|-- resources/
|   |-- style.qss
|   |-- dark_theme.qss
|   `-- airports_peru.json
`-- tests/
    `-- test_parser.py
```

## Requisitos

- Python 3.12 o superior.
- pandas
- numpy
- matplotlib
- PySide6
- metar
- openpyxl
- reportlab

Instalacion de dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion

Desde la carpeta del proyecto:

```powershell
cd C:\PROGRAMACION\PRUEBA_02\project
..\.venv\Scripts\python.exe main.py
```

Tambien puedes usar:

```powershell
python main.py
```

si tu entorno global ya tiene las dependencias instaladas.

## Uso Rapido

1. Abre la aplicacion.
2. Ve a Importar.
3. Selecciona `sample_metar.txt` o una carpeta con archivos TXT.
4. Ve a Procesar y pulsa Procesar.
5. Revisa la tabla en Variables.
6. Filtra por texto, tipo de reporte o categoria de vuelo si necesitas analizar un subconjunto.
7. Genera graficos seleccionando una variable.
8. Exporta los resultados desde Exportar.

## Archivo de Prueba

El archivo `sample_metar.txt` incluye reportes de ejemplo. Sirve para probar el flujo completo sin buscar datos externos.

Ejemplo:

```text
METAR SPQT 061200Z 09015G25KT 8KM BKN020 OVC040 25/22 Q1013 NOSIG=
METAR SPQT 061300Z 08018G28KT 6KM -RA BKN015 OVC035 24/21 Q1012 NOSIG=
```

## Clasificacion de Vuelo

- VFR: visibilidad mayor o igual a 8 km y ceiling mayor o igual a 3000 ft.
- MVFR: visibilidad entre 5 y 8 km o ceiling entre 1000 y 3000 ft.
- IFR: visibilidad entre 1.6 y 5 km o ceiling entre 500 y 1000 ft.
- LIFR: visibilidad menor a 1.6 km o ceiling menor a 500 ft.

## Exportacion

Los archivos exportados se guardan por defecto en `output/`:

- `metar.csv`
- `metar.xlsx`

Los graficos pueden guardarse como PNG, PDF o SVG.

## Estado

Version: 1.0
Fecha de trabajo: 2026-07-08
Proyecto orientado a uso academico e investigacion.
