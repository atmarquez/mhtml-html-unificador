#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# unificador_mhtml.py
#
# Unificador de documentos MHTML en un único HTML autocontenido.
#
# Author: Naidel
# Email: atmarquez@gmail.com
# Donate: https://paypal.me/atmarquez  # con PayPal
#
# Version: 1.0.1
# Copyright (C) 2026 Antonio Teodomiro Márquez Muñoz (Naidel)
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pathlib import Path
from email import policy
from email.parser import BytesParser
from datetime import datetime
import base64
import re
import mimetypes
import argparse
import sys


from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError

# =============================================================================
# METADATA
# =============================================================================

__author__ = "Antonio Teodomiro Márquez Muñoz (Naidel)"
__email__ = "atmarquez@gmail.com"
__version__ = "1.1.0"
__license__ = "GPL-3.0-or-later"
__donate__ = "https://paypal.me/atmarquez"

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================

# Extensiones de imagen soportadas para incrustación directa
IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
HTML_EXTS = {".html", ".htm", ".xhtml"}
MHTML_EXTS = {".mhtml"}

# =============================================================================
# ARGUMENTOS DE LÍNEA DE COMANDOS
# =============================================================================

parser = argparse.ArgumentParser(
    prog="unificador_mhtml.py",
    description=(
        "Unificador de documentos HTML, MHTML e imágenes en un único "
        "archivo HTML autocontenido.\n\n"
        "El programa recorre el directorio actual y:\n"
        "  • Une ficheros HTML, HTM, XHTML y MHTML\n"
        "  • Incrusta imágenes locales y remotas como Base64\n"
        "  • Evita duplicados y auto-inclusión del HTML generado\n"
        "  • Genera un único HTML listo para navegación, impresión o PDF"
    ),
    epilog=(
        "Ejemplos de uso:\n"
        "  python unificador_mhtml.py\n"
        "  python unificador_mhtml.py -o libro.html -t \"Manual ISACA CRISC\"\n"
        "  python unificador_mhtml.py --no-filenames\n"
        "  python unificador_mhtml.py --version\n\n"
        "Autor: Antonio Teodomiro Márquez Muñoz (Naidel)\n"
        "Donaciones: https://paypal.me/atmarquez"
    ),
    formatter_class=argparse.RawTextHelpFormatter
)

parser.add_argument(
    "-o", "--output",
    default="unido.html",
    help='Nombre del fichero HTML de salida (por defecto: unido.html)'
)

parser.add_argument(
    "-t", "--title",
    default="Manual unificado",
    help='Título principal del documento (por defecto: "Manual unificado")'
)

parser.add_argument(
    "--no-filenames",
    action="store_true",
    help="No mostrar el nombre del fichero antes de cada parte unificada"
)

parser.add_argument(
    "-V", "--version",
    action="store_true",
    help="Mostrar información del programa y salir"
)

args = parser.parse_args()

if args.version:
    print(
        "unificador_mhtml.py\n"
        f"  Versión:   {__version__}\n"
        f"  Autor:     {__author__}\n"
        f"  Email:     {__email__}\n"
        f"  Licencia:  {__license__}\n"
        f"  Donar:     {__donate__}"
    )
    sys.exit(0)

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def es_html_generado_por_unificador(path):
    """
    Detecta si un HTML ha sido generado por unificador_mhtml.py.
    """
    try:
        texto = path.read_text(encoding="utf-8", errors="ignore")
        if (
            "GENERATED-BY: unificador_mhtml.py" in texto
            or 'name="generator" content="unificador_mhtml.py"' in texto
        ):
            return True
    except Exception:
        pass
    return False

def incrustar_imagenes_externas(html, base_path):
    """
    Descarga o lee imágenes referenciadas por URL o ruta local en el HTML
    y las convierte en data URLs embebidas.
    """

    def reemplazo(match):
        prefijo = match.group(1)
        comilla = match.group(2)
        url = match.group(3).strip()

        # Ignorar data URLs y CID
        if url.startswith(("data:", "cid:")):
            return match.group(0)

        try:
            # --- IMÁGENES REMOTAS ---
            if url.startswith(("http://", "https://")):
                from urllib.request import urlopen
                with urlopen(url) as resp:
                    data = resp.read()
                    mime = resp.headers.get_content_type()

            # --- FILE:// ---
            elif url.startswith("file://"):
                ruta = Path(url[7:])
                data = ruta.read_bytes()
                mime, _ = mimetypes.guess_type(ruta)

            # --- RUTAS LOCALES RELATIVAS / ABSOLUTAS ---
            else:
                ruta = (base_path.parent / url).resolve()
                data = ruta.read_bytes()
                mime, _ = mimetypes.guess_type(ruta)

            if not data or not mime or not mime.startswith("image/"):
                raise ValueError("No es una imagen válida")

            b64 = base64.b64encode(data).decode("ascii")
            return f'{prefijo}{comilla}data:{mime};base64,{b64}{comilla}'

        except Exception as e:
            print(f"⚠️  No se pudo incrustar imagen: {url} ({e})")
            return match.group(0)

    return re.sub(
        r'(?i)(<img[^>]+src=)(["\'])([^"\']+)\2',
        reemplazo,
        html
    )
    
def extraer_recursos(msg):
    """
    Extrae imágenes embebidas desde un mensaje MHTML y las convierte en data URL.

    Recorre todas las partes MIME del mensaje y detecta imágenes con Content-ID
    (CID). Dichas imágenes se transforman en URLs base64 para que el HTML final
    sea completamente autocontenido.

    Args:
        msg (email.message.EmailMessage): Mensaje MHTML ya parseado.

    Returns:
        dict[str, str]: Mapa { "cid:xxxx" -> "data:image/...;base64,..." }
    """
    recursos = {}

    for part in msg.walk():
        # Ignorar contenedores multipart
        if part.is_multipart():
            continue

        content_id = part.get("Content-ID")
        content_type = part.get_content_type()

        # Solo imágenes con Content-ID
        if content_id and content_type.startswith("image/"):
            data = part.get_payload(decode=True)
            if not data:
                continue

            # Eliminar <>
            cid_limpio = content_id.strip("<>")
            b64 = base64.b64encode(data).decode("ascii")

            recursos[f"cid:{cid_limpio}"] = (
                f"data:{content_type};base64,{b64}"
            )

    return recursos


def extraer_css(msg):
    """
    Extrae todas las hojas de estilo CSS del MHTML y las devuelve como <style>.

    Args:
        msg (email.message.EmailMessage): Mensaje MHTML parseado.

    Returns:
        str: CSS combinado envuelto en etiquetas <style>.
    """
    estilos = []

    for part in msg.walk():
        if part.is_multipart():
            continue

        if part.get_content_type() == "text/css":
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            css = payload.decode(charset, errors="replace")

            estilos.append(f"<style>\n{css}\n</style>")

    return "\n".join(estilos)


def es_html(part):
    """
    Determina si una parte MIME contiene HTML.

    La detección se basa tanto en el Content-Type como en Content-Location
    (útil para MHTML imperfectos).

    Args:
        part (email.message.EmailMessage): Parte MIME a evaluar.

    Returns:
        bool: True si la parte parece HTML.
    """
    content_type = part.get_content_type().lower()
    content_location = (part.get("Content-Location") or "").lower()

    return (
        "html" in content_type
        or content_location.endswith(".html")
        or content_location.endswith(".htm")
    )


def limpiar_html(html):
    """
    Elimina etiquetas estructurales externas (<html>, <head>, <body>).

    Esto permite incrustar el HTML dentro de un documento mayor sin
    duplicar estructura.

    Args:
        html (str): Código HTML original.

    Returns:
        str: HTML limpio y embebible.
    """
    html = re.sub(r"(?is)<\s*(html|head|body)[^>]*>", "", html)
    html = re.sub(r"(?is)</\s*(html|head|body)\s*>", "", html)
    return html


def eliminar_base(html):
    """
    Elimina cualquier etiqueta <base> para evitar enlaces relativos incorrectos.

    Args:
        html (str): HTML original.

    Returns:
        str: HTML sin etiqueta <base>.
    """
    return re.sub(r"(?is)<\s*base\b[^>]*>", "", html)


def imagen_a_html(path):
    """
    Convierte una imagen local en HTML con imagen base64 embebida.

    Args:
        path (pathlib.Path): Ruta a la imagen.

    Returns:
        str: HTML <figure> con <img> embebido, o cadena vacía si no es soportada.
    """
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }

    mime = mime_map.get(path.suffix.lower())
    if not mime:
        return ""

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")

    return f"""
    <figure style="text-align:center; margin:3rem 0;">
        <img src="data:{mime};base64,{b64}">
    </figure>
    """


def prefijar_ids(html, prefijo, anchor_map):
    """
    Prefija todos los atributos id y name para evitar colisiones entre documentos.

    Ejemplo:
        id="intro" -> id="capitulo__intro"

    Además, guarda un mapa de anclas original -> nueva para reescribir enlaces.

    Args:
        html (str): HTML original.
        prefijo (str): Prefijo único (normalmente el nombre del archivo).
        anchor_map (dict): Diccionario compartido de anclas.

    Returns:
        str: HTML con IDs/names modificados.
    """
    def reemplazo(match):
        atributo = match.group(1)
        original = match.group(3)
        nuevo = f"{prefijo}__{original}"

        anchor_map.setdefault(original, nuevo)
        return f'{atributo}="{nuevo}"'

    return re.sub(
        r'\b(id|name)\s*=\s*(["\'])(.*?)\2',
        reemplazo,
        html,
        flags=re.I
    )


# =============================================================================
# PASADA 1: LECTURA Y EXTRACCIÓN
# =============================================================================

archivos = sorted(
    (
        p for p in Path(".").iterdir()
        if p.suffix.lower() in IMG_EXTS
        or p.suffix.lower() in HTML_EXTS
        or p.suffix.lower() in MHTML_EXTS
    ),
    key=lambda p: p.name.lower()
)

capitulos = []
anchor_map = {}

print("Extrayendo documentos, imágenes, CSS y anclas...")

for archivo in archivos:

    sufijo = archivo.suffix.lower()

    # -------------------------------------------------
    # IMÁGENES SUELTAS
    # -------------------------------------------------
    if sufijo in IMG_EXTS:
        capitulos.append((archivo.stem, imagen_a_html(archivo)))
        continue

    # -------------------------------------------------
    # HTML / HTM / XHTML
    # -------------------------------------------------
    if sufijo in HTML_EXTS:

        if es_html_generado_por_unificador(archivo):
            print(
                f"⏭️ {archivo.name} no se agregó: "
                "HTML generado previamente por unificador_mhtml.py"
            )
            continue

        print(f"Procesando HTML: {archivo.name}")

        html = archivo.read_text(encoding="utf-8", errors="replace")

        html = limpiar_html(html)
        html = eliminar_base(html)
        html = incrustar_imagenes_externas(html, archivo)
        html = prefijar_ids(html, archivo.stem, anchor_map)

        capitulos.append((archivo.stem, html))
        continue

    # -------------------------------------------------
    # MHTML
    # -------------------------------------------------
    if sufijo in MHTML_EXTS:
        print(f"Procesando MHTML: {archivo.name}")

        with archivo.open("rb") as fd:
            msg = BytesParser(policy=policy.default).parse(fd)

        recursos = extraer_recursos(msg)
        css_embebido = extraer_css(msg)
        html_final = ""

        for part in msg.walk():
            if part.is_multipart() or not es_html(part):
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            html = payload.decode(charset, errors="replace")

            # Sustituir CID por data URLs
            for cid, data in recursos.items():
                html = html.replace(cid, data)

            html = limpiar_html(html)
            html = eliminar_base(html)
            html = incrustar_imagenes_externas(html, archivo)
            html = prefijar_ids(html, archivo.stem, anchor_map)

            html_final = css_embebido + "\n" + html
            break

        capitulos.append((archivo.stem, html_final))


# =============================================================================
# PASADA 2: REESCRITURA DE ENLACES
# =============================================================================

def reescribir_links(html):
    """
    Reescribe enlaces internos (#ancla) usando el mapa de IDs prefijados.

    Args:
        html (str): HTML original.

    Returns:
        str: HTML con enlaces internos corregidos.
    """
    def reemplazo(match):
        pref, comilla, href = match.groups()
        parsed = urlparse(href)

        if not parsed.fragment:
            return match.group(0)

        fragmento = parsed.fragment

        if fragmento in anchor_map:
            return f'{pref}{comilla}#{anchor_map[fragmento]}{comilla}'

        if ":" in fragmento:
            _, derecha = fragmento.split(":", 1)
            if derecha in anchor_map:
                return f'{pref}{comilla}#{anchor_map[derecha]}{comilla}'

        return match.group(0)

    return re.sub(
        r'(?i)(href\s*=\s*)(["\'])([^"\']+)\2',
        reemplazo,
        html
    )


# =============================================================================
# GENERACIÓN DEL HTML FINAL
# =============================================================================

with open(args.output, "w", encoding="utf-8") as salida:
    fecha = datetime.now().isoformat(timespec="seconds")
    salida.write(
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<!-- GENERATED-BY: unificador_mhtml.py -->\n"
        f"<meta name=\"generator\" content=\"unificador_mhtml.py\">\n"
        f"<meta name=\"generator-version\" content=\"{__version__}\">\n"
        f"<meta name=\"generator-author\" content=\"{__author__}\">\n"
        f"<meta name=\"generator-email\" content=\"{__email__}\">\n"
        f"<meta name=\"generator-donate\" content=\"{__donate__}\">\n"
        f"<meta name=\"generator-date\" content=\"{fecha}\">\n"
        f"<title>{args.title}</title>\n"
        "<style>\n"
        "/* ================================ */\n"
        "/*  ESTILOS DE VISUALIZACIÓN WEB    */\n"
        "/* ================================ */\n"
        "\n"
        "@media screen {\n"
        "  body {\n"
        "    max-width: 900px;\n"
        "    margin: auto;\n"
        "  }\n"
        "}\n"
        "\n"
        "/* Título principal centrado */\n"
        "h1 {\n"
        "  text-align: center;\n"
        "  margin-top: 2rem;\n"
        "  margin-bottom: 3rem;\n"
        "}\n"      
        "\n"
        "section.capitulo {\n"
        "  margin-top: 4rem;\n"
        "  padding-top: 2rem;\n"
        "  border-top: 1px solid #ddd;\n"
        "}\n"
        "\n"
        "section.capitulo:first-of-type {\n"
        "  margin-top: 2rem;\n"
        "  padding-top: 0;\n"
        "  border-top: none;\n"
        "}\n"
        "\n"
        "section.capitulo > h2 {\n"
        "  margin-top: 0;\n"
        "  margin-bottom: 1.5rem;\n"    
        "}\n"
        "/* ================================ */\n"
        "/*  ESTILOS DE IMPRESIÓN            */\n"
        "/* ================================ */\n"
        "\n"
        "@media print {\n"
        "\n"
        "body {\n"
        "    margin: 0;\n"
        "}\n"       
        "\n"
        "  /* Cada capítulo comienza en página nueva */\n"
        "  section.capitulo {\n"
        "    break-before: page;\n"
        "    page-break-before: always;\n"
        "    max-width: 100%;\n"
        "  }\n"
        "\n"
        "  /* El primer capítulo no fuerza página nueva */\n"
        "  section.capitulo:first-of-type {\n"
        "    break-before: auto;\n"
        "    page-break-before: auto;\n"
        "  }\n"
        "\n"
        "  /* Evitar que títulos queden al final de página */\n"
        "  h1, h2 {\n"
        "    break-after: avoid;\n"
        "    page-break-after: avoid;\n"
        "  }\n"
        "\n"
        "  /* Evitar saltos dentro de figuras (imágenes, gráficos) */\n"
        "  figure {\n"
        "    break-inside: avoid;\n"
        "    page-break-inside: avoid;\n"
        "  }\n"
        "}\n"
        "</style>\n"
        "</head>\n<body>\n"
        f"<h1>{args.title}</h1>\n"
    )

    for titulo, html in capitulos:
        html = reescribir_links(html)
        
        salida.write(f'<section class="capitulo" id="{titulo}">')
        if not args.no_filenames:
            salida.write(f'<h2>{titulo}</h2>')
        salida.write(f'{html}</section>\n')

    salida.write("</body></html>")

print(f"✅ {args.output} creado correctamente")
