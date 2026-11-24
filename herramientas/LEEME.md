# Descargar XML de SIFEN por lista de CDC

`descargar_xml.py` consulta en SIFEN (SET) cada CDC de una lista, con la firma digital `.p12` de la empresa, y guarda el XML de cada documento en una carpeta. Después se arrastra esa carpeta al Generador de KuDE.

## Preparación (una sola vez)

1. Instalá Python desde <https://www.python.org/downloads/>. Durante la instalación marcá **"Add python.exe to PATH"**.
2. Abrí "Símbolo del sistema" y ejecutá:
   ```
   pip install cryptography
   ```

## Uso

1. Poné en una misma carpeta:
   - `descargar_xml.py` y `descargar.bat`
   - tu firma digital, con el nombre `firma.p12`
   - `lista_cdc.txt`, con un CDC por línea. Se puede pegar directo desde Excel, con o sin el apóstrofo inicial:
     ```
     '05800034007001002044211422026100511047909773
     05800034007001002044618922026102311572691948
     ```
2. Hacé doble clic en `descargar.bat` y escribí la contraseña del `.p12` cuando la pida (no se ve mientras escribís).
3. Los XML quedan en `xml_descargados`, con el CDC como nombre de archivo, y el detalle en `xml_descargados/resumen.csv` (se abre con Excel).
4. Arrastrá los XML al Generador de KuDE.

Si volvés a ejecutarlo, solo consulta los CDC que todavía no se descargaron.

## Qué hace con cada CDC

- Verifica que tenga 44 dígitos y un dígito verificador correcto; si no, avisa en qué línea está el problema.
- Lo consulta en SIFEN con un segundo de pausa entre consultas, para no saturar el servicio.
- Si SIFEN devuelve el documento, guarda el XML tal como viene (incluida la firma del emisor).
- Si no, anota el código y el mensaje de SIFEN en el resumen.

## Seguridad

- La contraseña del `.p12` se pide cada vez y **no se guarda**.
- La clave privada se carga en memoria. Python necesita leerla de un archivo, así que se escribe por un instante en una carpeta temporal, **cifrada con una contraseña aleatoria**, y se borra enseguida.
- El programa solo se conecta a `sifen.set.gov.py` (o `sifen-test.set.gov.py` con `--ambiente test`), verificando su certificado.
- **No subas** tu `firma.p12`, tu lista de CDC ni los XML descargados a GitHub ni los compartas.

## Pendiente de confirmar

El programa se probó contra un servidor que imita las respuestas de SIFEN, no contra SIFEN real. En la primera ejecución real conviene revisar `resumen.csv`:

- Si todo dice **descargado**, funciona.
- Si SIFEN responde que el documento no existe o que no tenés permiso para documentos que **recibiste**, puede ser que el servicio de consulta solo entregue el XML completo al emisor. En ese caso, pasá el `resumen.csv` para revisarlo.
