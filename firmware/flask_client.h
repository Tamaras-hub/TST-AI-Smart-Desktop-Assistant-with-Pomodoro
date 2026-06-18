#ifndef FLASK_CLIENT_H
#define FLASK_CLIENT_H

#include <Arduino.h>

// Segundos restantes que devolvió el servidor en la última sync
extern int    tiempoRestanteSync;
// millis() en el momento exacto en que llegó la respuesta HTTP
extern unsigned long momentoSync;
// Modo del pomodoro ("work", "break", "pause", "idle")
extern String pomodoroModo;
// true si el pomodoro está corriendo (no idle)
extern bool   pomodoroActivo;
// true si el pomodoro está en pausa
extern bool   pomodoroPausado;
// Mensaje de recomendación para el descanso
extern String pomodoroRecomendacion;

void enviarDatosFlask(
  float temperatura,
  float distancia,
  int presencia,
  int ventilador,
  int lampara,
  int buzzer
);
void obtenerEstadoEsp32Flask();

#endif