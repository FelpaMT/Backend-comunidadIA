import logging
import os
import re
from google import genai
from google.genai import types
from django.conf import settings
from .models import Publication

SYSTEM_INSTRUCTION = (
    "Eres un Tutor pedagógico experto en Inteligencia Artificial y educación. "
    "Tu tono debe ser empático, didáctico, claro y ético. Guías a educadores, docentes "
    "y profesionales a comprender, aplicar y reflexionar sobre la IA en el ámbito educativo. "
    "Responde siempre en español formateado en Markdown claro y estructurado."
)
logger = logging.getLogger(__name__)


def _build_pedagogical_fallback(message: str, pub_meta: dict | None = None) -> str:
    msg = (message or "").strip()
    if pub_meta:
        clean_body = re.sub(r"<[^>]+>", " ", pub_meta.get("content", "")).strip()
        excerpt = (clean_body[:260] + "...") if len(clean_body) > 260 else clean_body
        return (
            f"### Análisis Pedagógico: *{pub_meta.get('title')}*\n\n"
            f"**Contexto de la publicación:** {pub_meta.get('type')} en la categoría **{pub_meta.get('category')}** "
            f"(autor: `@{pub_meta.get('author')}`).\n\n"
            f"> {excerpt}\n\n"
            f"**Orientación didáctica sobre tu consulta (*\"{msg}\"*):**\n"
            f"1. **Aplicación en el aula:** Puedes articular los conceptos de esta publicación mediante actividades de aprendizaje basado en problemas (ABP) y verificación crítica de resultados generados por IA.\n"
            f"2. **Evaluación formativa:** Diseña rúbricas con criterios explícitos de autoría, trazabilidad del prompt y reflexión ética del estudiante.\n"
            f"3. **Siguiente paso sugerido:** Comparte en los comentarios de esta publicación cómo adaptarías esta estrategia a tu asignatura."
        )
    return (
        f"### Orientación del Tutor Pedagógico IA\n\n"
        f"Respecto a tu consulta (*\"{msg}\"*), aquí tienes una guía estructurada para el aula:\n\n"
        f"- **Objetivo didáctico:** Integrar herramientas de Inteligencia Artificial como apoyo al pensamiento crítico y no como sustituto del razonamiento del estudiante.\n"
        f"- **Estrategia metodológica:**\n"
        f"  1. Define con claridad el propósito de aprendizaje y los límites éticos del uso de IA.\n"
        f"  2. Solicita a los estudiantes documentar y contrastar las respuestas generadas con fuentes académicas verificables.\n"
        f"  3. Evalúa el proceso reflexivo, la argumentación oral y la apropiación conceptual.\n\n"
        f"¿Te gustaría que profundicemos en una rúbrica de evaluación o en una actividad práctica para tu curso?"
    )


def generate_chat_response(message: str, publication_id: int | str | None = None, history: list = None) -> dict:
    """
    Genera una respuesta utilizando la API de Google Gemini con respaldo pedagógico inmediato.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

    context_used = False
    context_text = ""
    pub_meta = None

    if publication_id:
        try:
            pub = Publication.objects.select_related("category", "educator", "educator__user").filter(id=publication_id).first()
            if pub:
                author_name = "Educador"
                if pub.educator:
                    author_name = pub.educator.nick_name or (pub.educator.user.name if pub.educator.user else pub.educator.user.email)
                cat_name = pub.category.name if pub.category else "Sin categoría"
                pub_type = pub.get_publication_type_display() if hasattr(pub, "get_publication_type_display") else getattr(pub, "publication_type", "Publicación")

                content_body = ""
                if hasattr(pub, "content") and pub.content:
                    content_body = pub.content
                elif getattr(pub, "content_url", None):
                    try:
                        from .storage import get_publication_html
                        content_body = get_publication_html(pub.content_url)
                    except Exception:
                        content_body = f"[Contenido en: {pub.content_url}]"

                pub_meta = {
                    "id": pub.id,
                    "title": pub.title,
                    "type": pub_type,
                    "category": cat_name,
                    "author": author_name,
                    "content": content_body,
                }
                context_text = (
                    f"\n\n[MARCO DE REFERENCIA - PUBLICACIÓN ACTUAL]\n"
                    f"ID: {pub.id}\n"
                    f"Título: {pub.title}\n"
                    f"Tipo: {pub_type}\n"
                    f"Categoría: {cat_name}\n"
                    f"Autor: {author_name}\n"
                    f"Contenido completo:\n{content_body}\n"
                    f"[FIN DEL MARCO DE REFERENCIA]\n\n"
                    f"Utiliza este contexto para responder la consulta del educador de manera precisa si aplica."
                )
                context_used = True
        except Exception as e:
            logger.warning("[GeminiService] Error fetching publication context: %s", e)

    if not api_key or not api_key.startswith("AIza"):
        return {
            "response": _build_pedagogical_fallback(message, pub_meta),
            "context_used": context_used,
        }

    gemini_history = []
    if history and isinstance(history, list):
        for item in history:
            role = item.get("role", "user")
            content = item.get("content", "")
            if role in ("assistant", "model"):
                role = "model"
            elif role != "user":
                role = "user"
            if content:
                gemini_history.append({"role": role, "parts": [{"text": content}]})

    model_name = getattr(settings, "GEMINI_MODEL_NAME", "gemini-2.0-flash") or os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
    full_system_instruction = SYSTEM_INSTRUCTION + context_text
    models_to_try = [model_name] if model_name in ("gemini-2.0-flash", "gemini-1.5-flash") else ["gemini-2.0-flash"]

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=6000))
    try:
        contents = [*gemini_history, {"role": "user", "parts": [{"text": message}]}]
        for m_name in models_to_try:
            try:
                result = client.models.generate_content(
                    model=m_name,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=full_system_instruction),
                )
                if result and result.text:
                    return {"response": result.text, "context_used": context_used}
            except Exception as exc:
                logger.warning("Gemini model %s failed: %s", m_name, type(exc).__name__)
                break

        return {
            "response": _build_pedagogical_fallback(message, pub_meta),
            "context_used": context_used,
        }
    finally:
        client.close()
