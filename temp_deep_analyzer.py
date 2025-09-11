# temp_deep_analyzer.py
from playwright.sync_api import sync_playwright
import time

URL = "https://www.worldwildlife.org/descubre-wwf/historias/cinco-aspectos-importantes-sobre-los-bosques-el-uso-de-suelo-y-los-objetivos-flag"
OUTPUT_FILE = "wwf-deep-analysis.html"

print(f"Iniciando ANÁLISIS PROFUNDO para: {URL}")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until='domcontentloaded', timeout=90000)
        print("Página cargada. Esperando carga inicial...")
        page.wait_for_timeout(5000)

        print("Iniciando desplazamiento para forzar carga de contenido dinámico...")
        scroll_height = page.evaluate("document.body.scrollHeight")
        for i in range(0, scroll_height, 500):
            page.evaluate(f"window.scrollTo(0, {i})")
            time.sleep(0.2)
        
        print("Desplazamiento completado. Esperando carga final...")
        page.wait_for_timeout(5000)

        html_content = page.content()
        browser.close()

    # Guardar en el directorio correcto
    with open("runa_github_pages/" + OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Análisis profundo completado. HTML guardado en: runa_github_pages/{OUTPUT_FILE}")

except Exception as e:
    print(f"Ocurrió un error durante el análisis profundo: {e}")