import os
import time
import requests
import re
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN IA LOCAL ---
AI_URL = "https://covalently-untasked-daphne.ngrok-free.dev/api/"
AI_USER = "jocarsa"
AI_PASS = "jocarsa"
AI_MODEL = "qwen3.5:latest"

def leer_codigo_proyecto(ruta_carpeta):
    """Lee archivos clave del proyecto para que la IA entienda la lógica."""
    contenido = ""
    archivos_clave = ['index.php', 'main.py', 'README.md', 'informe.txt']
    
    for root, dirs, files in os.walk(ruta_carpeta):
        for file in files:
            if file in archivos_clave or file.endswith('.php') or file.endswith('.html'):
                ruta_archivo = os.path.join(root, file)
                try:
                    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
                        contenido += f"\n--- Archivo: {file} ---\n"
                        contenido += "".join(f.readlines()[:300]) 
                except Exception:
                    pass
        break  # Solo primer nivel
        
    return contenido

def generar_mockup_html(codigo_fuente):
    """Pide a la IA que traduzca la lógica backend a un HTML estático visual."""
    print("🧠 Pidiendo a la IA local que diseñe un mockup HTML/CSS del interior del proyecto...")
    
    system_prompt = "Eres un desarrollador Frontend y UI/UX experto B2B."
    prompt = f"""
    Basándote en este código o lógica de aplicación backend, genera un ÚNICO archivo HTML5 completo (con CSS integrado en la etiqueta <style>) que simule visualmente la interfaz principal (Dashboard) de este software.
    
    REGLAS ESTRICTAS:
    1. NO hagas pantallas de login. Muestra la aplicación "por dentro" funcionando, con datos de ejemplo (mock data) realistas.
    2. Diseño corporativo, limpio, moderno (dashboard tech, tablas, gráficos simulados con CSS, barra lateral).
    3. Cero dependencias externas complejas o de backend. Todo estático. Si usas CDNs (Tailwind/Bootstrap), asegúrate de que sean enlaces válidos.
    4. Devuelve EXCLUSIVAMENTE el código HTML válido empezando por <!DOCTYPE html>. Sin explicaciones previas ni posteriores.
    5. OBLIGATORIO - TAMAÑO VERTICAL: La página DEBE ser muy larga. Añade múltiples secciones apiladas verticalmente, tablas con al menos 20 filas de datos de ejemplo y varios widgets para forzar que el navegador necesite hacer scroll hacia abajo.
    
    CÓDIGO DE CONTEXTO DEL PROYECTO:
    {codigo_fuente[:4000]}
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
        res = requests.post(AI_URL, json=payload, timeout=120)
        res.raise_for_status()
        
        try:
            datos = res.json()
            html_bruto = datos.get("answer", "")
        except:
            html_bruto = res.text
        
        # EXTRACCIÓN QUIRÚRGICA: Ignoramos si la IA habla antes o después del código
        match = re.search(r'(<!DOCTYPE html>.*?</html>|<html.*?</html>)', html_bruto, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            # Plan B: limpieza agresiva de sintaxis Markdown
            html_limpio = re.sub(r'```(?:html)?', '', html_bruto, flags=re.IGNORECASE).strip()
            return html_limpio
            
    except Exception as e:
        print(f"❌ Error al generar el diseño con la IA: {e}")
        return None

def tomar_capturas(ruta_carpeta):
    if not os.path.isdir(ruta_carpeta):
        print(f"❌ Error: El directorio {ruta_carpeta} no existe.")
        return

    codigo = leer_codigo_proyecto(ruta_carpeta)
    if not codigo:
        print("❌ No se encontró código fuente para analizar en esa carpeta.")
        return
        
    html_mockup = generar_mockup_html(codigo)
    if not html_mockup or "<html" not in html_mockup.lower():
        print("❌ La IA no devolvió un HTML estructuralmente válido.")
        return
        
    ruta_temp = os.path.abspath("temp_mockup.html")
    with open(ruta_temp, "w", encoding="utf-8") as f:
        f.write(html_mockup)
        
    print(f"⚙️ Interfaz estática guardada en: {ruta_temp}")

    try:
        with sync_playwright() as p:
            print("🚀 Lanzando motor Chromium...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            page = context.new_page()
            
            url_local = f"file://{ruta_temp}"
            print(f"🌐 Renderizando mockup interno en Playwright...")
            
            page.goto(url_local, wait_until="networkidle")
            
            # Margen táctico para que los CDNs externos carguen
            print("⏳ Dando tiempo extra para carga de estilos externos (Tailwind/Bootstrap)...")
            page.wait_for_timeout(3500)
            
            nombre_proyecto = os.path.basename(os.path.normpath(ruta_carpeta))
            captura_hero = f"{nombre_proyecto}_dashboard.png"
            captura_full = f"{nombre_proyecto}_dashboard_full.png"
            
            print("📸 Capturando vista inicial del Dashboard...")
            page.screenshot(path=captura_hero)
            
            print("📸 Forzando cálculo de altura para captura completa...")
            # Nos aseguramos de ir hasta abajo y esperar a que cualquier lazy load renderice
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            page.screenshot(path=captura_full, full_page=True)
            
            browser.close()
            print(f"\n✅ Proceso completado con éxito. Imágenes generadas:\n - {captura_hero}\n - {captura_full}")
            print("🔍 NOTA: Revisa 'temp_mockup.html' en tu navegador si quieres auditar la estructura generada.")

    except Exception as e:
        print(f"❌ Error crítico de Playwright durante la captura: {e}")

if __name__ == "__main__":
    print("="*50)
    print(" DEEPLENS - Renderizado IA + Capturas (Playwright)")
    print("="*50)
    
    ruta_input = input("Introduce la ruta absoluta del proyecto PHP/Python:\n> ").strip()
    ruta_input = ruta_input.strip('"').strip("'")
    
    tomar_capturas(ruta_input)
