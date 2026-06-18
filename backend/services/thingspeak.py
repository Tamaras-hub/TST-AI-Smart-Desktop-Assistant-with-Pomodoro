import requests
import time

WRITE_API_KEY = "5TEXFSD67OHA1IER"

URL = "https://api.thingspeak.com/update"

# Control de frecuencia
ultimo_envio = 0

INTERVALO_THINGSPEAK = 15  # segundos


def enviar_a_thingspeak(datos):
    global ultimo_envio

    print("[THINGSPEAK] Intentando enviar...")

    ahora = time.time()

    if ahora - ultimo_envio < INTERVALO_THINGSPEAK:
        print("[THINGSPEAK] Esperando intervalo de 15s...")
        return

    ultimo_envio = ahora

    payload = {
        "api_key": WRITE_API_KEY,
        "field1": datos.get("temperatura", 0),
        "field2": datos.get("distancia", 0),
        "field3": datos.get("presencia", 0),
        "field4": datos.get("actuadores", {}).get("ventilador", 0),
        "field5": datos.get("actuadores", {}).get("lampara", 0),
        "field6": datos.get("actuadores", {}).get("buzzer", 0),
    }

    try:
        response = requests.post(URL, data=payload)
        print(f"[THINGSPEAK] Codigo: {response.status_code}")
        print(f"[THINGSPEAK] Respuesta: {response.text}")

    except Exception as e:
        print(f"[THINGSPEAK] Error: {e}")