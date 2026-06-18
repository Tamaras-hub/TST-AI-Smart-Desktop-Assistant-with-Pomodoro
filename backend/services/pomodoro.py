# =============================================================================
# services/pomodoro.py — Lógica del temporizador Pomodoro
#
# DISEÑO: No usamos hilos (threads). En cambio guardamos el instante en que
# inició la sesión y calculamos el tiempo restante ON DEMAND con time.time().
#
#   tiempo_restante = duracion - (ahora - inicio) + segundos_pausados
#
# Esto evita race conditions y mantiene el tiempo siempre exacto.
#
# MÁQUINA DE ESTADOS:
#
#   IDLE ──start──► TRABAJANDO ──pause──► PAUSADO
#                       ▲                    │
#                       └──────resume────────┘
#                       │
#               tiempo llega a 0
#                       ▼
#                   DESCANSO ──tiempo llega a 0──► IDLE
#                       │
#                   finish (manual)
#                       ▼
#                     IDLE
# =============================================================================

import time
from services.estado import estado

DESCANSO_DEFECTO_MIN = 5  # minutos de descanso por defecto tras una sesión

# Estado interno del módulo (no se expone directamente al exterior)
_pom = {
    "inicio":         None,  # time.time() cuando arrancó o se reanudó
    "duracion":       0,     # duración total de la sesión activa (segundos)
    "tiempo_pausado": 0,     # acumulado de segundos en pausa
    "pausa_inicio":   None,  # time.time() del momento en que se pausó
    "descanso_configurado": DESCANSO_DEFECTO_MIN, # minutos de descanso para esta sesión
}


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _segundos_efectivos():
    """Segundos transcurridos descontando el tiempo en pausa."""
    if _pom["inicio"] is None:
        return 0
    return (time.time() - _pom["inicio"]) - _pom["tiempo_pausado"]


def _sync_tiempo_restante():
    """Actualiza tiempo_restante en el estado global (mínimo 0)."""
    restante = _pom["duracion"] - _segundos_efectivos()
    estado["sistema"]["tiempo_restante"] = max(0, int(restante))


def _resetear_timer():
    _pom["inicio"]         = None
    _pom["duracion"]       = 0
    _pom["tiempo_pausado"] = 0
    _pom["pausa_inicio"]   = None
    _pom["descanso_configurado"] = DESCANSO_DEFECTO_MIN


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def iniciar_pomodoro(tarea: str, duracion_min: int = 25, descanso_min: int = 5, recomendaciones: list = None):
    """
    Inicia una sesión de trabajo.
    Transición: cualquier estado → TRABAJANDO
    """
    _resetear_timer()
    _pom["inicio"]   = time.time()
    _pom["duracion"] = duracion_min * 60
    _pom["descanso_configurado"] = descanso_min

    estado["sistema"]["modo"]            = "TRABAJANDO"
    estado["sistema"]["tarea_actual"]    = tarea
    estado["sistema"]["tiempo_restante"] = _pom["duracion"]
    
    if recomendaciones:
        estado["sistema"]["recomendaciones_descanso"] = recomendaciones

    print(f"[POMODORO] ▶ Iniciado: '{tarea}' — {duracion_min} min")


def pausar_pomodoro():
    """
    Pausa el temporizador.
    Transición: TRABAJANDO → PAUSADO
    """
    if estado["sistema"]["modo"] != "TRABAJANDO":
        return {"ok": False, "error": "Solo puedes pausar cuando el modo es TRABAJANDO"}

    _pom["pausa_inicio"] = time.time()
    _sync_tiempo_restante()
    estado["sistema"]["modo"] = "PAUSADO"

    print(f"[POMODORO] ⏸ Pausado. Restante: {estado['sistema']['tiempo_restante']}s")
    return {"ok": True}


def reanudar_pomodoro():
    """
    Reanuda desde pausa.
    Transición: PAUSADO → TRABAJANDO
    Acumula en _pom['tiempo_pausado'] cuánto duró esta pausa para
    que el cálculo de tiempo_restante siga siendo correcto.
    """
    if estado["sistema"]["modo"] != "PAUSADO":
        return {"ok": False, "error": "Solo puedes reanudar cuando el modo es PAUSADO"}

    duracion_pausa        = time.time() - _pom["pausa_inicio"]
    _pom["tiempo_pausado"] += duracion_pausa
    _pom["pausa_inicio"]   = None

    estado["sistema"]["modo"] = "TRABAJANDO"
    _sync_tiempo_restante()

    print(f"[POMODORO] ▶ Reanudado. Restante: {estado['sistema']['tiempo_restante']}s")
    return {"ok": True}


def iniciar_descanso(duracion_min: int = None):
    """
    Inicia un período de descanso.
    Transición: TRABAJANDO (tiempo=0) → DESCANSO
    Reutiliza el mismo mecanismo de timer que el trabajo.
    """
    if duracion_min is None:
        duracion_min = _pom.get("descanso_configurado", DESCANSO_DEFECTO_MIN)

    _resetear_timer()
    _pom["inicio"]   = time.time()
    _pom["duracion"] = duracion_min * 60

    estado["sistema"]["modo"]            = "DESCANSO"
    # Mantener el nombre de la tarea durante el descanso en lugar de borrarlo
    estado["sistema"]["tiempo_restante"] = _pom["duracion"]

    print(f"[POMODORO] ☕ Descanso iniciado: {duracion_min} min")


def finalizar_pomodoro():
    """
    Termina manualmente la sesión activa (trabajo o descanso) y vuelve a IDLE.
    Transición: TRABAJANDO | PAUSADO | DESCANSO → IDLE
    """
    tarea = estado["sistema"]["tarea_actual"]
    _resetear_timer()

    estado["sistema"]["modo"]            = "IDLE"
    estado["sistema"]["tarea_actual"]    = ""
    estado["sistema"]["tiempo_restante"] = 0

    print(f"[POMODORO] ⏹ Finalizado: '{tarea}'")
    return {"ok": True}

def finalizar_trabajo():
    """
    Termina el bloque de trabajo actual y pasa a descanso.
    """
    modo = estado["sistema"]["modo"]

    if modo not in ("TRABAJANDO", "PAUSADO"):
        return {
            "ok": False,
            "error": "Solo puedes finalizar trabajo cuando estás trabajando o pausado"
        }

    iniciar_descanso()
    return {"ok": True}

def obtener_estado_pomodoro():
    """
    Devuelve el estado Pomodoro actualizado.
    La ESP32 llama a este endpoint periódicamente para mostrar
    el countdown en la pantalla TFT.

    Si el tiempo llega a 0:
      - En TRABAJANDO → transiciona a DESCANSO automáticamente
      - En DESCANSO   → transiciona a IDLE automáticamente
    """
    modo = estado["sistema"]["modo"]

    if modo in ("TRABAJANDO", "DESCANSO"):
        _sync_tiempo_restante()

        if estado["sistema"]["tiempo_restante"] == 0:
            if modo == "TRABAJANDO":
                # Sesión terminada → arranca descanso automático
                iniciar_descanso()
            else:
                # Descanso terminado → vuelve a IDLE
                finalizar_pomodoro()

    return {
        "modo":            estado["sistema"]["modo"],
        "tarea_actual":    estado["sistema"]["tarea_actual"],
        "tiempo_restante": estado["sistema"]["tiempo_restante"],
        "duracion_total":  _pom["duracion"],
        "recomendaciones": estado["sistema"]["recomendaciones_descanso"]
    }

def saltar_fase():
    """
    Avanza a la siguiente fase del Pomodoro.
    """

    modo = estado["sistema"]["modo"]

    # Si está trabajando o pausado -> pasar a descanso
    if modo in ("TRABAJANDO", "PAUSADO"):
        iniciar_descanso()
        return {
            "ok": True,
            "nuevo_modo": "DESCANSO"
        }

    # Si está descansando -> terminar ciclo
    elif modo == "DESCANSO":
        finalizar_pomodoro()
        return {
            "ok": True,
            "nuevo_modo": "IDLE"
        }

    return {
        "ok": False,
        "error": "No hay una fase activa"
    }