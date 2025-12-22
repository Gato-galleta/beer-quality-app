🍺 Beer Quality App

Aplicación Web para Control de Calidad en Cervecería

📌 Descripción del proyecto

Beer Quality App es una aplicación web desarrollada con Django que permite registrar, consultar y revisar parámetros de calidad asociados al proceso productivo cervecero.
El sistema está orientado a apoyar la toma de decisiones de control de calidad, facilitando la detección temprana de desviaciones en variables críticas del proceso.

El proyecto corresponde a un CRUD web funcional, desplegado tanto en entorno local como en entorno Cloud, cumpliendo los requisitos académicos de desarrollo, arquitectura y despliegue.

🎯 Problemática abordada

En la industria cervecera, el control de calidad depende del seguimiento constante de variables fisicoquímicas y operacionales.
La ausencia de herramientas centralizadas para la consulta de estos parámetros puede generar:

retrasos en la detección de desviaciones,

aumento de mermas,

decisiones correctivas tardías.

Esta aplicación busca centralizar la información de calidad, permitiendo su consulta rápida y estructurada desde una interfaz web.

🧱 Arquitectura del sistema

La aplicación sigue una arquitectura cliente-servidor, basada en el patrón MVC (Model–View–Template) propio de Django.

Componentes principales:

Frontend: Templates HTML gestionados por Django.

Backend: Framework Django (Python).

Base de datos: SQLite (entorno local).

Servidor de producción: Gunicorn.

Gestión de archivos estáticos: WhiteNoise.

Despliegue Cloud: Render.

📁 Estructura del proyecto
beer_quality_app/
│
├── build.sh
├── manage.py
├── requirements.txt
├── README.md
│
├── beer_quality/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── quality/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── templates/
│
└── .gitignore

⚙️ Requisitos del sistema

Python 3.9+

Django

Gunicorn

WhiteNoise

🚀 Instalación y ejecución local
1️⃣ Clonar el repositorio
git clone https://github.com/TU_USUARIO/beer-quality-app.git
cd beer-quality-app

2️⃣ Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate   # Windows

3️⃣ Instalar dependencias
pip install -r requirements.txt

4️⃣ Aplicar migraciones
python manage.py migrate

5️⃣ Ejecutar servidor local
python manage.py runserver


📍 Acceder en el navegador:

http://127.0.0.1:8000/quality/

☁️ Despliegue en Cloud (Render)

El proyecto se encuentra desplegado en Render, utilizando:

Build Command

./build.sh


Start Command

gunicorn beer_quality.wsgi:application


📍 URL del despliegue:

https://beer-quality-app-1.onrender.com/quality/

🧪 Funcionalidades principales

Acceso web a la aplicación de control de calidad.

Estructura CRUD base para gestión de información.

Arquitectura preparada para integración de reglas de decisión y modelos analíticos.

Despliegue funcional en entorno Cloud.

📚 Tecnologías utilizadas

Python

Django

HTML

SQLite

Gunicorn

Render

👥 Equipo de trabajo

Proyecto desarrollado con fines académicos como parte de una evaluación sumativa, demostrando el uso de frameworks web, patrones de diseño y despliegue en la nube.
