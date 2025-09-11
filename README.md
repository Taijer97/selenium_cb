# Generador de Reportes PDF - API Segura

API segura para generar reportes PDF de créditos usando DNI con autenticación JWT y medidas de seguridad avanzadas.

## 🔒 Características de Seguridad

- ✅ Autenticación JWT
- ✅ Rate Limiting
- ✅ Validación y sanitización de entrada
- ✅ CORS configurado de forma segura
- ✅ Logging de seguridad
- ✅ Prevención de Path Traversal
- ✅ Control de acceso por roles

## 🚀 Instalación

### Requisitos Previos
- Python 3.8+
- Chrome/Chromium browser
- Docker (opcional)

### Instalación Local

1. Clona el repositorio:
```bash
git clone https://github.com/tu-usuario/selenium_cb.git
cd selenium_cb
```

2. Crea un entorno virtual:
```bash
python -m venv env
env\Scripts\activate  # Windows
# source env/bin/activate  # Linux/Mac
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita .env con tus configuraciones
```

5. Ejecuta la aplicación:
```bash
python app.py
```

### Instalación con Docker

```bash
docker build -t selenium_cb-pdf-generator .
docker run -d -p 8500:8500 selenium_cb-pdf-generator
```

## 📖 Uso de la API

### Autenticación

1. Obtener token de acceso:
```bash
curl -X POST "http://localhost:8500/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=secret"
```

2. Usar el token en las peticiones:
```bash
curl -X POST "http://localhost:8500/generate-pdf" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"dni": "12345678"}'
```

### Endpoints Disponibles

- `POST /token` - Obtener token de acceso
- `POST /generate-pdf` - Generar PDF por DNI
- `POST /generate-and-download-pdf` - Generar y descargar PDF
- `GET /download/{filename}` - Descargar PDF específico
- `GET /list-pdfs` - Listar PDFs disponibles
- `DELETE /cleanup-pdfs` - Limpiar PDFs antiguos (solo admin)

## 🔐 Credenciales por Defecto

- **Admin**: `admin` / `secret`
- **Usuario**: `user` / `secret`

⚠️ **IMPORTANTE**: Cambia estas credenciales en producción.

## 🛡️ Configuración de Seguridad

### Variables de Entorno Importantes

```env
SECRET_KEY=tu-clave-secreta-muy-segura
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=INFO
```

### Rate Limits

- Login: 5 intentos/minuto
- Generación PDF: 10/minuto
- Descarga: 20/minuto
- Limpieza: 2/hora

## 🐳 Docker

El proyecto incluye configuración completa de Docker con todas las dependencias necesarias.

## 📝 Logging

Todos los eventos de seguridad se registran en `security.log`:
- Intentos de login
- Generación de PDFs
- Accesos a archivos
- Errores de seguridad

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## ⚠️ Advertencias de Seguridad

- Nunca subas el archivo `.env` al repositorio
- Cambia la `SECRET_KEY` en producción
- Usa HTTPS en producción
- Revisa regularmente los logs de seguridad
- Mantén las dependencias actualizadas