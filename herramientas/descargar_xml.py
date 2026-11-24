#!/usr/bin/env python3
"""
Descarga desde SIFEN (SET Paraguay) el XML de cada CDC de una lista, usando la
firma digital .p12 de la empresa. Los XML quedan en una carpeta lista para
arrastrar al Generador de KuDE.

Uso:
    python descargar_xml.py lista_cdc.txt --p12 firma.p12
    python descargar_xml.py lista_cdc.txt --p12 firma.p12 --salida xml_descargados

La lista puede venir copiada de Excel: se aceptan líneas con apóstrofo inicial
('0580...), espacios o guiones. La contraseña del .p12 se pide al ejecutar y no
se guarda en ningún lado.

Requisitos: Python 3.9 o superior y el paquete "cryptography"
    (pip install cryptography)
"""
import argparse
import csv
import getpass
import html
import os
import re
import secrets
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

URLS = {
    "produccion": "https://sifen.set.gov.py/de/ws/consultas/consulta.wsdl",
    "test": "https://sifen-test.set.gov.py/de/ws/consultas/consulta.wsdl",
}
TIPO_DE = {"01": "Factura", "04": "Autofactura", "05": "Nota de crédito",
           "06": "Nota de débito", "07": "Nota de remisión"}
PAUSA_SEG = 1.0      # entre consultas, para no saturar el servicio de la SET
REINTENTOS = 3


# ---------- lista de CDC ----------
def dv_mod11(digitos):
    """Dígito verificador módulo 11 (Manual Técnico SIFEN)."""
    total, k = 0, 2
    for c in reversed(digitos):
        total += int(c) * k
        k = 2 if k == 11 else k + 1
    r = total % 11
    return 11 - r if r > 1 else 0


def leer_lista(ruta):
    """Devuelve (cdcs_validos, errores). Ignora líneas vacías y repetidos."""
    validos, errores, vistos = [], [], set()
    texto = Path(ruta).read_text(encoding="utf-8-sig", errors="replace")
    for n, linea in enumerate(texto.splitlines(), 1):
        if not linea.strip():
            continue
        cdc = re.sub(r"\D", "", linea)
        if len(cdc) != 44:
            errores.append((n, linea.strip(), f"tiene {len(cdc)} dígitos, deben ser 44"))
        elif dv_mod11(cdc[:43]) != int(cdc[43]):
            errores.append((n, linea.strip(), "el dígito verificador no corresponde"))
        elif cdc not in vistos:
            vistos.add(cdc)
            validos.append(cdc)
    return validos, errores


def descripcion(cdc):
    return f"{TIPO_DE.get(cdc[:2], 'Documento')} {cdc[11:14]}-{cdc[14:17]}-{cdc[17:24]}"


# ---------- certificado ----------
def contexto_tls(ruta_p12, clave, cafile=None):
    """Arma la conexión TLS con el certificado del .p12.

    Python solo acepta el certificado desde archivos, así que se escribe en una
    carpeta temporal con la clave privada cifrada con una contraseña aleatoria,
    y se borra apenas se carga.
    """
    from cryptography.hazmat.primitives.serialization import (
        BestAvailableEncryption, Encoding, PrivateFormat, pkcs12)

    clave_privada, cert, extras = pkcs12.load_key_and_certificates(
        Path(ruta_p12).read_bytes(), clave.encode())
    if clave_privada is None or cert is None:
        raise ValueError("el .p12 no contiene un certificado con su clave privada")

    ctx = ssl.create_default_context(cafile=cafile)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    temporal = secrets.token_urlsafe(24)
    with tempfile.TemporaryDirectory() as carpeta:
        crt, key = os.path.join(carpeta, "c.pem"), os.path.join(carpeta, "k.pem")
        with open(crt, "wb") as f:
            f.write(cert.public_bytes(Encoding.PEM))
            for extra in extras or []:
                f.write(extra.public_bytes(Encoding.PEM))
        with open(key, "wb") as f:
            f.write(clave_privada.private_bytes(Encoding.PEM, PrivateFormat.PKCS8,
                                                BestAvailableEncryption(temporal.encode())))
        ctx.load_cert_chain(crt, key, password=temporal)
    return ctx, cert.subject.rfc4514_string()


# ---------- consulta a SIFEN ----------
def consultar(cdc, n, url, ctx):
    """Consulta un CDC. Devuelve (codigo, mensaje, xml_o_None)."""
    cuerpo = (
        '<env:Envelope xmlns:env="http://www.w3.org/2003/05/soap-envelope">'
        "<env:Header/><env:Body>"
        '<rEnviConsDeRequest xmlns="http://ekuatia.set.gov.py/sifen/xsd">'
        f"<dId>{n}</dId><dCDC>{cdc}</dCDC>"
        "</rEnviConsDeRequest></env:Body></env:Envelope>"
    ).encode("utf-8")
    pedido = urllib.request.Request(url, data=cuerpo, method="POST", headers={
        "Content-Type": "application/xml; charset=utf-8",
        "User-Agent": "GeneradorKuDE/2.4",
    })
    with urllib.request.urlopen(pedido, context=ctx, timeout=60) as r:
        respuesta = r.read().decode("utf-8", errors="replace")

    codigo = _campo(respuesta, "dCodRes")
    mensaje = html.unescape(_campo(respuesta, "dMsgRes"))
    contenido = re.search(r"<(?:\w+:)?xContenDE[^>]*>(.*?)</(?:\w+:)?xContenDE>", respuesta, re.S)
    xml = None
    if contenido:
        interno = contenido.group(1).strip()
        if interno.startswith("<![CDATA["):
            interno = interno[9:-3]
        elif "&lt;" in interno[:200]:
            interno = html.unescape(interno)
        rde = re.search(r"<((?:\w+:)?)rDE[\s>].*</\1rDE>", interno, re.S)   # con o sin prefijo (ns2:rDE)
        if rde:
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + rde.group(0)
    return codigo, mensaje, xml


def _campo(texto, etiqueta):
    m = re.search(rf"<(?:\w+:)?{etiqueta}>([^<]*)<", texto)
    return m.group(1).strip() if m else ""


# ---------- programa ----------
def main():
    ap = argparse.ArgumentParser(description="Descarga de SIFEN los XML de una lista de CDC.")
    ap.add_argument("lista", help="archivo de texto con un CDC por línea")
    ap.add_argument("--p12", required=True, help="firma digital de la empresa (.p12 o .pfx)")
    ap.add_argument("--salida", default="xml_descargados", help="carpeta donde guardar los XML")
    ap.add_argument("--ambiente", choices=URLS, default="produccion")
    ap.add_argument("--url", help=argparse.SUPPRESS)       # solo para pruebas
    ap.add_argument("--cafile", help=argparse.SUPPRESS)    # solo para pruebas
    args = ap.parse_args()

    cdcs, errores = leer_lista(args.lista)
    for n, linea, motivo in errores:
        print(f"  Línea {n} ignorada ({motivo}): {linea}")
    if not cdcs:
        sys.exit("No hay CDC válidos en la lista.")

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    pendientes = [c for c in cdcs if not (salida / f"{c}.xml").exists()]
    print(f"{len(cdcs)} CDC válidos; {len(cdcs) - len(pendientes)} ya estaban descargados.")

    try:
        ctx, titular = contexto_tls(args.p12, getpass.getpass("Contraseña del .p12: "), args.cafile)
    except Exception as e:
        sys.exit(f"No se pudo abrir el certificado: {e}")
    print(f"Certificado: {titular}\n")

    url = args.url or URLS[args.ambiente]
    filas, bajados = [], 0
    try:
        for i, cdc in enumerate(pendientes, 1):
            print(f"[{i}/{len(pendientes)}] {descripcion(cdc)} … ", end="", flush=True)
            codigo = mensaje = ""
            for intento in range(1, REINTENTOS + 1):
                try:
                    codigo, mensaje, xml = consultar(cdc, i, url, ctx)
                    break
                except urllib.error.URLError as e:
                    if isinstance(e.reason, ssl.SSLError):   # problema de certificado: reintentar no sirve
                        print()
                        raise SystemExit(f"SIFEN rechazó la conexión segura: {e.reason}\n"
                                         "Revisá que el .p12 sea la firma vigente de la empresa.")
                    codigo, mensaje, xml = "ERROR", f"sin respuesta de SIFEN: {e.reason}", None
                except (TimeoutError, ConnectionError) as e:
                    codigo, mensaje, xml = "ERROR", f"sin respuesta de SIFEN: {e}", None
                time.sleep(PAUSA_SEG * 3 * intento)
            if xml:
                (salida / f"{cdc}.xml").write_text(xml, encoding="utf-8")
                bajados += 1
                print("descargado")
            else:
                print(f"NO descargado ({codigo} {mensaje})".strip())
            filas.append([cdc, descripcion(cdc), "descargado" if xml else "no descargado", codigo, mensaje])
            time.sleep(PAUSA_SEG)
    finally:   # el resumen se guarda aunque se corte a mitad de camino (Ctrl+C o error)
        resumen = salida / "resumen.csv"
        with open(resumen, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel lo abre bien
            w = csv.writer(f, delimiter=";")
            w.writerow(["CDC", "Documento", "Estado", "Código SIFEN", "Mensaje"])
            w.writerows(filas)
        print(f"\n{bajados} de {len(pendientes)} descargados en «{salida}». Detalle en {resumen.name}.")


if __name__ == "__main__":
    main()
