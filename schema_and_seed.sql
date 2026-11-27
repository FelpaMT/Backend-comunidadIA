-- =============================================================================
-- COMUNIDADIA - ESQUEMA DE BASE DE DATOS, DATOS SEMILLA Y PARAMETROS DE IA
-- Cumplimiento del Literal c) para Registro de Soporte Logico y Entrega ETITC:
-- "El esquema y contenido de la base de datos, asi como los conjuntos de datos
--  utilizados y los modelos entrenados con sus parametros"
-- =============================================================================
-- Motor objetivo: PostgreSQL 13 / 14 / 15 / 16+
-- Codificacion: UTF-8
-- Zona horaria: America/Bogota
--
-- NOTA SOBRE MODELOS DE INTELIGENCIA ARTIFICIAL Y PARAMETROS:
-- ComunidadIA NO entrena ni almacena pesos neuronales locales propios.
-- El Tutor Pedagogico utiliza una arquitectura RAG (Retrieval-Augmented Generation)
-- consumiendo por API el modelo preentrenado Google Gemini (SDK google-genai==2.29.0)
-- con los siguientes parametros configurados en core/gemini_service.py y core/views.py:
--   * Modelo principal en produccion: GEMINI_MODEL_NAME = "gemini-2.5-flash"
--   * Cadena de modelos de respaldo (fallback):
--       [GEMINI_MODEL_NAME, "gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]
--   * SYSTEM_INSTRUCTION:
--       "Eres un Tutor pedagogico experto en Inteligencia Artificial y educacion.
--        Tu tono debe ser empatico, didactico, claro y etico. Guias a educadores,
--        docentes y profesionales a comprender, aplicar y reflexionar sobre la IA
--        en el ambito educativo. Responde siempre en espanol formateado en Markdown
--        claro y estructurado."
--   * Limite de caracteres por mensaje: 4000 caracteres.
--   * Ventana de historial conversacional: maximo 20 mensajes (hasta 4000 caracteres c/u).
--   * Limite de tasa (Throttling scope 'chat'): 30 solicitudes por minuto.
-- =============================================================================

BEGIN;

-- 1. Tabla de Usuarios y Credenciales (core_user)
CREATE TABLE IF NOT EXISTS core_user (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'EDUCATOR',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE
);

-- 2. Tabla de Perfiles Profesionales de Educadores (core_educator)
CREATE TABLE IF NOT EXISTS core_educator (
    id BIGSERIAL PRIMARY KEY,
    nick_name VARCHAR(255) UNIQUE,
    user_id BIGINT NOT NULL UNIQUE REFERENCES core_user(id) ON DELETE CASCADE,
    bio TEXT NOT NULL DEFAULT '',
    institution VARCHAR(255) NOT NULL DEFAULT '',
    specialty VARCHAR(255) NOT NULL DEFAULT '',
    avatar VARCHAR(500) NOT NULL DEFAULT '',
    website VARCHAR(500) NOT NULL DEFAULT '',
    linkedin_url VARCHAR(500) NOT NULL DEFAULT ''
);

-- 3. Tabla de Categorias Pedagogicas (core_category)
CREATE TABLE IF NOT EXISTS core_category (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

-- 4. Tabla de Publicaciones - Articulos y Foros (core_publication)
-- El cuerpo HTML sanitizado con nh3 se almacena fisicamente en MEDIA_ROOT/publications/<uuid>.html
CREATE TABLE IF NOT EXISTS core_publication (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    educator_id BIGINT NOT NULL REFERENCES core_educator(id) ON DELETE CASCADE,
    publication_type VARCHAR(20) NOT NULL CHECK (publication_type IN ('ARTICLE', 'FORUM')),
    content_url VARCHAR(1000) NOT NULL,
    category_id BIGINT REFERENCES core_category(id) ON DELETE SET NULL
);

-- 5. Tabla de Imagenes Adjuntas a Publicaciones (core_image)
CREATE TABLE IF NOT EXISTS core_image (
    id BIGSERIAL PRIMARY KEY,
    publication_id BIGINT NOT NULL REFERENCES core_publication(id) ON DELETE CASCADE,
    file VARCHAR(100) NOT NULL,
    url VARCHAR(200),
    caption VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Tabla de Comentarios en Publicaciones (core_commentary)
CREATE TABLE IF NOT EXISTS core_commentary (
    id BIGSERIAL PRIMARY KEY,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    educator_id BIGINT NOT NULL REFERENCES core_educator(id) ON DELETE CASCADE,
    publication_id BIGINT NOT NULL REFERENCES core_publication(id) ON DELETE CASCADE
);

-- 7. Tabla de Suscripciones / Seguimiento entre Educadores (core_subscription)
CREATE TABLE IF NOT EXISTS core_subscription (
    id BIGSERIAL PRIMARY KEY,
    subscriber_id BIGINT NOT NULL REFERENCES core_educator(id) ON DELETE CASCADE,
    subscribed_id BIGINT NOT NULL REFERENCES core_educator(id) ON DELETE CASCADE,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT core_subscription_subscriber_subscribed_uniq UNIQUE (subscriber_id, subscribed_id),
    CONSTRAINT core_subscription_no_self_follow CHECK (subscriber_id <> subscribed_id)
);

-- 8. Tabla de Tokens de Renovacion de Sesion (core_refreshtoken)
-- Almacena el digesto SHA-256 del refresh token, nunca el token en texto plano.
CREATE TABLE IF NOT EXISTS core_refreshtoken (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES core_user(id) ON DELETE CASCADE,
    token VARCHAR(512) NOT NULL,
    expiry_date TIMESTAMPTZ NOT NULL
);

-- 9. Tabla de Tokens y Codigos de Verificacion de Correo (core_emailverificationtoken)
-- Almacena los digestos SHA-256 del codigo de 6 digitos y del token de enlace.
CREATE TABLE IF NOT EXISTS core_emailverificationtoken (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    code VARCHAR(64) NOT NULL,
    token VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    is_used BOOLEAN NOT NULL DEFAULT FALSE
);

-- 10. Tabla de Tokens de Recuperacion de Contrasena (core_passwordresettoken)
CREATE TABLE IF NOT EXISTS core_passwordresettoken (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    token VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE
);

-- =============================================================================
-- CONTENIDO SEMILLA OFICIAL (CONJUNTO DE DATOS BASE DE CATEGORIAS PEDAGOGICAS)
-- Fuente: core/management/commands/seed_categories.py
-- =============================================================================
INSERT INTO core_category (name, slug, description) VALUES
    ('IA Generativa en el Aula', 'ia-generativa', 'Uso de modelos como ChatGPT, Gemini o Claude en actividades pedagógicas y planificación de clases.'),
    ('Prompts y Diseño Instruccional', 'prompts-educativos', 'Plantillas de prompts, rúbricas, guías didácticas y diseño de material educativo asistido por IA.'),
    ('Ética y Privacidad Escolar', 'etica-ia', 'Debates sobre derechos de autor, plagio, sesgos algorítmicos y protección de datos estudiantiles.'),
    ('Herramientas y Recursos', 'herramientas-ia', 'Reseñas, tutoriales y recomendaciones de plataformas digitales e inteligencia artificial para profesores.'),
    ('Evaluación con IA', 'evaluacion-ia', 'Estrategias de retroalimentación formativa, calificación asistida y creación de exámenes adaptativos.'),
    ('Investigación y Tendencias', 'investigacion', 'Artículos académicos, estudios de caso y noticias sobre el futuro de la tecnología educativa.'),
    ('Debates y Experiencias', 'debates', 'Espacio abierto para compartir anécdotas de aula, dudas y reflexiones entre docentes.')
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    description = EXCLUDED.description;

COMMIT;
