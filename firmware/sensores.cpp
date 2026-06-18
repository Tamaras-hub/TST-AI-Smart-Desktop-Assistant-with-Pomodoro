#include <Arduino.h>
#include <DHT.h>

#include "config.h"

DHT dht(DHTPIN, DHTTYPE);

void iniciarSensores() {

  pinMode(TRIGGER_PIN, OUTPUT);

  pinMode(ECHO_PIN, INPUT);

  dht.begin();
}

float historialDistancia[5] = {0.0, 0.0, 0.0, 0.0, 0.0};
int cantidadLecturas = 0;

float medirDistancia() {
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 30000);
  float lecturaActual = 999.0;

  if (duracion != 0) {
    lecturaActual = (duracion / 2.0) / 29.1;
  }

  // --- FILTRO DE ARREGLO EN ESP32 (PROMEDIO MÓVIL DE 5 LECTURAS) ---
  // Ignoramos lecturas erráticas o timeouts (999) para no contaminar el
  // promedio
  if (lecturaActual < 400.0) {
    if (cantidadLecturas == 0) {
      // Primera lectura válida: rellenar el arreglo completo
      for (int i = 0; i < 5; i++) {
        historialDistancia[i] = lecturaActual;
      }
      cantidadLecturas = 5;
    } else {
      // Desplazamiento de los elementos del arreglo hacia la izquierda
      for (int i = 0; i < 4; i++) {
        historialDistancia[i] = historialDistancia[i + 1];
      }
      // Insertar el nuevo valor filtrado en la última posición del arreglo
      historialDistancia[4] = lecturaActual;
    }
  }

  // Si aún no hay ninguna lectura válida en el historial, retornamos 999
  if (cantidadLecturas == 0) {
    return 999.0;
  }

  // Calcular el promedio del arreglo de 5 lecturas
  float suma = 0.0;
  for (int i = 0; i < 5; i++) {
    suma += historialDistancia[i];
  }

  return suma / 5.0;
}

float leerTemperatura() { return dht.readTemperature(); }
