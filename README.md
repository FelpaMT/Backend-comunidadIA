# 🎓 Comunidad IA - Backend API

Servidor backend de **Comunidad IA**, una plataforma educativa orientada a docentes y profesionales para explorar, compartir publicaciones y consultar con un Asistente Virtual Pedagógico.

## 🚀 Funcionalidades Principales

- **Autenticación y Seguridad**: Registro de usuarios, verificación de correo electrónico y gestión de sesiones seguras.
- **Red de Educadores**: Directorio de docentes, perfiles profesionales y sistema de seguimiento mutuo.
- **Publicaciones y Foros**: Creación y categorización de artículos educativos, foros de debate, imágenes y comentarios.
- **Asistente Virtual Pedagógico**: Tutor inteligente integrado para resolver dudas didácticas e inyectar el contexto de las publicaciones.

## 🛠️ Tecnologías

- **Python & Django**
- **Django REST Framework**
- **OpenAPI / Swagger**

## 📋 Instalación y Ejecución

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuración de Variables de Entorno**:
   Copia el archivo `.env.example` a `.env` y ajusta tus credenciales.

3. **Aplicar Migraciones**:
   ```bash
   python manage.py migrate
   ```

4. **Iniciar Servidor**:
   ```bash
   python manage.py runserver 8000
   ```
   La API estará accesible en `http://localhost:8000`.

## 📚 Documentación Interactiva (Swagger)

Accede a la documentación OpenAPI en: `http://localhost:8000/api/schema/swagger/`