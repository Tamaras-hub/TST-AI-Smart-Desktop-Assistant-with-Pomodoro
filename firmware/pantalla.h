#ifndef PANTALLA_H
#define PANTALLA_H
#include <Arduino.h>

void iniciarPantalla();
void actualizarPantalla(float temperatura, float distancia, int lampara, int motor, int buzzer, unsigned long ahora, int pomodoroMinutos,
  int pomodoroSegundos, String pomodoroModo, String pomodoroRecomendacion);
 
#endif