#include <TFT_eSPI.h>

#include "actuadores.h"
#include "config.h"
#include "flask_client.h"
#include "pantalla.h"
#include "sensores.h"
#include "wifi_manager.h"


// =========================
// TFT
// =========================
TFT_eSPI tft = TFT_eSPI();

// =========================
// TIMERS
// =========================
unsigned long ultimoEstadoFlask = 0;
unsigned long ultimoDht = 0;
unsigned long ultimoEnvioFlask = 0;
unsigned long ultimoTickSegundo = 0; // tick local 1-segundo

const unsigned long INTERVALO_GET_FLASK = 1000; // Sincronización rápida cada 1s
const unsigned long INTERVALO_POST_FLASK = 6000; // envío sensores cada 6s

// =========================
// VARIABLES SENSORES
// =========================
float temperaturaActual = 0;
float distanciaActual = 999;

// =========================
// VARIABLES POMODORO (locales — el display las usa)
// =========================
int pomodoroMin = 0; // minutos mostrados en pantalla
int pomodoroSeg = 0; // segundos mostrados en pantalla

// Variables del módulo flask_client
extern int tiempoRestanteSync; // segundos del servidor (última sync)
extern String pomodoroModo;
extern bool pomodoroActivo;
extern bool pomodoroPausado;
extern String pomodoroRecomendacion;

// =========================
// SETUP
// =========================
void setup() {

  Serial.begin(115200);

  // 1. Pantalla (Iniciar primero para dar feedback visual)
  iniciarPantalla();

  // 2. WiFi
  conectarWiFi();

  // 3. Sensores y Actuadores
  iniciarSensores();
  iniciarActuadores();

  ultimoTickSegundo = millis();
}

// =========================
// LOOP
// =========================
void loop() {

  unsigned long ahora = millis();

  // =====================================================
  // TICK LOCAL — baja 1 segundo exacto por segundo
  // El display se basa en esto, no en la red.
  // =====================================================
  // ELIMINADO: El tick local ya no resta segundos.
  // Ahora confiamos 100% en el servidor para evitar saltos.
  ultimoTickSegundo = ahora;

  // =====================================================
  // DISTANCIA
  // =====================================================
  distanciaActual = medirDistancia();

  // =====================================================
  // ACTUADORES
  // =====================================================
  actualizarLampara(distanciaActual, ahora);
  actualizarBuzzer(distanciaActual, ahora);

  // =====================================================
  // DHT22
  // =====================================================
  if (ahora - ultimoDht >= INTERVALO_DHT) {
    ultimoDht = ahora;
    float temp = leerTemperatura();
    if (!isnan(temp)) {
      temperaturaActual = temp;
      actualizarMotor(temperaturaActual, distanciaActual);
    }
  }

  // =====================================================
  // SYNC CON SERVIDOR cada 3s
  // El servidor es la fuente de verdad.
  // Solo actualizamos el contador local si hay diferencia.
  // =====================================================
  if (ahora - ultimoEstadoFlask >= INTERVALO_GET_FLASK) {
    ultimoEstadoFlask = ahora;

    obtenerEstadoEsp32Flask(); // Actualiza tiempoRestanteSync, pomodoroModo,
                               // pomodoroActivo, pomodoroPausado

    // =====================================================
    // DETECCIÓN DE CAMBIO DE FASE PARA BUZZER (1 seg)
    // =====================================================
    static String pomodoroModoPrevio = "IDLE";

    if (pomodoroModo != pomodoroModoPrevio && pomodoroModoPrevio != "") {
      // Pitar en CUALQUIER cambio de estado (Inicia, Pausa, Reanuda, Descanso,
      // Termina)
      beepPomodoro(millis());
      pomodoroModoPrevio = pomodoroModo;
    } else if (pomodoroModoPrevio == "") {
      pomodoroModoPrevio = pomodoroModo; // Inicialización
    }

    // Aplicar directamente el tiempo del servidor a la pantalla
    if (pomodoroActivo) {
      pomodoroMin = tiempoRestanteSync / 60;
      pomodoroSeg = tiempoRestanteSync % 60;
    } else {
      pomodoroMin = 0;
      pomodoroSeg = 0;
    }
  }

  // =====================================================
  // TFT
  // =====================================================
  actualizarPantalla(temperaturaActual, distanciaActual, estadoLampara(),
                     estadoMotor(), estadoBuzzer(), millis(), pomodoroMin,
                     pomodoroSeg, pomodoroModo, pomodoroRecomendacion);

  // =====================================================
  // POST DATOS A FLASK (cada 6s)
  // =====================================================
  if (ahora - ultimoEnvioFlask >= INTERVALO_POST_FLASK) {
    ultimoEnvioFlask = ahora;

    int presencia = distanciaActual < DISTANCIA_LUZ ? 1 : 0;

    enviarDatosFlask(temperaturaActual, distanciaActual, presencia,
                     estadoMotor(), estadoLampara(), estadoBuzzer());
  }
}
