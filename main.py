import os
import time
import requests
import re
import json
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN IA LOCAL ---
AI_URL = "https://covalently-untasked-daphne.ngrok-free.dev/api/"
AI_USER = "jocarsa"
AI_PASS = "jocarsa"
AI_MODEL = "qwen3.5:latest"

def leer_codigo_proyecto(ruta_carpeta):
    contenido = ""
    archivos_clave = ['index.php', 'main.py', 'README.md', 'informe.txt', 'header.php', 'menu.php']
    
    for root, dirs, files in os.walk(ruta_carpeta):
        for file in files:
            if file in archivos_clave or file.endswith('.php') or file.endswith('.html'):
                ruta_archivo = os.path.join(root, file)
                try:
                    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
                        contenido += f"\n--- Archivo: {file} ---\n"
                        contenido += "".join(f.readlines()[:400]) 
                except Exception:
                    pass
        break 
        
    return contenido

def generar_mockups_json(codigo_fuente):
    print("🧠 Analizando código para extraer múltiples pantallas en formato JSON...")
    
    system_prompt = "Eres un analizador de código estricto. Tu única función es transcribir lógica backend a HTML estático."
    
    # Prompt ajustado para evitar que escupa código PHP en la interfaz visual
    prompt = f"""
    Analiza este código backend y detecta cuántas pantallas o vistas diferentes tiene la aplicación.
    
    REGLAS ESTRICTAS E INQUEBRANTABLES:
    1. NO INVENTES FUNCIONALIDADES NUEVAS. Pero DEBES interpretar la lógica (bucles, arrays, variables) y traducirla a elementos visuales HTML. 
    2. Genera un archivo HTML5 completo (con CSS incrustado) para CADA pantalla detectada.
    3. FORMATO DE SALIDA OBLIGATORIO: Devuelve ÚNICAMENTE un objeto JSON válido. 
       - Claves: nombre de la pantalla.
       - Valores: código HTML completo en formato string.
    4. PROHIBIDO escribir texto fuera de la estructura JSON.
    5. PROHIBICIÓN CRÍTICA: BAJO NINGÚN CONCEPTO debes imprimir sintaxis de backend cruda (como tags <?php ?>, bucles foreach, corchetes de arrays o variables $) en la pantalla visible. Transforma esos datos en texto normal o inputs de formulario (radios, selects, tablas).

    CÓDIGO DE CONTEXTO:
    {codigo_fuente[:5000]}
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
        res = requests.post(AI_URL, json=payload, timeout=180)
        res.raise_for_status()
        
        datos = res.json() if "application/json" in res.headers.get("Content-Type", "") else res.text
        if isinstance(datos, dict) and "answer" in datos:
            respuesta_cruda = datos["answer"]
        else:
            respuesta_cruda = res.text
            
        match = re.search(r'\{.*\}', respuesta_cruda, re.IGNORECASE | re.DOTALL)
        if match:
            str_json = match.group(0)
            return json.loads(str_json)
        else:
            print("❌ La IA no devolvió un formato JSON reconocible.")
            with open("error_ia_crudo.txt", "w", encoding="utf-8") as f:
                f.write(respuesta_cruda)
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ La IA devolvió un JSON mal formado: {e}")
        with open("error_json_roto.txt", "w", encoding="utf-8") as f:
            f.write(respuesta_cruda)
        return None
    except Exception as e:
        print(f"❌ Error de conexión o timeout con la IA: {e}")
        return None

def tomar_capturas(ruta_carpeta):
    if not os.path.isdir(ruta_carpeta):
        print(f"❌ Error: El directorio {ruta_carpeta} no existe.")
        return

    codigo = leer_codigo_proyecto(ruta_carpeta)
    if not codigo:
        print("❌ No se encontró código en esa carpeta.")
        return
        
    diccionario_pantallas = generar_mockups_json(codigo)
    
    if not diccionario_pantallas:
        print("❌ Abortando: No se pudieron parsear las pantallas.")
        return
        
    print(f"🎯 ¡Éxito! La IA detectó {len(diccionario_pantallas)} pantallas: {list(diccionario_pantallas.keys())}")

    try:
        with sync_playwright() as p:
            print("🚀 Lanzando Chromium...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            page = context.new_page()
            
            nombre_proyecto = os.path.basename(os.path.normpath(ruta_carpeta))
            
            for nombre_pantalla, html_content in diccionario_pantallas.items():
                nombre_seguro = re.sub(r'[^a-zA-Z0-9]', '_', nombre_pantalla).lower()
                ruta_temp = os.path.abspath(f"temp_{nombre_seguro}.html")
                
                with open(ruta_temp, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                print(f"🌐 Renderizando vista: {nombre_pantalla}...")
                page.goto(f"file://{ruta_temp}", wait_until="networkidle")
                page.wait_for_timeout(2000)
                
                captura_full = f"{nombre_proyecto}_{nombre_seguro}_full.png"
                
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                page.evaluate("window.scrollTo(0, 0)")
                
                page.screenshot(path=captura_full, full_page=True)
                print(f"📸 Captura guardada: {captura_full}")
                
            browser.close()
            print("\n✅ Proceso multi-pantalla completado.")

    except Exception as e:
        print(f"❌ Error crítico en Playwright: {e}")

if __name__ == "__main__":
    print("="*60)
    print(" DEEPLENS - Extractor Multi-Pantalla (Modo Estricto JSON)")
    print("="*60)
    
    ruta_input = input("Introduce la ruta absoluta del proyecto:\n> ").strip()
    ruta_input = ruta_input.strip('"').strip("'")
    
    tomar_capturas(ruta_input)
