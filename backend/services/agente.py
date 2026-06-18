# =============================================================================
# services/agente.py — Agente inteligente Pomodoro con Groq
# =============================================================================
#
# Flujo:
#   1. generar_propuesta_pomodoro(tareas) es llamado desde routes/api.py
#   2. Construye un prompt detallado con las tareas recibidas
#   3. Llama a Groq con el modelo LLaMA 3 70B
#   4. Si Groq falla (cuota, timeout, JSON inválido), usa propuesta_local()
#   5. Siempre devuelve el mismo formato JSON esperado por el frontend
#
# API key requerida en .env:
#   GROQ_API_KEY=gsk_...
#
# Formato de respuesta garantizado:
# {
#   "tareas_priorizadas": [...],
#   "tarea_id": "...",
#   "tarea_nombre": "...",
#   "minutos_trabajo": 25,
#   "minutos_descanso": 5,
#   "actividades_descanso": ["...", "...", "..."],
#   "tipo_descanso": "relajacion",
#   "mensaje": "..."
# }
# =============================================================================

import os
import json
import re
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logger
logger = logging.getLogger("agente")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

# -----------------------------------------------------------------------------
# Configuración de Groq vía HTTP Directo
# -----------------------------------------------------------------------------
API_KEY = os.getenv("GROQ_API_KEY", "").strip()
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODELO = "llama-3.3-70b-versatile"

if not API_KEY:
    logger.warning("GROQ_API_KEY no configurada. Se usará fallback local.")
else:
    logger.info("Configuración de Groq API lista para peticiones directas.")


# =============================================================================
# Utilidades
# =============================================================================

def _limpiar_json(texto: str) -> str:
    """
    Limpia la respuesta del LLM eliminando bloques Markdown y texto extra.
    Los modelos a veces incluyen ```json ... ``` aunque se les pida no hacerlo.
    Extrae el primer objeto JSON válido que encuentre en el texto.
    """
    texto = texto.strip()

    # Eliminar bloques markdown ```json ... ``` o ``` ... ```
    texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s*```$", "", texto)
    texto = texto.strip()

    # Extraer el primer objeto JSON completo si hay texto alrededor
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        return match.group(0)

    return texto


def _validar_propuesta(propuesta: dict, tareas: list) -> dict:
    """
    Valida y corrige la propuesta devuelta por el LLM para garantizar
    que cumple todas las restricciones antes de enviarla al frontend.
    """
    ids_validos = {t["id"] for t in tareas}

    # Validar tarea_id — si no coincide con ninguna tarea real, usar la de mayor prioridad
    if propuesta.get("tarea_id") not in ids_validos:
        tarea_fallback = _tarea_mayor_prioridad(tareas)
        propuesta["tarea_id"] = tarea_fallback["id"]
        propuesta["tarea_nombre"] = tarea_fallback["nombre"]
        logger.warning(
            "[VALIDACIÓN] tarea_id inválido — corregido a '%s'.",
            tarea_fallback["nombre"]
        )

    # Validar minutos_trabajo (entre 15 y 50)
    mt = propuesta.get("minutos_trabajo", 25)
    if not isinstance(mt, int) or mt < 15 or mt > 50:
        propuesta["minutos_trabajo"] = 25
        logger.warning("[VALIDACIÓN] minutos_trabajo fuera de rango — corregido a 25.")

    # Validar minutos_descanso (entre 5 y 15)
    md = propuesta.get("minutos_descanso", 5)
    if not isinstance(md, int) or md < 5 or md > 15:
        propuesta["minutos_descanso"] = 5
        logger.warning("[VALIDACIÓN] minutos_descanso fuera de rango — corregido a 5.")

    # Validar actividades_descanso (debe ser lista con al menos 1 ítem)
    act = propuesta.get("actividades_descanso", [])
    if not isinstance(act, list) or len(act) == 0:
        propuesta["actividades_descanso"] = [
            "Tomar un vaso de agua",
            "Estirar suavemente",
            "Respirar profundo"
        ]

    # Validar tipo_descanso
    tipos_validos = {"activo", "relajacion", "social", "creativo"}
    if propuesta.get("tipo_descanso") not in tipos_validos:
        propuesta["tipo_descanso"] = "relajacion"

    # Garantizar campo mensaje
    if not propuesta.get("mensaje"):
        propuesta["mensaje"] = "Planificación generada automáticamente."

    # Garantizar tareas_priorizadas (si el LLM no la generó, crearla localmente)
    if not isinstance(propuesta.get("tareas_priorizadas"), list):
        propuesta["tareas_priorizadas"] = _priorizar_tareas_local(tareas)

    return propuesta


# =============================================================================
# Lógica local de priorización (usada por el fallback y por la validación)
# =============================================================================

def _calcular_dias_restantes(fecha_str: str, hoy_date=None) -> int:
    if not fecha_str:
        return 999
    try:
        fecha_entrega = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        if hoy_date is None:
            hoy_date = datetime.now().date()
        elif isinstance(hoy_date, str):
            hoy_date = datetime.strptime(hoy_date, "%Y-%m-%d").date()
        return (fecha_entrega - hoy_date).days
    except Exception:
        return 999


def _calcular_puntaje_prioridad(t: dict, hoy_date=None) -> float:
    dif = int(t.get("dificultad", 3))
    con = int(t.get("concentracion", 3))
    fecha_str = t.get("fecha_entrega") or t.get("fechaEntrega") or ""
    
    dias = _calcular_dias_restantes(fecha_str, hoy_date)
    puntaje = dif + con
    
    if not fecha_str:
        return puntaje

    # La prioridad de las tareas se basa fuertemente en la fecha de entrega
    # Entre más cerca esté la fecha de entrega, más prioridad tiene.
    if dias <= 0:
        # Vencida o para hoy: máxima prioridad absoluta
        bonus = 100 - dias
    else:
        # Tareas futuras: entre más cerca, mayor bonus (ej: 1 día restante = 79 bonus, 5 días restante = 75 bonus)
        bonus = max(0, 80 - dias)
        
    return puntaje + bonus


def _tarea_mayor_prioridad(tareas: list, hoy_date=None) -> dict:
    """
    Retorna la tarea con mayor puntaje de prioridad calculando dificultad,
    concentración y cercanía de fecha de entrega.
    """
    return sorted(
        tareas,
        key=lambda t: _calcular_puntaje_prioridad(t, hoy_date),
        reverse=True
    )[0]


def _priorizar_tareas_local(tareas: list, hoy_date=None) -> list:
    """
    Ordena las tareas por prioridad: puntaje considerando dificultad,
    concentración y fecha de entrega. Genera razones descriptivas muy claras.
    """
    ordenadas = sorted(
        tareas,
        key=lambda t: _calcular_puntaje_prioridad(t, hoy_date),
        reverse=True
    )

    resultado = []
    for i, t in enumerate(ordenadas):
        fecha_str = t.get("fecha_entrega") or t.get("fechaEntrega") or ""
        dias = _calcular_dias_restantes(fecha_str, hoy_date)
        dif = int(t.get("dificultad", 3))
        con = int(t.get("concentracion", 3))
        puntaje = dif + con

        if fecha_str:
            if dias <= 0:
                razon = f"⚠️ TAREA CRÍTICA VENCIDA O PARA HOY ({fecha_str}). ¡Prioridad máxima absoluta!"
            elif dias <= 3:
                razon = f"Vence muy pronto en {dias} días ({fecha_str}). Atención urgente recomendada."
            elif dias <= 7:
                razon = f"Vence en esta semana ({dias} días restantes). Prioridad incrementada."
            else:
                razon = f"Fecha de entrega establecida ({fecha_str}). Prioridad moderada."
        else:
            if dif >= 4 and con >= 4:
                razon = "Alta dificultad y concentración requerida sin fecha límite."
            elif dif >= 4:
                razon = "Tarea compleja que requiere esfuerzo sin fecha límite."
            elif con >= 4:
                razon = "Requiere alta concentración: mejor abordarla con energía."
            elif puntaje <= 4:
                razon = "Tarea liviana sin fecha de entrega: prioridad baja."
            else:
                razon = "Prioridad base según dificultad y concentración."

        resultado.append({
            "tarea_id":    t["id"],
            "tarea_nombre": t["nombre"],
            "prioridad":   i + 1,
            "razon":       razon
        })

    return resultado


def propuesta_local(tareas: list, hoy_date=None) -> dict:
    """
    Fallback local completo cuando Groq no está disponible.
    Aplica reglas que adaptan los tiempos y las actividades de descanso
    dependiendo de la dificultad y de las palabras clave en el nombre de la tarea.
    """
    logger.info("[FALLBACK] Generando propuesta local sin Groq.")

    tareas_priorizadas = _priorizar_tareas_local(tareas, hoy_date)
    tarea = _tarea_mayor_prioridad(tareas, hoy_date)
    nombre_tarea = tarea["nombre"].lower()

    dif = int(tarea.get("dificultad", 3))
    con = int(tarea.get("concentracion", 3))
    puntaje = dif + con

    # Determinar el tipo de tarea basado en palabras clave para personalizar el descanso
    es_mental = any(kw in nombre_tarea for kw in ["estudi", "leer", "matem", "prog", "codig", "doc", "tarea"])
    es_fisica = any(kw in nombre_tarea for kw in ["limpi", "orden", "habita", "ejercicio", "cocina", "lava"])
    es_computadora = any(kw in nombre_tarea for kw in ["correo", "email", "pc", "comput", "excel", "word"])

    # Escalamiento dinámico según puntaje (Dificultad + Concentración: 2 a 10)
    # Calculamos minutos_trabajo entre 15 y 50 min de forma granular
    if puntaje >= 9:
        minutos_trabajo = 45
        minutos_descanso = 15
        mensaje = f"'{tarea['nombre']}' es extremadamente exigente. Bloque largo de 45 min con descanso amplio."
    elif puntaje >= 7:
        minutos_trabajo = 35
        minutos_descanso = 10
        mensaje = f"'{tarea['nombre']}' requiere un esfuerzo alto. Bloque de 35 min."
    elif puntaje >= 5:
        minutos_trabajo = 25
        minutos_descanso = 5
        mensaje = f"'{tarea['nombre']}' tiene una carga moderada. Pomodoro estándar de 25 min."
    else:
        minutos_trabajo = 15
        minutos_descanso = 5
        mensaje = f"'{tarea['nombre']}' es una tarea muy ligera. Bloque ágil de 15 min."

    tipo_descanso = "relajacion"
    if es_fisica: tipo_descanso = "activo"
    elif es_mental: tipo_descanso = "creativo"

    # --- Lógica de "Pensamiento" Local Dinámica y Personalizada ---
    # Evitamos a toda costa recomendaciones genéricas por defecto como "tomar agua".
    seleccionadas = []
    
    # 1. Primera recomendación: adaptada al tipo de esfuerzo del nombre de la tarea
    if any(kw in nombre_tarea for kw in ["prog", "codig", "soft", "dev"]):
        seleccionadas.append("Mirar por la ventana a un punto lejano")
    elif any(kw in nombre_tarea for kw in ["estudi", "leer", "exam", "revis", "tarea"]):
        seleccionadas.append("Hacer 5 rotaciones de cabeza muy lentas")
    elif any(kw in nombre_tarea for kw in ["matem", "calcul", "fisic"]):
        seleccionadas.append("Respirar hondo con los ojos cerrados")
    elif any(kw in nombre_tarea for kw in ["limpi", "orden", "habita", "cocin"]):
        seleccionadas.append("Sentarse a relajar la espalda baja")
    elif any(kw in nombre_tarea for kw in ["correo", "email", "chat"]):
        seleccionadas.append("Hacer estiramientos suaves de muñecas")
    else:
        seleccionadas.append("Estirar hombros y relajar el cuello")

    # 2. Segunda recomendación: adaptada al tiempo de descanso asignado y esfuerzo de forma dinámica
    if minutos_descanso >= 10:
        if es_mental:
            seleccionadas.append(f"Caminar fuera del escritorio {minutos_descanso} min")
        elif es_fisica:
            seleccionadas.append(f"Cerrar los ojos en una silla {minutos_descanso} min")
        else:
            seleccionadas.append(f"Hacer estiramiento lumbar suave ({minutos_descanso} min)")
    else:
        if es_mental:
            seleccionadas.append("Parpadear conscientemente diez veces")
        elif es_fisica:
            seleccionadas.append("Sentarse y respirar hondo 5 veces")
        elif es_computadora:
            seleccionadas.append("Masajear la palma de las manos")
        else:
            seleccionadas.append("Hacer círculos suaves con los tobillos")

    # 3. Tercera recomendación: adaptada al nivel de exigencia (puntaje dificultad + concentracion)
    if puntaje >= 8:
        if es_mental:
            seleccionadas.append("Escuchar una melodía corta y suave")
        else:
            seleccionadas.append("Hacer estiramiento completo de pie")
    elif puntaje >= 5:
        if es_computadora:
            seleccionadas.append("Estirar cada uno de tus dedos")
        else:
            seleccionadas.append("Hacer círculos suaves con los hombros")
    else:
        seleccionadas.append("Lavar las manos con agua muy fría")

    return {
        "tareas_priorizadas":   tareas_priorizadas,
        "tarea_id":             tarea["id"],
        "tarea_nombre":         tarea["nombre"],
        "minutos_trabajo":      minutos_trabajo,
        "minutos_descanso":     minutos_descanso,
        "actividades_descanso": seleccionadas,
        "actividades_descanso_corto": [s[:24] for s in seleccionadas],
        "tipo_descanso":        tipo_descanso,
        "mensaje":              mensaje
    }



# =============================================================================
# Agente principal con Groq
# =============================================================================

def _construir_prompt(tareas: list, hoy_date=None) -> str:
    """
    Construye el prompt para el LLM.
    Prompt estructurado y explícito para maximizar la calidad del JSON de salida.
    """
    tareas_json = json.dumps(tareas, ensure_ascii=False, indent=2)
    if hoy_date is None:
        hoy_str = datetime.now().date().strftime("%Y-%m-%d")
    elif isinstance(hoy_date, str):
        hoy_str = hoy_date
    else:
        hoy_str = hoy_date.strftime("%Y-%m-%d")

    return f"""Eres un agente experto en productividad y técnica Pomodoro.

Analiza las siguientes tareas y genera una planificación Pomodoro óptima.

TAREAS:
{tareas_json}

REGLAS OBLIGATORIAS:
- CRÍTICO - REGLA DE FECHA DE ENTREGA (NUEVA): Hoy estamos a fecha {hoy_str}. Cada tarea puede tener un campo "fecha_entrega" o "fechaEntrega" (formato YYYY-MM-DD). La cercanía de la fecha de entrega es el factor de prioridad MÁS importante. Entre más cercana esté la fecha de entrega, mayor prioridad tiene la tarea. Por ejemplo, si una tarea se entrega el 1 de mayo y otra el 5 de mayo, la del 1 de mayo DEBE tener mayor prioridad y realizarse de primera, independientemente de su dificultad o concentración.
- NUNCA uses el emoji de calendario 📅 en tus respuestas, razones o explicaciones.
- Si una tarea vence hoy, mañana o está vencida (con respecto a {hoy_str}), DEBE ser la primera elegida para trabajar.
- Más dificultad + más concentración = mayor prioridad (siempre y cuando no haya urgencia por fecha de entrega).
- Si la concentración de la tarea más prioritaria es baja (1 o 2), elige en cambio una tarea más simple.
- actividades_descanso: exactamente 3 actividades breves y descriptivas.
- actividades_descanso_corto: exactamente 3 versiones ultra-resumidas (MÁXIMO 25 CARACTERES, ej: "Caminata corta", "Estirar brazos", etc. NUNCA uses más de 25 caracteres).
- tipo_descanso: debe ser exactamente uno de: activo, relajacion, social, creativo.
- CRÍTICO - PROHIBICIÓN ABSOLUTA DE RECOMENDACIONES POR DEFECTO: El agente DEBE PENSAR Y RAZONAR. Queda estrictamente prohibido devolver consejos genéricos o por defecto como "beber agua", "tomar un vaso de agua", "hacer la regla 20-20-20", "hidratarse", "estirar los hombros" o similares. Todas las recomendaciones deben ser originales, sumamente específicas y pensadas directamente para el tipo de descanso y relajación física/mental que requiere el usuario tras realizar esa tarea en particular. Las recomendaciones deben ser de descanso puro, no extensiones de trabajo o estudio. Por ejemplo, si la tarea es "programar", recomendar descansos físicos para programadores como: "masajear suavemente las muñecas y dedos (descanso de digitación)", "lavar la cara con agua fría para aliviar la fatiga ocular", "hacer 5 rotaciones suaves de hombros para liberar tensión lumbar". Si la tarea es "estudiar", recomendar descansos mentales como: "cerrar los ojos y escuchar una melodía instrumental corta", "caminar unos minutos libre de pantallas y textos", "hacer 3 respiraciones profundas con los ojos cerrados".
- tareas_priorizadas: lista COMPLETA de tareas ordenadas de mayor a menor prioridad, con razón en español que explique claramente si priorizó por fecha de entrega/urgencia.

Responde ÚNICAMENTE con un objeto JSON válido. No uses markdown, no añadas texto antes ni después del JSON.

Formato exacto requerido:
{{
  "tareas_priorizadas": [
    {{
      "tarea_id": "id de la tarea",
      "tarea_nombre": "nombre de la tarea",
      "prioridad": 1,
      "razon": "motivo breve en español"
    }}
  ],
  "tarea_id": "id de la tarea elegida",
  "tarea_nombre": "nombre de la tarea elegida",
  "minutos_trabajo": 40,
  "minutos_descanso": 10,
  "actividades_descanso": [
    "actividad descriptiva 1",
    "actividad descriptiva 2",
    "actividad descriptiva 3"
  ],
  "actividades_descanso_corto": [
    "Resumen 1 (20 char)",
    "Resumen 2 (20 char)",
    "Resumen 3 (20 char)"
  ],
  "tipo_descanso": "relajacion",
  "mensaje": "explicación breve en español"
}}"""


def run_agente(tareas: list, hoy_date=None) -> dict:
    """
    Intenta obtener la planificación desde Groq usando peticiones HTTP directas.
    """
    if not tareas:
        raise ValueError("La lista de tareas está vacía.")

    if not API_KEY:
        logger.warning("[AGENTE] Sin API Key — usando fallback local.")
        return propuesta_local(tareas, hoy_date)

    prompt = _construir_prompt(tareas, hoy_date)

    try:
        logger.info("[AGENTE] Solicitando IA avanzada a Groq (%s)...", MODELO)

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODELO,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 1000
        }

        response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            logger.error("[AGENTE] Error en API Groq (%d): %s", response.status_code, response.text)
            return propuesta_local(tareas, hoy_date)

        data = response.json()
        texto_raw = data["choices"][0]["message"]["content"]
        
        texto_limpio = _limpiar_json(texto_raw)
        propuesta = json.loads(texto_limpio)

        # Validar y corregir campos fuera de rango
        propuesta = _validar_propuesta(propuesta, tareas)

        logger.info(
            "[AGENTE] ✅ IA activada correctamente. "
            "Tarea: '%s' | Trabajo: %d | Descanso: %d",
            propuesta.get("tarea_nombre", "?"),
            propuesta.get("minutos_trabajo", 0),
            propuesta.get("minutos_descanso", 0)
        )

        return propuesta

    except Exception as e:
        logger.error("[AGENTE] ❌ Fallo crítico en comunicación: %s", e)
        return propuesta_local(tareas, hoy_date)


def generar_propuesta_pomodoro(tareas: list, hoy_date=None) -> dict:
    """
    Punto de entrada público para routes/api.py.
    Delega en run_agente() que maneja Groq + fallback local.
    """
    return run_agente(tareas, hoy_date)


# =============================================================================
# Script de prueba directo: python services/agente.py
# =============================================================================

if __name__ == "__main__":
    tareas_ejemplo = [
        {"id": "t1", "nombre": "Refactorizar módulo de autenticación", "dificultad": 5, "concentracion": 4},
        {"id": "t2", "nombre": "Responder correos pendientes",          "dificultad": 2, "concentracion": 2},
        {"id": "t3", "nombre": "Revisar documentación del proyecto",    "dificultad": 3, "concentracion": 3},
    ]

    print("=" * 60)
    print("Probando agente Pomodoro con Groq...")
    print("=" * 60)

    resultado = generar_propuesta_pomodoro(tareas_ejemplo)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))