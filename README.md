# Generador de KuDE

Genera la representación impresa (KuDE) de facturas electrónicas de Paraguay a partir del XML descargado de **e-Kuatia** (SIFEN).

- Es un único archivo HTML: se abre con doble clic en cualquier navegador.
- Funciona **sin conexión**. Ningún dato sale de la computadora (la política de seguridad CSP bloquea toda conexión de red).
- Permite cargar varios XML a la vez, imprimirlos o descargar un PDF por factura (`Proveedor_número.pdf`).
- Controla la coherencia de cada XML: dígito verificador del CDC, CDC contra los datos del XML, QR de e-Kuatia y totales.

> Los controles **no verifican la firma digital**. Para confirmar la validez de una factura, consultá el CDC en <https://ekuatia.set.gov.py/consultas/>.

## Uso

1. Abrí `Generador_KuDE.html` (siempre es la última versión).
2. Arrastrá los XML o usá «Elegir archivos…».
3. Revisá los controles de integridad y presioná «Imprimir» o «Descargar PDF».

## Versiones

| Versión | Archivo | Cambios |
|---|---|---|
| 2.2 | [`versiones/Generador_KuDE_v2.2.html`](versiones/Generador_KuDE_v2.2.html) | Correcciones de seguridad y lista con scroll, buscador y filtro (ver abajo). |
| 2.1 | [`versiones/Generador_KuDE_v2.1.html`](versiones/Generador_KuDE_v2.1.html) | Versión inicial publicada en este repositorio. |

Cada versión también tiene su etiqueta de git (`v2.1`, `v2.2`).

### v2.2

**Seguridad y robustez**
- Un XML con total negativo ya no cuelga la página (recursión infinita en el monto en letras).
- La generación de PDF trabaja sobre cada factura y bloquea los botones mientras corre, para que el nombre del PDF siempre coincida con su contenido.
- Control del QR más estricto: dominio oficial, sin puerto ni credenciales y con la ruta `/consultas…`.
- La librería de QR se reemplazó por la versión oficial `qrcode-generator` 2.0.4 (la anterior tenía una línea modificada).
- Se quitaron funciones de prueba expuestas en `window` (`__lastPdf`, `__sheetToPdf`, `__printOnly`).
- Máximo 100 archivos por carga. Si una hoja falla, solo esa factura muestra el error.
- CSP ampliada con `frame-src`, `worker-src` y `manifest-src 'none'`.
- Monto en letras con redondeo correcto, nombres de PDF sin punto inicial y tolerancia de suma por moneda.
- La etiqueta «Controles OK» pasa a «Coherencia OK» y se avisa que la firma digital no se verifica.

**Interfaz**
- La lista de facturas tiene su propio scroll; la zona de carga queda siempre visible.
- Buscador por proveedor, número, CDC o archivo, y filtro «Todas / Con fallas / Sin fallas».
- Contador de facturas con fallas, factura seleccionada resaltada y botones más compactos.
- Las notas de ayuda pasan a un desplegable «Información».

## Librerías incluidas

Todas van embebidas en el HTML, idénticas a las publicadas en npm:

- [html2canvas](https://html2canvas.hertzen.com) 1.4.1 (MIT)
- [jsPDF](https://github.com/parallax/jsPDF) 4.2.1 (MIT)
- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 2.0.4 (MIT)

## Si se modifica el código

La CSP del archivo autoriza cada `<script>` por su hash SHA-256. Si se cambia cualquier script, hay que recalcular su hash y actualizar la etiqueta `Content-Security-Policy`; si no, el navegador no lo ejecuta.
