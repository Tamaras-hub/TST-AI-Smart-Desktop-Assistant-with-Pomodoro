#ifndef ACTUADORES_H
#define ACTUADORES_H

void iniciarActuadores();

void actualizarLampara(float distancia, unsigned long ahora);

void actualizarBuzzer(float distancia, unsigned long ahora);

void beepPomodoro(unsigned long ahora);

void actualizarMotor(float temperatura, float distancia);

int estadoLampara();

int estadoBuzzer();

int estadoMotor();

bool alertaDistanciaActiva();

#endif