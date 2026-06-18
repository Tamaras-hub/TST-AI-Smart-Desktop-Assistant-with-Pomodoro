# =============================================================================
# routes/api.py — Endpoints de la API REST
# =============================================================================

from flask import Blueprint, request, jsonify
from datetime import datetime
from services.estado import obtener_estado, actualizar_entorno, estado
from services.agente import generar_propuesta_pomodoro
from services.pomodoro import (
    iniciar_pomodoro,
    pausar_pomodoro,
    reanudar_pomodoro,
    finalizar_pomodoro,
    obtener_estado_pomodoro,
    saltar_fase,
)


import unicodedata

def eliminar_acentos(texto):
    """Elimina acentos y caracteres especiales para compatibilidad con LCD."""
    if not texto:
        return ""
    # Normalizar para separar caracteres base de sus acentos
    s = unicodedata.normalize('NFD', str(texto))
    # Filtrar solo los caracteres que NO sean acentos (Mn = Mark, Nonspacing)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

def limpiar_y_abreviar(texto, es_lcd=False):
    """Limpia guiones y resume de forma inteligente para la LCD."""
    if not texto: return ""
    
    import re
    # 1. Quitar guiones, puntos o números al inicio
    texto = re.sub(r"^[\s\-\*\d\.\)]+", "", texto).strip()
    
    if not es_lcd:
        return texto

    # --- EXTRACCIÓN INTELIGENTE DE ACCIÓN PRINCIPAL PARA LCD ---
    t_lower = texto.lower()
    
    # 1. Estiramientos (cuello, hombros, espalda, dedos)
    if "estiramiento" in t_lower or "estirar" in t_lower:
        if "cuello" in t_lower or "hombro" in t_lower:
            return "Estirar cuello/hombros"
        elif "dedo" in t_lower or "mano" in t_lower or "muñeca" in t_lower:
            return "Estirar dedos y manos"
        elif "lumbar" in t_lower or "espalda" in t_lower:
            return "Estirar la espalda"
        return "Hacer estiramientos"

    # 2. Rotaciones / Círculos
    elif "rotacion" in t_lower or "rotaci\u00f3n" in t_lower or "rotar" in t_lower or "c\u00edrculo" in t_lower or "circulo" in t_lower:
        if "cuello" in t_lower or "cabeza" in t_lower:
            return "Rotar el cuello"
        elif "hombro" in t_lower:
            return "Rotar los hombros"
        elif "tobillo" in t_lower or "pie" in t_lower:
            return "Rotar los tobillos"
        elif "mu\u00f1eca" in t_lower or "mano" in t_lower:
            return "Rotar las mu\u00f1ecas"
        return "Hacer rotaciones"

    # 3. Caminar / Paseo / Pausa activa
    elif "caminar" in t_lower or "paseo" in t_lower or "camina" in t_lower:
        return "Caminar y despejarse"

    # 3. Respiración / Relajación
    elif "respirar" in t_lower or "respiración" in t_lower:
        return "Respirar hondo y relajar"

    # 4. Masajes
    elif "masajear" in t_lower or "masaje" in t_lower:
        if "sienes" in t_lower or "sien" in t_lower:
            return "Masajear las sienes"
        elif "mano" in t_lower or "muñeca" in t_lower:
            return "Masajear las manos"
        return "Hacer un masaje suave"

    # 5. Ojos / Vista / Pantalla
    elif "ojo" in t_lower or "vista" in t_lower or "parpadear" in t_lower or "horizonte" in t_lower:
        if "parpadear" in t_lower:
            return "Parpadear despacio"
        return "Descansar los ojos"

    # 6. Música / Melodía
    elif "música" in t_lower or "melodía" in t_lower or "canción" in t_lower:
        return "Escuchar música suave"

    # 7. Lavar / Agua fría
    elif "lavar" in t_lower or "limpiar" in t_lower:
        if "cara" in t_lower:
            return "Lavar la cara"
        elif "mano" in t_lower:
            return "Lavar las manos"
        return "Lavar cara o manos"

    # 8. Cerrar ojos / Descansar / Relajar
    elif "sentarse" in t_lower or "relajar" in t_lower or "cerrar" in t_lower:
        return "Cerrar ojos y descansar"

    # Fallback si no coincide con ninguna categoría (Limpieza clásica mejorada)
    res = re.sub(r"^(realizar|hacer|tomar|dar|una?|el|la|los|las|serie\s+de|ejercicios\s+de)\s+", "", texto, flags=re.IGNORECASE)

    # Cortar tras conectores largos (incluyendo "por X" al final)
    for patron in [r"\s+para\s+.*", r"\s+por\s+.*", r"\s+con\s+el\s+fin\s+.*", r"\s+y\s+mejorar\s+.*", r"\s+con\s+el\s+objetivo\s+.*"]:
        res = re.sub(patron, "", res, flags=re.IGNORECASE)

    res = res.strip()

    # Recortar por palabras completas (nunca cortar a mitad de palabra)
    if len(res) > 24:
        palabras = res.split()
        while palabras and len(" ".join(palabras)) > 24:
            palabras.pop()
        res = " ".join(palabras)

    # SANITIZADOR FINAL: quitar preposiciones/artículos sueltos al final
    CONECTORES = {"de", "del", "con", "para", "a", "al", "el", "la", "los",
                  "las", "un", "una", "unos", "unas", "y", "o", "e", "u", "por"}
    palabras = res.split()
    while palabras and palabras[-1].lower().rstrip(".,;:") in CONECTORES:
        palabras.pop()
    res = " ".join(palabras)

    if not res: return "Descanso Activo"
    return res[0].upper() + res[1:]

api_blueprint = Blueprint('api', __name__)


# =============================================================================
# SISTEMA
# =============================================================================

@api_blueprint.route('/status', methods=['GET'])
def obtener_status():
    """GET /api/status — Estado global completo."""
    return jsonify(obtener_estado())


@api_blueprint.route('/health', methods=['GET'])
def health_check():
    """GET /api/health — Verifica que el servidor esté vivo."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# =============================================================================
# IoT
# =============================================================================

@api_blueprint.route('/iot/registro', methods=['POST'])
def registrar_datos_iot():
    """
    POST /api/iot/registro — Recibe datos del ESP32.

    Body:
    {
        "temperatura": 31.2,
        "distancia": 25,
        "presencia": 1,
        "actuadores": { "ventilador": 1, "lampara": 1, "buzzer": 0 }
    }
    """
    datos = request.json
    if datos is None:
        return jsonify({"status": "error", "mensaje": "Se requiere Content-Type: application/json"}), 400

    actualizar_entorno(datos)
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# =============================================================================
# POMODORO
#
# Las rutas solo manejan HTTP (validar body, construir respuesta).
# Toda la lógica de estados vive en services/pomodoro.py.
# =============================================================================

@api_blueprint.route('/pomodoro/start', methods=['POST'])
def pomodoro_start():
    """
    POST /api/pomodoro/start — Inicia sesión de trabajo.
    Transición: cualquier estado → TRABAJANDO

    Body:
    {
        "tarea": "Estudiar Flask",
        "duracion": 25          ← opcional, default 25 min
    }
    """
    datos    = request.json or {}
    tarea    = datos.get("tarea", "").strip()
    duracion = datos.get("duracion", 25)
    descanso = datos.get("descanso", 5)
    recoms   = datos.get("recomendaciones")

    if not tarea:
        return jsonify({"status": "error", "mensaje": "El campo 'tarea' es obligatorio"}), 400

    if recoms is None or (isinstance(recoms, list) and len(recoms) == 0):
        try:
            logger.info("[API] No se enviaron recomendaciones. Generando nuevas para: %s", tarea)
            tarea_obj = [{"id": "manual", "nombre": tarea, "dificultad": 3, "concentracion": 3}]
            propuesta = generar_propuesta_pomodoro(tarea_obj)
            recoms = [limpiar_y_abreviar(r) for r in propuesta.get("actividades_descanso", [])]
            recoms_corto = [limpiar_y_abreviar(r, es_lcd=True) for r in propuesta.get("actividades_descanso_corto", [])]
        except Exception as e:
            logger.error("[API] Error regenerando recoms: %s", e)
            recoms = estado["sistema"]["recomendaciones_descanso"]
            recoms_corto = estado["sistema"]["recomendaciones_descanso_corto"]
    else:
        # Si vienen de la web, limpiamos guiones (aquí simplificamos y generamos la corta)
        recoms = [limpiar_y_abreviar(r) for r in recoms]
        recoms_corto = [limpiar_y_abreviar(r, es_lcd=True) for r in recoms]

    # Guardar en estado global
    estado["sistema"]["recomendaciones_descanso"] = recoms
    estado["sistema"]["recomendaciones_descanso_corto"] = recoms_corto

    iniciar_pomodoro(tarea, duracion, descanso, recoms)

    return jsonify({
        "status":  "ok",
        "mensaje": f"Pomodoro iniciado: '{tarea}'",
        "estado":  obtener_estado_pomodoro()
    })


@api_blueprint.route('/pomodoro/pause', methods=['POST'])
def pomodoro_pause():
    """
    POST /api/pomodoro/pause — Pausa el temporizador.
    Transición: TRABAJANDO → PAUSADO

    No requiere body.
    Error 400 si el modo actual no es TRABAJANDO.
    """
    resultado = pausar_pomodoro()

    if not resultado["ok"]:
        return jsonify({"status": "error", "mensaje": resultado["error"]}), 400

    return jsonify({
        "status":  "ok",
        "mensaje": "Pomodoro pausado",
        "estado":  obtener_estado_pomodoro()
    })


@api_blueprint.route('/pomodoro/resume', methods=['POST'])
def pomodoro_resume():
    """
    POST /api/pomodoro/resume — Reanuda desde pausa.
    Transición: PAUSADO → TRABAJANDO

    No requiere body.
    Error 400 si el modo actual no es PAUSADO.
    """
    resultado = reanudar_pomodoro()

    if not resultado["ok"]:
        return jsonify({"status": "error", "mensaje": resultado["error"]}), 400

    return jsonify({
        "status":  "ok",
        "mensaje": "Pomodoro reanudado",
        "estado":  obtener_estado_pomodoro()
    })


@api_blueprint.route('/pomodoro/finish', methods=['POST'])
def pomodoro_finish():
    """
    POST /api/pomodoro/finish — Finaliza manualmente y vuelve a IDLE.
    Transición: TRABAJANDO | PAUSADO | DESCANSO → IDLE

    No requiere body.
    """
    finalizar_pomodoro()

    return jsonify({
        "status":  "ok",
        "mensaje": "Sesión finalizada, volviendo a IDLE",
        "estado":  obtener_estado_pomodoro()
    })



@api_blueprint.route('/pomodoro/status', methods=['GET'])
def pomodoro_status():
    """
    GET /api/pomodoro/status — Estado actual del Pomodoro.

    La ESP32 llama a este endpoint cada N segundos.
    Calcula tiempo_restante en vivo y dispara transiciones automáticas:
      TRABAJANDO (t=0) → DESCANSO
      DESCANSO   (t=0) → IDLE

    Respuesta:
    {
        "modo":            "TRABAJANDO",
        "tarea_actual":    "Estudiar Flask",
        "tiempo_restante": 1243,
        "duracion_total":  1500
    }
    """
    pom = obtener_estado_pomodoro()
    pom["entorno"] = estado["entorno"]
    return jsonify(pom)

@api_blueprint.route("/pomodoro/skip", methods=["POST"])
def skip_phase():
    resultado = saltar_fase()
    return jsonify(resultado)

# =============================================================================
# AGENTE IA — Planificación Pomodoro con Llama
# =============================================================================

@api_blueprint.route("/ia/propuesta", methods=["POST"])
def ia_propuesta():
    """
    POST /api/ia/propuesta — Genera una planificación Pomodoro con IA.

    Body esperado:
    {
        "tareas": [
            { "id": "t1", "nombre": "Tarea A", "dificultad": 4, "concentracion": 3 },
            ...
        ]
    }

    Respuesta exitosa:
    {
        "ok": true,
        "propuesta": {
            "tareas_priorizadas": [...],
            "tarea_id": "t1",
            "tarea_nombre": "Tarea A",
            "minutos_trabajo": 25,
            "minutos_descanso": 5,
            "actividades_descanso": ["...", "...", "..."],
            "tipo_descanso": "relajacion",
            "mensaje": "..."
        }
    }
    """
    import logging
    logger = logging.getLogger("agente")

    data = request.get_json(silent=True) or {}
    tareas = data.get("tareas", [])
    fecha_actual = data.get("fecha_actual")

    # --- Validación básica ---
    if not tareas:
        logger.warning("[API /ia/propuesta] Petición sin tareas.")
        return jsonify({
            "ok": False,
            "error": "Debes enviar al menos una tarea en el campo 'tareas'."
        }), 400

    if not isinstance(tareas, list):
        return jsonify({
            "ok": False,
            "error": "El campo 'tareas' debe ser una lista."
        }), 400

    # Validar estructura mínima de cada tarea
    for i, t in enumerate(tareas):
        if not isinstance(t, dict):
            return jsonify({
                "ok": False,
                "error": f"La tarea en posición {i} no es un objeto válido."
            }), 400
        if not t.get("id") or not t.get("nombre"):
            return jsonify({
                "ok": False,
                "error": f"La tarea en posición {i} debe tener 'id' y 'nombre'."
            }), 400

    # --- Llamada al agente ---
    try:
        logger.info("[API /ia/propuesta] Procesando %d tarea(s)...", len(tareas))

        propuesta = generar_propuesta_pomodoro(tareas, hoy_date=fecha_actual)

        logger.info(
            "[API /ia/propuesta] ✅ Propuesta generada para tarea '%s'.",
            propuesta.get("tarea_nombre", "?")
        )

        # Guardar recomendaciones para el ESP32 (sin guiones)
        recoms_limpias = [limpiar_y_abreviar(r) for r in propuesta.get("actividades_descanso", [])]
        recoms_cortas = [limpiar_y_abreviar(r, es_lcd=True) for r in propuesta.get("actividades_descanso_corto", [])]
        
        estado["sistema"]["recomendaciones_descanso"] = recoms_limpias
        estado["sistema"]["recomendaciones_descanso_corto"] = recoms_cortas
        
        # También limpiamos la propuesta que va al navegador para que coincidan al 100%
        propuesta["actividades_descanso"] = recoms_limpias
        propuesta["actividades_descanso_corto"] = recoms_cortas
        propuesta["mensaje"] = eliminar_acentos(propuesta.get("mensaje", ""))
        propuesta["tarea_nombre"] = eliminar_acentos(propuesta.get("tarea_nombre", ""))
        for t_p in propuesta.get("tareas_priorizadas", []):
            t_p["tarea_nombre"] = eliminar_acentos(t_p.get("tarea_nombre", ""))
            t_p["razon"] = eliminar_acentos(t_p.get("razon", ""))

        return jsonify({
            "ok": True,
            "propuesta": propuesta
        })

    except Exception as e:
        logger.error("[API /ia/propuesta] ❌ Error inesperado: %s", e)
        return jsonify({
            "ok": False,
            "error": "No se pudo generar la propuesta. Intenta de nuevo."
        }), 500
# =============================================================================
# ESP32
# =============================================================================

# Tabla de mapeo: estado interno Flask → valores que entiende la ESP32.
# Centralizar esto aquí evita repetir la lógica si se agrega otro endpoint.
_MAPA_ESTADO = {
    #  modo Flask   accion            modo UI   mensaje TFT
    "TRABAJANDO": ("start_pomodoro", "work",   "Trabajando"),
    "DESCANSO":   ("break",          "break",  "Descansando"),
    "PAUSADO":    ("pause",          "pause",  "En pausa"),
    "IDLE":       ("idle",           "idle",   "Listo"),
}


@api_blueprint.route('/esp32/status', methods=['GET'])
def esp32_status():
    """
    GET /api/esp32/status — Respuesta compacta y lista para consumir en la ESP32.

    Por qué NO usar /api/status:
      - /api/status devuelve TODO el estado global (~20 campos).
      - La ESP32 solo necesita saber qué mostrar y qué hacer.
      - Parsear JSON grande en C++ consume más RAM y tiempo de CPU.
      - Este endpoint devuelve exactamente lo necesario (~8 campos).

    Cómo lo usa la ESP32:
      1. Hace GET /api/esp32/status cada N segundos (ej. cada 2s).
      2. Lee ui.modo para decidir qué pantalla mostrar en la TFT.
      3. Lee parametros.duracion para el countdown.
      4. Lee actuadores para sincronizar ventilador, lampara y buzzer.

    Respuestas por modo:

    TRABAJANDO:
    {
      "accion": "start_pomodoro",
      "parametros": { "duracion": 1243 },
      "ui": { "mensaje": "Trabajando: Estudiar Flask", "modo": "work" },
      "actuadores": { "ventilador": 1, "lampara": 1, "buzzer": 0 }
    }

    DESCANSO:
    {
      "accion": "break",
      "parametros": { "duracion": 287 },
      "ui": { "mensaje": "Descansando", "modo": "break" },
      "actuadores": { "ventilador": 0, "lampara": 1, "buzzer": 0 }
    }

    PAUSADO:
    {
      "accion": "pause",
      "parametros": { "duracion": 950 },
      "ui": { "mensaje": "En pausa", "modo": "pause" },
      "actuadores": { "ventilador": 0, "lampara": 1, "buzzer": 0 }
    }

    IDLE:
    {
      "accion": "idle",
      "parametros": { "duracion": 0 },
      "ui": { "mensaje": "Listo", "modo": "idle" },
      "actuadores": { "ventilador": 0, "lampara": 0, "buzzer": 0 }
    }
    """
    # obtener_estado_pomodoro() calcula tiempo_restante en vivo y dispara
    # transiciones automáticas (TRABAJANDO→DESCANSO, DESCANSO→IDLE).
    pom = obtener_estado_pomodoro()

    modo_flask = pom["modo"]                          # ej. "TRABAJANDO"
    accion, modo_ui, mensaje_base = _MAPA_ESTADO.get(
        modo_flask, ("idle", "idle", "Listo")
    )

    # En modo trabajo añadimos el nombre de la tarea al mensaje
    if modo_flask == "TRABAJANDO" and pom["tarea_actual"]:
        mensaje = f"{mensaje_base}: {pom['tarea_actual']}"
    else:
        mensaje = mensaje_base

    return jsonify({
        "accion": accion,
        "parametros": {
            "duracion": pom["tiempo_restante"]
        },
        "ui": {
            "mensaje": eliminar_acentos(mensaje),
            "modo":    modo_ui,
            "recomendaciones": [eliminar_acentos(r) for r in estado["sistema"]["recomendaciones_descanso_corto"]]
        },
        # Datos del entorno físico, actualizados por el ESP32 vía POST /api/iot/registro.
        "entorno": {
            "temperatura": estado["entorno"]["temperatura"],
            "distancia":   estado["entorno"]["distancia"],
            "presencia":   estado["entorno"]["presencia"],
        },
        # Los actuadores se reflejan de vuelta para que la ESP32 confirme su estado.
        "actuadores": estado["entorno"]["actuadores"]
    })

