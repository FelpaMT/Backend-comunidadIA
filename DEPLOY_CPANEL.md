# Despliegue de ComunidadIA en cPanel

Esta guía asume que el frontend se sirve como archivos estáticos y Django corre como aplicación WSGI de Passenger.

## Requisitos del plan

Confirma con el proveedor que tu cuenta tiene **Setup Python App** (Passenger/Python Selector), SSH o Git Version Control y **PostgreSQL** habilitado. Este backend requiere PostgreSQL cuando `DJANGO_DEBUG=False`; SQLite está limitado al desarrollo y el proyecto no está configurado para MySQL. Usa Python 3.12 si está disponible; Django 5.2.18 admite Python 3.10–3.14.

Usa un dominio para el frontend, por ejemplo `https://www.example.com`, y un subdominio separado para la API, por ejemplo `https://api.example.com`. La aplicación Passenger de la API debe quedar montada en la raíz del subdominio, ya que Django incluye la ruta `/api/`.

## 1. Crear la base de datos

En cPanel, abre **PostgreSQL Database Wizard**, crea una base y un usuario con contraseña única, y asigna el usuario a la base. Copia los nombres completos: muchos hostings les agregan un prefijo con el usuario de cPanel. Usa el host de base de datos que indique el proveedor; no asumas `localhost` si su servicio es externo.

## 2. Subir y registrar el backend

Clona este repositorio fuera de `public_html`, por ejemplo en `/home/CPANEL_USER/apps/comunidadia-backend`. En **Setup Python App**, crea la aplicación con el directorio raíz del repositorio, selecciona una versión de Python compatible y configura el archivo de inicio `passenger_wsgi.py` y el callable `application`.

Instala `requirements.txt` en el entorno virtual que muestra cPanel. El comando de activación exacto depende de la ruta que genere el panel; cópialo de la interfaz. Después:

```bash
cd /home/CPANEL_USER/apps/comunidadia-backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Configurar secretos y servicios

Crea `.env` en el directorio del backend, fuera del document root, y limita sus permisos al usuario de cPanel (`chmod 600 .env` si SSH está disponible). Completa los valores de `.env.example` con los datos reales:

- `DJANGO_SECRET_KEY`: valor aleatorio privado de al menos 50 caracteres.
- `DJANGO_DEBUG=False` y `DJANGO_ALLOWED_HOSTS=api.example.com`.
- `CORS_ALLOWED_ORIGINS=https://www.example.com` (añade el dominio raíz únicamente si también sirve el frontend).
- `USE_POSTGRES=True` y credenciales PostgreSQL.
- `PUBLIC_ROOT`: document root real del frontend, por ejemplo `/home/CPANEL_USER/public_html`.
- `STATIC_ROOT`: carpeta pública `/static` dentro del document root.
- `MEDIA_ROOT`: carpeta pública `/comunidadia_uploads` dentro del document root.
- `DOMAIN` y `FRONTEND_URL`: URL HTTPS canónica del frontend (se usa para formar URLs públicas de archivos y enlaces de verificación).
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` o `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` y `DEFAULT_FROM_EMAIL`: credenciales SMTP de una cuenta de correo real del dominio. TLS y SSL no se deben activar a la vez.
- `GEMINI_API_KEY`: necesaria para habilitar el asistente de IA.

Puedes generar la clave de Django con Python desde SSH: `python -c 'import secrets; print(secrets.token_urlsafe(64))'`.

No copies `.env` a GitHub ni a `public_html`. El backend rechaza el backend de correo de consola y la configuración incompleta al arrancar con `DEBUG=False`.

Activa `SECURE_SSL_REDIRECT=True` cuando HTTPS esté disponible. Deja `SECURE_HSTS_SECONDS=0` durante la primera puesta en marcha; solo aumenta HSTS después de comprobar HTTPS para todos los subdominios que lo hereden.

## 4. Migrar, recolectar estáticos y crear el administrador de la API

Con el entorno virtual activado:

```bash
python manage.py migrate --noinput
python manage.py check --deploy
python manage.py create_api_admin
```

`create_api_admin` crea el usuario `ADMIN` de la API de forma interactiva y valida su contraseña. Es distinto al superusuario de Django Admin (`createsuperuser`). No cargues `initial_data.json` en producción: contiene datos de ejemplo, no cuentas con contraseñas utilizables.

En cPanel, reinicia la aplicación Passenger después de instalar dependencias, editar variables o publicar una versión nueva.

## 5. Construir el frontend

En el checkout local del repositorio frontend, usa Node.js 22.12+ o una versión LTS compatible con Vite y configura la URL pública de la API antes del build:

```bash
export VITE_API_URL=https://api.example.com
npm ci
npm run build
```

En PowerShell, define la variable en una línea separada: `$env:VITE_API_URL='https://api.example.com'`, luego ejecuta `npm ci` y `npm run build`.

Sube el **contenido** de `dist/` al document root del frontend. El build incluye `.htaccess`, que devuelve las rutas de React a `index.html` para que `/inicio`, `/signup` y otras rutas funcionen al recargar. Si el hosting no permite `.htaccess` o `mod_rewrite`, solicita al proveedor la regla equivalente. En futuras publicaciones, conserva las carpetas `static/` y `comunidadia_uploads/`: Django las usa para sus archivos y para las imágenes/publicaciones cargadas.

## 6. Verificación posterior

1. Activa AutoSSL para el frontend y la API.
2. Con el entorno virtual del backend, ejecuta `python manage.py collectstatic --noinput` después de subir el frontend, para asegurar que los archivos del administrador Django queden en `STATIC_ROOT`.
3. Abre el frontend y recarga una ruta interna.
4. Comprueba `https://api.example.com/api/schema/swagger/` y que no haya errores de `DisallowedHost` o CORS.
5. Registra una cuenta nueva y verifica que el mensaje llegue por SMTP; prueba inicio y cierre de sesión y restablecimiento de contraseña.
6. Prueba publicación, imagen/archivo, edición y chatbot.
7. Revisa los logs de Passenger y del correo si un flujo falla.

No compartas contraseñas, claves SMTP, la clave de Django ni la clave Gemini en tickets públicos o en GitHub.
