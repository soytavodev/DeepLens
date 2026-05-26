# DeepLens 👁️

## 📋 Descripción
Herramienta de automatización y auditoría visual impulsada por Inteligencia Artificial. `DeepLens` es capaz de examinar código backend crudo y HTML fragmentado de un repositorio, deducir la interfaz de usuario que se pretende construir, inyectar dinámicamente un framework de estilos minimalista (*Classless CSS*) y utilizar un navegador automatizado en modo *headless* para renderizar y capturar mockups estáticos de alta fidelidad, todo sin necesidad de desplegar el servidor web real del proyecto.

---

## 🛠️ Stack Tecnológico
* **Lenguaje:** Python 3.x
* **Automatización Web:** Playwright (Chromium Headless).
* **Core IA:** Ollama API (`qwen3.5:latest`).
* **Estilos Dinámicos:** Pico.css (Framework inyectado al vuelo).
* **Procesamiento de Texto:** Regex avanzados y validación estricta de payloads JSON.

---

## 🏗️ Estructura del Proyecto
```text
/DeepLens
├── main.py            # Analizador del código, inyector CSS y capturador Playwright
├── README.md          # Documentación del proyecto
├── error_ia_crudo.txt # Logs de control y depuración de respuestas de la IA
└── temp_*.html        # Plantillas HTML intermedias forzadas por el parseador
```
---

## ⚙️ Características Principales
* **Filtro Inteligente de Ruido:** El script ignora automáticamente directorios masivos como `node_modules`, `vendor` o configuraciones locales, enfocándose estrictamente en los archivos de lógica visual (`index.php`, `main.py`, `app.js`, etc.).
* **Inyección Classless CSS:** Transforma código HTML plano y desestructurado devuelto por la IA en interfaces modernas inyectando `Pico.css` en tiempo de ejecución.
* **Generación de Evidencias Visuales:** Automatiza el lanzamiento de navegadores de fondo para tomar capturas `.png` perfectas que sirven como mockups de la aplicación.

---

## 🚀 Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/soytavodev/DeepLens.git](https://github.com/soytavodev/DeepLens.git)
   cd DeepLens
Instalar dependencias y entornos de Playwright:

Bash
pip install -r requirements.txt
playwright install chromium
Ejecutar la herramienta apuntando a tu código objetivo:

Bash
python3 main.py --ruta /ruta/a/tu/proyecto
