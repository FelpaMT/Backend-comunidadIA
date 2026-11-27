# Manifiesto de Dependencias de Terceros y Licencias Aplicables — ComunidadIA

**Proyecto:** ComunidadIA — Plataforma Web Educativa para Docentes con Inteligencia Artificial  
**Autores:** Felipe Alejandro Paez Vargas, Luis Felipe Mayorga Tibaquicha  
**Semillero / Institución:** Semillero VIRTUS — Universidad Distrital Francisco José de Caldas / ETITC  
**Propósito:** Cumplimiento del Literal b) de los requisitos de registro y entrega de soporte lógico (*"El manifiesto de dependencias de terceros con indicación de la licencia aplicable a cada componente"*).

---

## 1. Dependencias del Backend (`Backend-comunidadIA/requirements.txt`)

Todas las dependencias de terceros del backend corresponden a bibliotecas de código abierto con licencias permisivas o compatibles (BSD, MIT, Apache-2.0, PSF-2.0, LGPL) que autorizan su uso, distribución y despliegue institucional sin restricciones comerciales ni regalías.

| Paquete / Componente | Versión | Licencia Aplicable | Propósito en el Sistema |
| :--- | :--- | :--- | :--- |
| `Django` | `5.2.18` (o `5.1.15` LTS en PG 13) | `BSD-3-Clause` | Framework web principal, ORM relacional, sistema de migraciones y correo SMTP. |
| `djangorestframework` | `3.15.2` | `BSD-3-Clause` | Construcción de la API RESTful, serializadores, permisos y limitación de tasas (throttling). |
| `djangorestframework_simplejwt` | `5.5.1` | `MIT` | Soporte y utilidades para autenticación basada en JSON Web Tokens (JWT). |
| `PyJWT` | `2.9.0` | `MIT` | Codificación, firma criptográfica (`HS256`) y verificación de tokens JWT. |
| `django-cors-headers` | `4.9.0` | `MIT` | Gestión de cabeceras Cross-Origin Resource Sharing (CORS) entre frontend y API. |
| `drf-spectacular` | `0.27.2` | `BSD-3-Clause` | Generación automática del esquema OpenAPI 3.0 e interfaz Swagger UI. |
| `google-genai` | `2.29.0` | `Apache-2.0` | SDK oficial de Google para el consumo de los modelos generativos Gemini en el Tutor IA. |
| `psycopg2-binary` | `>=2.9.10` | `LGPL-3.0-with-linking-exception` | Adaptador en lenguaje C para conexión con el motor PostgreSQL. |
| `nh3` | `0.3.2` | `MIT` | Sanitizador de HTML basado en Rust (Ammonia) para prevención de XSS en servidor. |
| `pillow` | `12.0.0` | `MIT-CMU` | Validación e inspección de archivos de imagen adjuntos a publicaciones. |
| `python-dotenv` | `1.0.1` | `BSD-3-Clause` | Carga de variables de entorno desde archivo `.env`. |
| `asgiref` | `3.10.0` | `BSD-3-Clause` | Especificación ASGI y utilidades base requeridas por Django. |
| `sqlparse` | `0.5.3` | `BSD-3-Clause` | Analizador sintáctico SQL no validante requerido por Django. |
| `PyYAML` | `6.0.3` | `MIT` | Procesamiento de formato YAML para esquemas OpenAPI. |
| `jsonschema` | `4.25.1` | `MIT` | Validación de especificaciones JSON Schema en `drf-spectacular`. |
| `jsonschema-specifications` | `2025.9.1` | `MIT` | Archivos de especificación estándar de JSON Schema. |
| `referencing` | `0.37.0` | `MIT` | Resolución de referencias URI en esquemas JSON/OpenAPI. |
| `rpds-py` | `0.28.0` | `MIT` | Estructuras de datos persistentes requeridas por `jsonschema`. |
| `attrs` | `25.4.0` | `MIT` | Declaración declarativa de clases en dependencias de validación. |
| `inflection` | `0.5.1` | `MIT` | Transformación de cadenas para nomenclatura de esquemas OpenAPI. |
| `uritemplate` | `4.2.0` | `BSD-3-Clause OR Apache-2.0` | Expansión de plantillas URI RFC 6570 en rutas de OpenAPI. |
| `typing_extensions` | `4.15.0` | `PSF-2.0` | Soporte de anotaciones de tipo avanzadas en Python. |
| `django-extensions` | `4.1` | `MIT` | Comandos extendidos de administración y utilidades de desarrollo para Django. |
| `graphviz` | `0.21` | `MIT` | Interfaz Python para renderizado de grafos con Graphviz. |
| `pydotplus` | `2.0.2` | `MIT` | Interfaz Python al lenguaje DOT de Graphviz. |
| `pyparsing` | `3.2.5` | `MIT` | Analizador gramatical utilizado por `pydotplus`. |
| `pylint` | `4.0.4` | `GPL-2.0-only` | Herramienta de análisis estático de calidad de código (solo entorno de desarrollo). |
| `astroid` | `4.0.2` | `LGPL-2.1-or-later` | Biblioteca de análisis de árboles sintácticos (AST) para `pylint` (solo desarrollo). |
| `isort` | `7.0.0` | `MIT` | Ordenamiento de importaciones Python (solo desarrollo). |
| `mccabe` | `0.7.0` | `MIT` | Verificador de complejidad ciclomática para `pylint` (solo desarrollo). |
| `dill` | `0.4.0` | `BSD-3-Clause` | Serialización extendida de objetos Python para caché de análisis estático. |
| `platformdirs` | `4.5.1` | `MIT` | Resolución multiplataforma de rutas de usuario y caché. |
| `tomlkit` | `0.13.3` | `MIT` | Procesamiento de archivos de configuración TOML. |

---

## 2. Dependencias del Frontend (`Frontend-ComunidadIA/package.json`)

| Paquete / Componente npm | Versión Declarada | Tipo | Licencia Aplicable | Propósito en el Sistema |
| :--- | :--- | :--- | :--- | :--- |
| `react` | `^19.2.0` | Producción | `MIT` | Biblioteca principal para construcción de interfaces de usuario basadas en componentes. |
| `react-dom` | `^19.2.0` | Producción | `MIT` | Punto de montaje y renderizado del árbol de componentes React en el DOM. |
| `react-router-dom` | `^7.9.6` | Producción | `MIT` | Enrutamiento declarativo SPA (`BrowserRouter`), rutas públicas y protegidas. |
| `axios` | `^1.13.2` | Producción | `MIT` | Cliente HTTP centralizado con interceptores de autenticación y refresco JWT. |
| `dompurify` | `^3.4.15` | Producción | `Apache-2.0 OR MPL-2.0` | Sanitización del árbol DOM en el navegador contra ataques XSS. |
| `quill` | `2.0.2` | Producción | `BSD-3-Clause` | Editor de texto enriquecido WYSIWYG para creación y edición de publicaciones. |
| `marked` | `^17.0.1` | Producción | `MIT` | Analizador y compilador de Markdown a HTML para respuestas del Tutor IA. |
| `lucide-react` | `^1.11.0` | Producción | `ISC` | Colección de íconos vectoriales SVG para la interfaz. |
| `clsx` | `^2.1.1` | Producción | `MIT` | Utilidad para composición condicional de clases CSS. |
| `tailwind-merge` | `^3.5.0` | Producción | `MIT` | Fusión determinista de clases utilitarias de Tailwind CSS. |
| `class-variance-authority` | `^0.7.1` | Producción | `Apache-2.0` | Gestión estructurada de variantes visuales de componentes. |
| `vite` | `^7.2.4` | Desarrollo / Build | `MIT` | Servidor de desarrollo ESM y empaquetador de activos estáticos de producción. |
| `@vitejs/plugin-react` | `^5.1.1` | Desarrollo / Build | `MIT` | Plugin oficial de soporte React y Fast Refresh para Vite. |
| `tailwindcss` | `^4.3.3` | Desarrollo / Build | `MIT` | Framework CSS utilitario con soporte nativo para tema claro y oscuro. |
| `@tailwindcss/postcss` | `^4.3.3` | Desarrollo / Build | `MIT` | Integración de compilación de Tailwind CSS v4 sobre PostCSS. |
| `postcss` | `^8.5.10` | Desarrollo / Build | `MIT` | Herramienta de transformación de hojas de estilo CSS. |
| `autoprefixer` | `^10.5.0` | Desarrollo / Build | `MIT` | Generación automática de prefijos de compatibilidad CSS entre navegadores. |
| `eslint` | `^9.39.1` | Desarrollo / Lint | `MIT` | Motor de análisis estático de código JavaScript y JSX. |
| `@eslint/js` | `^9.39.1` | Desarrollo / Lint | `MIT` | Reglas estándar recomendadas de ESLint para JavaScript. |
| `eslint-plugin-react-hooks` | `^7.0.1` | Desarrollo / Lint | `MIT` | Validación estática de las reglas de Hooks de React. |
| `eslint-plugin-react-refresh` | `^0.4.24` | Desarrollo / Lint | `MIT` | Validación de exportación segura de componentes para Fast Refresh. |
| `globals` | `^16.5.0` | Desarrollo / Lint | `MIT` | Diccionario de variables globales de entornos Browser y ES2021+. |
| `@types/react` | `^19.2.5` | Desarrollo | `MIT` | Definiciones de tipos TypeScript para el núcleo de React. |
| `@types/react-dom` | `^19.2.3` | Desarrollo | `MIT` | Definiciones de tipos TypeScript para `react-dom`. |
| `cypress` | `^16.4.0` | Desarrollo / Pruebas E2E | `MIT` | Framework de pruebas automatizadas *End-to-End* en navegador (20 casos E2E en 5 suites). |
