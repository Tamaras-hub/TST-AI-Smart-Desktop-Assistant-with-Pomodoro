# =============================================================================
# services/estado.py — Estado global del sistema
#
# El "estado global" es el diccionario que representa cómo está el sistema
# en todo momento. Todos los módulos importan y comparten ESTE mismo objeto
# (Python no crea copias al importar, usa la misma referencia en memoria).
# =============================================================================

# Diccionario principal. Es la "fuente de verdad" de toda la aplicación.
from services.thingspeak import enviar_a_thingspeak

estado = {
    "sistema": {
        "modo": "IDLE",          # IDLE | TRABAJANDO | DESCANSO | PAUSADO
        "tarea_actual": "",
        "tiempo_restante": 0,
        "recomendaciones_descanso": [
            "Estira tus brazos y espalda",
            "Bebe un vaso de agua",
            "Cierra los ojos por 1 minuto",
            "Mira a un punto lejano"
        ],
        "recomendaciones_descanso_corto": [
            "Estirar brazos",
            "Beber agua",
            "Cerrar ojos",
            "Mirar lejos"
        ],
        "tareas": []
    },
    "entorno": {
        "temperatura": 0,        # °C — sensor DHT11/DHT22
        "distancia": 0,          # cm — sensor HC-SR04
        "presencia": 0,          # 0 = nadie, 1 = hay alguien
        "historial_distancia": [0.0, 0.0, 0.0, 0.0, 0.0],  # Arreglo de variable de entrada (HC-SR04)
        "actuadores": {
            "ventilador": 0,     # 0 = apagado, 1 = encendido
            "lampara": 0,
            "buzzer": 0
        }
    }
}


def obtener_estado():
    """Devuelve el estado global completo."""
    return estado


def actualizar_entorno(datos_iot):
    """
    Actualiza la sección 'entorno' con los datos recibidos del ESP32.
    Usa .get(clave, valor_actual) para no romper si falta algún campo.
    """
    # Temperatura normal
    estado["entorno"]["temperatura"] = datos_iot.get("temperatura", estado["entorno"]["temperatura"])

    # Filtro de Promedio Móvil para la distancia del HC-SR04 (Arreglo de entrada)
    nueva_dist = datos_iot.get("distancia")
    if nueva_dist is not None:
        try:
            nueva_dist = float(nueva_dist)
            # Obtener el arreglo actual
            historial = estado["entorno"].get("historial_distancia", [0.0, 0.0, 0.0, 0.0, 0.0])
            if not historial:
                historial = [nueva_dist] * 5
            # Añadir nueva lectura (desplazamiento de buffer)
            historial.append(nueva_dist)
            if len(historial) > 5:
                historial.pop(0)
            
            estado["entorno"]["historial_distancia"] = historial
            # La distancia real filtrada será el promedio móvil de nuestro arreglo de entrada
            estado["entorno"]["distancia"] = round(sum(historial) / len(historial), 1)
        except (ValueError, TypeError):
            pass

    estado["entorno"]["presencia"]   = datos_iot.get("presencia",   estado["entorno"]["presencia"])

    if "actuadores" in datos_iot:
        act = datos_iot["actuadores"]
        estado["entorno"]["actuadores"]["ventilador"] = act.get("ventilador", estado["entorno"]["actuadores"]["ventilador"])
        estado["entorno"]["actuadores"]["lampara"]    = act.get("lampara",    estado["entorno"]["actuadores"]["lampara"])
        estado["entorno"]["actuadores"]["buzzer"]     = act.get("buzzer",     estado["entorno"]["actuadores"]["buzzer"])

    print(f"[ESTADO] temp={estado['entorno']['temperatura']}°C  "
          f"dist={estado['entorno']['distancia']}cm (Historial Arreglo Distancia={estado['entorno']['historial_distancia']})  "
          f"presencia={estado['entorno']['presencia']}")
    
    enviar_a_thingspeak(estado["entorno"])


def cambiar_modo(nuevo_modo):
    """Cambia el modo del sistema. Valida que sea un modo conocido."""
    modos_validos = ["IDLE", "TRABAJANDO", "DESCANSO", "PAUSADO"]
    if nuevo_modo in modos_validos:
        estado["sistema"]["modo"] = nuevo_modo
        print(f"[ESTADO] Modo → {nuevo_modo}")
    else:
        print(f"[ESTADO] Modo inválido: '{nuevo_modo}'. Opciones: {modos_validos}")
