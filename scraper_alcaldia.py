import requests
from bs4 import BeautifulSoup
import datetime
import re
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Lista de las secciones más importantes basadas en el menú de tu imagen
URLS_A_ESCANEAR = [
    "https://www.villanueva-guajira.gov.co", # Inicio (Noticias y Datos)
    "https://www.villanueva-guajira.gov.co/atencion-y-servicios-a-la-ciudadania", # Trámites y servicios
    "https://www.villanueva-guajira.gov.co/transparencia", # Transparencia y contrataciones
    "https://www.villanueva-guajira.gov.co/nuestra-alcaldia", # Nosotros
    "https://www.villanueva-guajira.gov.co/nuestra-alcaldia/directorio-de-funcionarios", # Directorio
    "https://www.villanueva-guajira.gov.co/nuestra-alcaldia/directorio-institucional" # Directorio
]

def limpiar_texto(texto):
    texto = re.sub(r'\n+', '\n', texto)
    texto = re.sub(r'\s{2,}', ' ', texto)
    return texto.strip()

def extraer_datos_web():
    print("\n" + "="*50)
    print(f"[*] INICIANDO EXTRACCIÓN MASIVA - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    texto_total_extraido = ""
    
    for url in URLS_A_ESCANEAR:
        print(f"[*] Escaneando sección: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            respuesta = requests.get(url, headers=headers, timeout=15, verify=False)
            respuesta.raise_for_status()
            
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            for tag in soup(['script', 'style', 'noscript', 'meta', 'head', 'header', 'footer']):
                tag.decompose()
                
            texto = limpiar_texto(soup.get_text(separator=' '))
            # Guardamos los primeros 3000 caracteres de cada sección para no saturar la memoria
            texto_total_extraido += f"\n\n--- SECCIÓN: {url} ---\n{texto[:3000]}\n"
            
        except Exception as e:
            print(f"[!] Error al escanear {url}: {e}")
    
    # Escribir la información en nuestra base de datos local
    print("\n[*] Guardando y actualizando datos_web.txt...")
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Reescribimos el archivo para tener siempre la info más fresca (evitamos que crezca infinitamente)
    with open("datos_web.txt", "w", encoding="utf-8") as f:
        f.write(f"# BASE DE DATOS AUTOMÁTICA - ALCALDÍA DE VILLANUEVA\n")
        f.write(f"# Última actualización automática: {fecha_actual}\n")
        f.write(texto_total_extraido)
        
    print("[+] ¡Araña Web finalizada! Base de datos web actualizada con éxito.")

def auto_actualizador(horas=24):
    """Ejecuta el scraper automáticamente cada cierto tiempo"""
    while True:
        extraer_datos_web()
        print(f"[*] El robot entrará en modo reposo. Próxima actualización en {horas} horas...")
        # Esperar la cantidad de horas en segundos
        time.sleep(horas * 3600)

if __name__ == "__main__":
    # Iniciar el robot para que se actualice solo cada 24 horas
    auto_actualizador(horas=24)

