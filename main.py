import os
import requests
import re
import json
import argparse
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN IA LOCAL ---
AI_URL = "https://covalently-untasked-daphne.ngrok-free.dev/api/"
AI_USER = "jocarsa"
AI_PASS = "jocarsa"
AI_MODEL = "qwen3.5:latest"

# Inyección de framework CSS Classless (hace que cualquier HTML bruto se vea moderno)
CSS_INJECTION = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">'

def leer_codigo_proyecto(ruta_carpeta):
    """Filtra basura y extrae contexto relevante del código."""
    contenido = ""
    archivos_clave = ['index.php', 'main.py', 'README.md', 'header.php', 'menu.php', 'app.js', 'db.php']
    
    for root, dirs, files in os.walk(ruta_carpeta):
        # Filtro inteligente de ruido: ignoramos carpetas pesadas/basura
        if any(ignorar in root for ignorar in ['node_modules', 'vendor', '.git', '__pycache__', 'img', 'video', 'assets']):
            continue
            
        for file in files:
            if file in archivos_clave or file.endswith('.php') or file.endswith('.html'):
                ruta_archivo = os.path.join(root, file)
                try:
                    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
                        contenido += f"\n--- Archivo: {ruta_archivo} ---\n"
                        # Limitamos a 250 líneas por archivo para no ahogar el LLM
                        contenido += "".join(f.readlines()[:250]) 
                except Exception:
                    pass
                    
    # Límite de seguridad para el contexto de la IA local
    return contenido[:12000]

def generar_mockups_json(codigo_fuente):
    print("🧠 Analizando código para extraer pantallas y generar reporte...")
    
    system_prompt = "Eres un procesador de datos backend. Tu única salida de texto debe ser formato JSON puro y válido. Tienes terminantemente prohibido usar lenguaje natural, saludar, o añadir explicaciones fuera del JSON."
    
    prompt = f"""
Extrae las pantallas o vistas principales que se generarían a partir de este código fuente.

REGLAS CRÍTICAS Y ABSOLUTAS:
1. Tu respuesta debe empezar OBLIGATORIAMENTE con la llave {{ y terminar con la llave }}.
2. NO uses bloques de código Markdown (como ```json). Escribe el JSON crudo.
3. Debes generar el código HTML estático (sin PHP/Python) que represente la interfaz descrita en el código.
4. Escapa correctamente las comillas dobles dentro del campo "html".

FORMATO JSON REQUERIDO:
{{
    "pantallas": [
        {{
            "nombre": "nombre_identificativo",
            "descripcion": "Descripción breve de la lógica y tablas implicadas.",
            "html": "<html><body><h1>Ejemplo</h1></body></html>"
        }}
    ]
}}

CÓDIGO FUENTE A ANALIZAR:
{codigo_fuente}

DEVUELVE ÚNICAMENTE EL JSON A PARTIR DE AQUÍ:
{{
    "pantallas": [
"""
    
    payload = {
        "user": AI_USER,
        "password": AI_PASS,
        "action": "generate",
        "model": AI_MODEL,
        "system": system_prompt,
        "question": prompt
    }
    
    try:
        res = requests.post(AI_URL, json=payload, timeout=240)
        res.raise_for_status()
        
        datos = res.json() if "application/json" in res.headers.get("Content-Type", "") else res.text
        respuesta_cruda = datos["answer"] if isinstance(datos, dict) and "answer" in datos else res.text
        
        # --- LIMPIEZA EXTREMA DEL STRING ---
        respuesta_limpia = respuesta_cruda.strip()
        
        # Como le forzamos a empezar el JSON en el prompt, si el modelo omitió el inicio, se lo reconstruimos:
        if not respuesta_limpia.startswith("{") and not respuesta_limpia.startswith("```"):
            if '"nombre"' in respuesta_limpia or "'nombre'" in respuesta_limpia:
                 respuesta_limpia = '{\n    "pantallas": [\n' + respuesta_limpia

        # Quitar marcas de markdown
        if respuesta_limpia.startswith("```json"):
            respuesta_limpia = respuesta_limpia[7:]
        elif respuesta_limpia.startswith("```"):
            respuesta_limpia = respuesta_limpia[3:]
        if respuesta_limpia.endswith("```"):
            respuesta_limpia = respuesta_limpia[:-3]
            
        respuesta_limpia = respuesta_limpia.strip()
        
        # Buscar forzosamente el primer '{' y el último '}'
        inicio = respuesta_limpia.find('{')
        fin = respuesta_limpia.rfind('}')
        
        if inicio != -1 and fin != -1:
            respuesta_limpia = respuesta_limpia[inicio:fin+1]
        else:
            raise ValueError("No se encontró estructura JSON en la respuesta de la IA.")
        
        # --- PARSEO ---
        return json.loads(respuesta_limpia)
            
    except json.JSONDecodeError as e:
        print(f"❌ La IA devolvió un JSON con errores de sintaxis: {e}")
        with open("error_json_roto.txt", "w", encoding="utf-8") as f: 
            f.write(respuesta_cruda)
        return None
    except Exception as e:
        print(f"❌ Error al procesar la respuesta de la IA: {e}")
        with open("error_ia_crudo.txt", "w", encoding="utf-8") as f:
            try:
                f.write(respuesta_cruda)
            except:
                pass
        return None

def tomar_capturas(ruta_carpeta, out_dir):
    if not os.path.isdir(ruta_carpeta):
        print(f"❌ Error: El directorio {ruta_carpeta} no existe.")
        return

    os.makedirs(out_dir, exist_ok=True)
    codigo = leer_codigo_proyecto(ruta_carpeta)
    
    if not codigo:
        print("❌ No se encontró código válido para analizar en esa carpeta.")
        return
        
    data = generar_mockups_json(codigo)
    if not data or "pantallas" not in data:
        print("❌ Abortando: No se pudieron parsear las pantallas.")
        return
        
    pantallas = data["pantallas"]
    print(f"🎯 ¡Éxito! La IA detectó {len(pantallas)} pantallas.")

    # --- GENERAR DOCUMENTACIÓN MARKDOWN ---
    reporte_md = f"# 🔍 Auditoría Visual de DeepLens\n\n"
    reporte_md += f"**Directorio analizado:** `{os.path.abspath(ruta_carpeta)}`\n"
    reporte_md += f"**Pantallas detectadas:** {len(pantallas)}\n\n---\n\n"
    
    for p in pantallas:
        reporte_md += f"## 🖥️ {p.get('nombre', 'Pantalla').capitalize()}\n"
        reporte_md += f"> {p.get('descripcion', 'Sin descripción')}\n\n"
        
    ruta_md = os.path.join(out_dir, "Auditoria_Visual.md")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(reporte_md)
    print(f"📄 Documentación Markdown generada en: {ruta_md}")

    # --- RENDERIZADO CON PLAYWRIGHT ---
    try:
        with sync_playwright() as p:
            print("🚀 Lanzando navegador Chromium headless...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            page = context.new_page()
            
            nombre_proyecto = os.path.basename(os.path.normpath(ruta_carpeta))
            
            for p_data in pantallas:
                nombre_pantalla = p_data.get('nombre', 'unknown')
                html_content = p_data.get('html', '')
                
                # INYECCIÓN DE CSS (PICO.CSS)
                if "</head>" in html_content:
                    html_content = html_content.replace("</head>", f"{CSS_INJECTION}\n</head>")
                elif "<html>" in html_content:
                    html_content = html_content.replace("<html>", f"<html><head>{CSS_INJECTION}</head>")
                else:
                    html_content = f"<!DOCTYPE html><html><head>{CSS_INJECTION}</head><body>{html_content}</body></html>"
                
                nombre_seguro = re.sub(r'[^a-zA-Z0-9]', '_', nombre_pantalla).lower()
                ruta_temp = os.path.abspath(os.path.join(out_dir, f"temp_{nombre_seguro}.html"))
                
                with open(ruta_temp, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                print(f"🌐 Renderizando vista: {nombre_pantalla}...")
                page.goto(f"file://{ruta_temp}", wait_until="networkidle")
                page.wait_for_timeout(1500) # Tiempo para inyectar CSS y webfonts
                
                captura_full = os.path.join(out_dir, f"{nombre_proyecto}_{nombre_seguro}_full.png")
                
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(500)
                page.evaluate("window.scrollTo(0, 0)")
                
                page.screenshot(path=captura_full, full_page=True)
                print(f"📸 Captura guardada: {captura_full}")
                
            browser.close()
            print(f"\n✅ Proceso completado.")
            print(f"📂 Revisa la carpeta '{out_dir}' para ver tus capturas y el reporte Markdown.")

    except Exception as e:
        print(f"❌ Error crítico en Playwright: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEEPLENS PRO - Auditoría Visual y Mockups Inteligentes")
    parser.add_argument("--path", required=True, help="Ruta absoluta o relativa del proyecto a analizar")
    parser.add_argument("--out", default=".", help="Directorio de salida para imágenes y reporte Markdown")
    
    args = parser.parse_args()
    
    print("="*60)
    print(" DEEPLENS PRO - Extractor Multi-Pantalla IA")
    print("="*60)
    
    tomar_capturas(args.path, args.out)
