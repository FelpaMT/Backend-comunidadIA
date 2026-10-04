import google.generativeai as genai
from django.conf import settings
from .models import Publication

SYSTEM_INSTRUCTION = (
    "Eres un Tutor pedagógico experto en Inteligencia Artificial y educación. "
    "Tu tono debe ser empático, didáctico, claro y ético. Guías a educadores, docentes "
    "y profesionales a comprender, aplicar y reflexionar sobre la IA en el ámbito educativo. "
    "Responde siempre en español formateado en Markdown claro y estructurado."
)

def generate_chat_response(message: str, publication_id: int | str | None = None, history: list = None) -> dict:
    """
    Genera una respuesta utilizando la API de Google Gemini (gemini-1.5-flash por defecto).
    
    :param message: Consulta enviada por el usuario.
    :param publication_id: ID opcional de publicación para inyectar contexto pedagógico.
    :param history: Historial conversacional previo [{'role': 'user'|'model', 'content': '...'}].
    :return: dict con 'response' y 'context_used'.
    """
    import os
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        # Intentar cargar .env si no fue cargado previamente
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(settings.BASE_DIR) / ".env", override=True)
        api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        return {
            "response": "Error de configuración: La clave GEMINI_API_KEY no está definida en el backend.",
            "context_used": False
        }
    
    genai.configure(api_key=api_key)
    
    context_used = False
    context_text = ""
    
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
            print(f"[GeminiService] Error fetching publication context: {e}")

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
                gemini_history.append({"role": role, "parts": [content]})
                
    model_name = getattr(settings, "GEMINI_MODEL_NAME", "gemini-3.8-flash") or os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")
    full_system_instruction = SYSTEM_INSTRUCTION + context_text

    candidate_models = [model_name, "gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    # Eliminar duplicados preservando orden
    seen = set()
    models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

    last_exception = None
    for m_name in models_to_try:
        try:
            model = genai.GenerativeModel(
                model_name=m_name,
                system_instruction=full_system_instruction,
            )
            chat = model.start_chat(history=gemini_history)
            res = chat.send_message(message)
            return {
                "response": res.text,
                "context_used": context_used
            }
        except Exception as e:
            last_exception = e
            print(f"[GeminiService] Model '{m_name}' failed: {e}. Trying next model...")

    return {
        "response": f"Lo siento, ocurrió un problema al consultar el servicio de IA: {str(last_exception)}",
        "context_used": context_used
    }
