# GigiMET

GigiMET analiza reportes meteorologicos aeronauticos METAR/SPECI, calcula variables clave, clasifica categorias de vuelo y vincula cada estacion con un catalogo local de aeropuertos del Peru.

El proyecto mantiene dos interfaces:

- Version web local y publicable en Streamlit: `app.py`
- Version de escritorio PySide6: `project/main.py`

## Ejecutar la version web

Instala dependencias:

```bash
pip install -r requirements.txt
```

Ejecuta Streamlit desde la raiz del repositorio:

```bash
streamlit run app.py
```

En una tablet Android conectada a la misma red WiFi, abre la URL que muestra la app en la barra lateral, por ejemplo:

```text
http://192.168.1.50:8501
```

## Publicar en Streamlit Community Cloud

1. Sube este repositorio a GitHub.
2. En Streamlit Community Cloud selecciona el repositorio.
3. Usa `app.py` como Main file path.
4. Streamlit instalara las dependencias desde `requirements.txt`.

## Funcionalidades principales

- Carga de uno o varios archivos TXT con reportes METAR/SPECI.
- Seleccion de ano y mes para construir fechas completas.
- Eliminacion de duplicados exactos.
- Tabla filtrable por texto, tipo de reporte y categoria de vuelo.
- Resumen ejecutivo con calidad de datos, periodo, tipos, viento predominante y categorias VFR/MVFR/IFR/LIFR.
- Ficha del aeropuerto detectado desde `project/resources/airports_peru.json`.
- Graficos de serie individual, comparacion de variables y dona de categorias de vuelo.
- Descarga de graficos en PNG, PDF y SVG.
- Exportacion de datos filtrados a CSV y Excel.
- Generacion de reporte PDF tecnico con figuras seleccionadas.

## Estructura importante

```text
app.py
requirements.txt
README.md
.streamlit/config.toml
project/
  main.py
  parser/
  graphics/
  database/
  utils/
  ui/
  resources/
    airports_peru.json
```

## Version de escritorio

La version PySide6 original no se elimina. Para ejecutarla:

```bash
python project/main.py
```

## Crear un ejecutable descargable para Windows

Para generar un solo archivo ejecutable de la version de escritorio:

```powershell
.\build_windows_exe.ps1
```

El archivo final queda en:

```text
dist\GigiMET.exe
```

Notas importantes:

- Ese `.exe` funciona en Windows. Para macOS o Linux se debe construir el ejecutable en cada sistema operativo.
- Android e iOS no ejecutan aplicaciones PySide6 de escritorio como un `.exe`.
- Si necesitas usar GigiMET desde cualquier dispositivo con navegador, publica la version Streamlit (`app.py`) y abre la URL desde telefono, tablet o PC.

## Archivo de prueba

Puedes usar `project/sample_metar.txt` para probar el flujo completo.
