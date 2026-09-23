import time
import requests
import os
import csv
import datetime
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN DE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8952217848:AAENS7u1_BhK82-0iVd8KtGCdpFdebgEqHE"
URL_TELEGRAM = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ==========================================
# CREAR CARPETAS Y ARCHIVOS DE AUDITORÍA
# ==========================================
if not os.path.exists("Tickets_Alcaldia"):
    os.makedirs("Tickets_Alcaldia")

ARCHIVO_CSV = "auditoria_chats.csv"
if not os.path.exists(ARCHIVO_CSV):
    with open(ARCHIVO_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Fecha", "Nombre_Usuario", "Chat_ID", "Mensaje_Usuario", "Respuesta_IA"])

def guardar_auditoria(nombre, chat_id, mensaje, respuesta):
    with open(ARCHIVO_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nombre, chat_id, mensaje, respuesta])

def generar_ticket_local(nombre, problema):
    ticket_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    ruta = f"Tickets_Alcaldia/Ticket_{ticket_id}.txt"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("=== TICKET DE SOPORTE TÉCNICO - ALCALDÍA ===\n")
        f.write(f"ID TICKET: {ticket_id}\n")
        f.write(f"FECHA: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"USUARIO AFECTADO: {nombre}\n")
        f.write(f"PROBLEMA REPORTADO:\n{problema}\n\n")
        f.write("ESTADO: Pendiente de revisión por un técnico humano.\n")
    return ticket_id

# ==========================================
# CONFIGURACIÓN DE IA (GEMINI)
# ==========================================
API_KEY = "AQ.Ab8RN6JLqD9BVaeMUsXKdA-LNuxs662VX69dobMrmAq86txGYw"
client = genai.Client(api_key=API_KEY)

# PROMPT TOTALMENTE ESTRICTO PARA EVITAR SALUDOS Y SER RÁPIDO
SYSTEM_PROMPT = """
Eres el Asistente de Soporte Técnico de la Alcaldía de Villanueva, La Guajira.

REGLAS ESTRICTAS DE RESPUESTA (OBLIGATORIO):
1. PROHIBIDO SALUDAR. Bajo ninguna circunstancia uses las palabras "Bienvenido", "Hola", o "Te saluda". Empieza a dar la solución o respuesta en la primera letra.
2. SÉ CLARO Y CONCISO. Da respuestas completas pero sin rodeos. Da los pasos técnicos exactos cuando sea necesario.
3. AHORA PUEDES ESCUCHAR AUDIOS Y VER IMÁGENES. Si te mandan un audio o imagen quejándose, responde directo al problema.
4. SISTEMA DE TICKETS: Si el problema es físico o muy complejo, o si te escriben "Necesito un técnico presencial", incluye EXACTAMENTE esta palabra secreta al final: [CREAR_TICKET].
"""

def cargar_configuracion():
    try:
        with open("base_de_datos.txt", "r", encoding="utf-8") as f:
            datos_manuales = f.read()
    except Exception:
        datos_manuales = ""
    try:
        with open("datos_web.txt", "r", encoding="utf-8") as f:
            datos_web = f.read()
    except Exception:
        datos_web = ""

    prompt_final = SYSTEM_PROMPT + "\n\nDATOS:\n" + datos_manuales + "\n" + datos_web
    
    return types.GenerateContentConfig(system_instruction=prompt_final, temperature=0.5)

sesiones_chat = {}

def enviar_accion_escribiendo(chat_id):
    try:
        requests.post(f"{URL_TELEGRAM}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
    except Exception:
        pass

def enviar_mensaje_telegram(chat_id, texto, reply_markup=None):
    payload = {"chat_id": chat_id, "text": texto}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{URL_TELEGRAM}/sendMessage", json=payload)
    except Exception as e:
        print("Error enviando a Telegram:", e)

def obtener_respuesta_ia(chat_id, mensaje_o_lista):
    if isinstance(mensaje_o_lista, str):
        texto_limpio = mensaje_o_lista.strip().lower()
        if texto_limpio == "/actualizar" or texto_limpio == "actualizar":
            sesiones_chat.pop(chat_id, None)
            return "✅ Memoria limpia y actualizada."

    if chat_id not in sesiones_chat:
        config = cargar_configuracion()
        sesiones_chat[chat_id] = client.chats.create(model="gemini-3.6-flash", config=config)
    
    # Sistema de reintentos para evitar el mensaje de saturación al usuario
    for intento in range(3):
        try:
            chat = sesiones_chat[chat_id]
            respuesta = chat.send_message(mensaje_o_lista)
            return respuesta.text.strip()
        except Exception as e:
            print(f"[!] Error Gemini (Intento {intento+1}): {e}")
            time.sleep(2) # Esperar 2 segundos antes de reintentar
            
    return "⚠️ *El servidor central está procesando demasiadas solicitudes.* Por favor, intenta de nuevo en 10 segundos."

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Bot de la Alcaldia Funcionando Perfectamente OK!")
    
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

# ==========================================
# BUCLE PRINCIPAL DEL SERVIDOR
# ==========================================
def main():
    # Iniciar el servidor web falso para engañar a Render.com y que sea GRATIS
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    print("="*60)
    print("🚀 SERVIDOR CON MENÚ INTERACTIVO Y BOTONES INICIADO")
    print("="*60)
    
    offset = 0
    while True:
        try:
            response = requests.get(f"{URL_TELEGRAM}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        nombre = msg["from"].get("first_name", "Usuario")
                        
                        texto_usuario = msg.get("text", "")
                        media_part = None
                        
                        # Manejar comandos y botones de selección primero
                        texto_limpio = texto_usuario.strip()
                        if texto_limpio == "/start":
                            sesiones_chat.pop(chat_id, None) # Reiniciar sesión
                            teclado = {
                                "keyboard": [
                                    [{"text": "🏢 Funcionario / Contratista"}], 
                                    [{"text": "🏘️ Ciudadano"}]
                                ],
                                "resize_keyboard": True,
                                "one_time_keyboard": True
                            }
                            msj = f"¡Hola {nombre}! Bienvenido al Asistente Virtual de la Alcaldía de Villanueva.\n\nPor favor, indícame tu perfil seleccionando uno de los botones abajo 👇:"
                            enviar_mensaje_telegram(chat_id, msj, reply_markup=teclado)
                            continue
                            
                        elif texto_limpio == "🏢 Funcionario / Contratista":
                            teclado = {
                                "keyboard": [
                                    [{"text": "💻 Mi equipo no prende"}, {"text": "🖨️ La impresora no funciona"}],
                                    [{"text": "🌐 No hay internet"}, {"text": "🎫 Necesito un técnico presencial"}]
                                ],
                                "resize_keyboard": True,
                                "one_time_keyboard": True
                            }
                            msj = "¡Excelente, compañero de la Alcaldía! 🏢\n\n¿En qué te puedo ayudar el día de hoy? Selecciona una de las opciones rápidas o escríbeme tu problema:"
                            enviar_mensaje_telegram(chat_id, msj, reply_markup=teclado)
                            continue
                            
                        elif texto_limpio == "🏘️ Ciudadano":
                            teclado = {
                                "keyboard": [
                                    [{"text": "📝 ¿Cómo radicar una PQRS?"}, {"text": "📅 Horarios de atención"}],
                                    [{"text": "📰 ¿Cuáles son las últimas noticias?"}]
                                ],
                                "resize_keyboard": True,
                                "one_time_keyboard": True
                            }
                            msj = "¡Bienvenido, ciudadano! 🏘️\n\n¿Qué trámite o consulta deseas realizar hoy? Selecciona una opción o escríbeme tu pregunta:"
                            enviar_mensaje_telegram(chat_id, msj, reply_markup=teclado)
                            continue
                        
                        # 1. VERIFICAR SI HAY IMAGEN
                        if "photo" in msg:
                            photo = msg["photo"][-1]
                            file_id = photo["file_id"]
                            texto_usuario = msg.get("caption", "[Envió una imagen sin texto]")
                            print(f"\n[Telegram - IMAGEN] de {nombre}")
                            
                            file_info = requests.get(f"{URL_TELEGRAM}/getFile?file_id={file_id}").json()
                            img_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info['result']['file_path']}"
                            img_bytes = requests.get(img_url).content
                            media_part = Image.open(BytesIO(img_bytes))
                            
                        # 2. VERIFICAR SI HAY NOTA DE VOZ (AUDIO)
                        elif "voice" in msg:
                            file_id = msg["voice"]["file_id"]
                            texto_usuario = "[Envió una nota de voz]"
                            print(f"\n[Telegram - AUDIO] de {nombre}")
                            
                            file_info = requests.get(f"{URL_TELEGRAM}/getFile?file_id={file_id}").json()
                            audio_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info['result']['file_path']}"
                            audio_bytes = requests.get(audio_url).content
                            media_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
                        
                        # Si hay texto, imagen o audio, y NO es un comando de menú, lo pasamos a la IA
                        if texto_usuario != "" or media_part:
                            if "voice" not in msg and "photo" not in msg:
                                print(f"\n[Telegram] {nombre}: {texto_usuario}")
                                
                            enviar_accion_escribiendo(chat_id)
                            
                            contenido_a_enviar = texto_usuario
                            if media_part:
                                contenido_a_enviar = [media_part, texto_usuario] if texto_usuario != "[Envió una nota de voz]" else [media_part, "Por favor, escucha este audio y responde al problema."]
                            
                            respuesta_ia = obtener_respuesta_ia(chat_id, contenido_a_enviar)
                            
                            # Para evitar que el teclado se quede para siempre, lo ocultamos después de una pregunta normal
                            ocultar_teclado = {"remove_keyboard": True}
                            
                            if "[CREAR_TICKET]" in respuesta_ia:
                                respuesta_ia = respuesta_ia.replace("[CREAR_TICKET]", "").strip()
                                ticket_id = generar_ticket_local(nombre, texto_usuario)
                                respuesta_ia += f"\n\n🎫 *TICKET #{ticket_id} GENERADO EXITOSAMENTE*"
                                print(f"*** TICKET {ticket_id} GENERADO ***")

                            enviar_mensaje_telegram(chat_id, respuesta_ia, reply_markup=ocultar_teclado)
                            print(f"-> [IA Bot]: {respuesta_ia}")
                            guardar_auditoria(nombre, chat_id, texto_usuario, respuesta_ia)

        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            print("Error general:", e)
            time.sleep(2)

if __name__ == '__main__':
    main()
