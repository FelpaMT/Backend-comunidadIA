from django.conf import settings
from django.utils import timezone
from pathlib import Path
import uuid
import nh3

PUBLICATION_HTML_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "dd", "del", "div",
    "dl", "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "hr",
    "i", "img", "li", "ol", "p", "pre", "s", "span", "strong", "sub", "sup",
    "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
}
PUBLICATION_HTML_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}


def sanitize_publication_html(content: str) -> str:
    return nh3.clean(
        content,
        tags=PUBLICATION_HTML_TAGS,
        attributes=PUBLICATION_HTML_ATTRIBUTES,
        clean_content_tags={"script", "style", "iframe", "object", "svg", "math"},
        url_schemes={"http", "https", "mailto"},
    )

def get_publication_html(content_url):

        # Convertir URL pública → ruta absoluta
        url_part = content_url.replace(settings.MEDIA_URL, "", 1)
        abs_path = Path(settings.MEDIA_ROOT) / url_part

        if abs_path.exists() and abs_path.is_file():
            content = abs_path.read_text(encoding="utf-8")
            safe_content = sanitize_publication_html(content)
            if safe_content != content:
                abs_path.write_text(safe_content, encoding="utf-8")
            return safe_content
        else:
            raise FileNotFoundError("No se encontró el contenido")

def save_publication_html(content: str) -> str:
    # Guarda el contenido como archivo .html dentro de ./media/publications/
    folder = Path(settings.MEDIA_ROOT) / "publications"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.html"
    path = folder / filename
    path.write_text(sanitize_publication_html(content), encoding="utf-8")
    # URL (sirviendo media en desarrollo con runserver)
    return f"{settings.MEDIA_URL}publications/{filename}"

def update_publication_html(content_url: str, content: str):
    try:
        if not content_url:
            return "content_url not provided"

        # 1. Convertir URL → ruta relativa del filesystem
        relative_path = content_url.replace(settings.MEDIA_URL, "", 1)

        # 2. Ruta absoluta
        abs_path = Path(settings.MEDIA_ROOT) / relative_path

        # 3. Asegurar existencia del directorio
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # 4. Escribir el nuevo contenido
        abs_path.write_text(sanitize_publication_html(content), encoding="utf-8")

        return "ok"

    except Exception as e:
        print("File update failed", e)
        return f"file update failed: {e}"
    
def delete_publication_html(content_url):
    if not content_url:
        return

    relative_path = content_url.replace(settings.MEDIA_URL, "", 1)

    abs_path = Path(settings.MEDIA_ROOT) / relative_path

    # 3. Borrar si existe
    try:
        if abs_path.exists() and abs_path.is_file():
            abs_path.unlink()
    except Exception:
        pass
