@echo off
rem Descarga de SIFEN los XML de los CDC de lista_cdc.txt usando firma.p12.
rem Este archivo, el programa (descargar_xml.exe o descargar_xml.py), lista_cdc.txt y firma.p12 van en la misma carpeta.
cd /d "%~dp0"
if exist descargar_xml.exe (
  descargar_xml.exe lista_cdc.txt --p12 firma.p12 --salida xml_descargados
) else (
  python descargar_xml.py lista_cdc.txt --p12 firma.p12 --salida xml_descargados
)
echo.
pause
