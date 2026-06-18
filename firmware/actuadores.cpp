#include <Arduino.h>

#include "config.h"

// ── LEDC (PWM) config para el buzzer ─────────────────────────────────────────
#define BUZZER_RESOLUTION 8     // 8 bits → duty entre 0 y 255

// Helpers internos para el buzzer
static void buzzerTone(uint32_t frecuencia, uint8_t duty) {
  // Detach + re-attach: forma confiable de cambiar frecuencia en Core 3.x
  ledcDetach(BUZZER_PIN);
  ledcAttach(BUZZER_PIN, frecuencia, BUZZER_RESOLUTION);
  ledcWrite(BUZZER_PIN, duty);
}

static void buzzerSilencio() {
  ledcDetach(BUZZER_PIN);
  ledcAttach(BUZZER_PIN, 1000, BUZZER_RESOLUTION);
  ledcWrite(BUZZER_PIN, 0);  // duty=0 → sin señal
}

unsigned long ultimoDetectado = 0;
unsigned long inicioCercania = 0;

bool objetoCerca = false;

int lamparaActual = 0;
int buzzerActual = 0;
int motorActual = 0;

void iniciarActuadores() {

  pinMode(RELE_PIN, OUTPUT);

  pinMode(MOTOR_PIN, OUTPUT);

  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(RELE_PIN, LOW);

  digitalWrite(MOTOR_PIN, LOW);

  // Inicializar PWM del buzzer
  ledcAttach(BUZZER_PIN, 1000, BUZZER_RESOLUTION);
  buzzerSilencio();
}

void actualizarLampara(float distancia, unsigned long ahora) {

  if (distancia < DISTANCIA_LUZ) {

    digitalWrite(RELE_PIN, HIGH);

    lamparaActual = 1;

    ultimoDetectado = ahora;
  }

  if (ahora - ultimoDetectado > RETARDO_RELE) {

    digitalWrite(RELE_PIN, LOW);

    lamparaActual = 0;
  }
}

unsigned long finBeepPomodoro = 0;

void beepPomodoro(unsigned long ahora) {
  finBeepPomodoro = ahora + 300; // 0.5 segundos (500 ms)
}

unsigned long ultimoCercaBuzzer = 0;

void actualizarBuzzer(float distancia, unsigned long ahora) {
  // 1. Alerta Pomodoro (Prioridad alta)
  if (finBeepPomodoro > 0 && ahora < finBeepPomodoro) {
    if (buzzerActual != 2) {
      // Pomodoro: 600 Hz, duty alto (~78%) → sonido fuerte
      buzzerTone(600, 200); 
      buzzerActual = 2;
    }
    return; // Si el pomodoro suena, ignorar distancia
  }

  // 2. Alarma de Distancia
  if (distancia < DISTANCIA_BUZZER) {
    ultimoCercaBuzzer = ahora; // Registramos la última vez que lo vimos cerca

    if (!objetoCerca) {
      inicioCercania = ahora;
      objetoCerca = true;
    }

    if (ahora - inicioCercania > RETARDO_BUZZER) {
      if (buzzerActual != 1) {
        // Distancia: 300 Hz, duty bajo (~31%) → sonido suave/grave
        buzzerTone(300, 80); 
        buzzerActual = 1;
      }
    }
  } else {
    // Esperamos 500ms de lecturas "lejos" confirmadas para evitar que
    // errores del sensor (ej. leer 999 por un instante) reinicien el timer de 2 segs.
    if (ahora - ultimoCercaBuzzer > 500) {
      if (objetoCerca || buzzerActual != 0) {
        objetoCerca = false;
        buzzerSilencio();
        buzzerActual = 0;
      }
    }
  }
}

void actualizarMotor(float temperatura, float distancia) {

  if (temperatura > TEMP_MOTOR && distancia < DISTANCIA_LUZ) {

    digitalWrite(MOTOR_PIN, HIGH);

    motorActual = 1;

  } else {

    digitalWrite(MOTOR_PIN, LOW);

    motorActual = 0;
  }
}

int estadoLampara() { return lamparaActual; }

int estadoBuzzer() { return buzzerActual; }

int estadoMotor() { return motorActual; }

bool alertaDistanciaActiva() {
  return objetoCerca && (millis() - inicioCercania > RETARDO_BUZZER);
}