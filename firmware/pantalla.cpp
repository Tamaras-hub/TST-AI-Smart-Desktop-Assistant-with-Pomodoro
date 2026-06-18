#include "pantalla.h"
#include "actuadores.h"
#include <Arduino.h>
#include <TFT_eSPI.h>

// Usamos extern para referenciar la instancia creada en el archivo principal
// (.ino)
extern TFT_eSPI tft;

// =========================
// VARIABLES DE CONTROL
// =========================
static unsigned long tiempoAlternancia = 0;
static int tandaVisible = 0;
static bool alertaPrevia = false;

// Detectar cambio del pomodoro
static bool pomodoroActivoPrevio = false;
static bool esDescansoPrevio = false;

// =========================
// INICIAR PANTALLA
// =========================
void iniciarPantalla() {

  tft.init();
  tft.setRotation(2);
  tft.fillScreen(TFT_WHITE);

  // =========================
  // BIENVENIDA
  // =========================
  tft.setTextColor(TFT_BLACK, TFT_WHITE);
  tft.setTextSize(3);

  tft.setCursor(130, 110);
  tft.print("Hola");

  delay(1000);

  tft.fillScreen(TFT_WHITE);

  tft.setCursor(20, 110);
  tft.print("Vamos a trabajar");

  delay(1000);

  tft.fillScreen(TFT_WHITE);
}

// =========================
// ACTUALIZAR PANTALLA
// =========================
void actualizarPantalla(float temperatura, float distancia, int lampara,
                        int motor, int buzzer, unsigned long ahora,
                        int pomodoroMinutos, int pomodoroSegundos,
                        String pomodoroModo, String pomodoroRecomendacion) {

  bool alertaActiva = alertaDistanciaActiva();

  // =========================
  // LIMPIEZA INTELIGENTE
  // =========================
  if (alertaActiva && !alertaPrevia) {

    tft.fillScreen(TFT_WHITE);

    alertaPrevia = true;
  } else if (!alertaActiva && alertaPrevia) {

    tft.fillScreen(TFT_WHITE);

    alertaPrevia = false;

    tandaVisible = 0;
  }

  // =========================
  // PANTALLA ALERTA
  // =========================
  if (alertaActiva) {

    tft.setTextColor(TFT_CYAN, TFT_WHITE);

    tft.setTextSize(3);

    tft.setCursor(100, 70);
    tft.print("ALERTA!");

    tft.setTextSize(2);

    tft.setCursor(80, 120);
    tft.print("ALEJATE DE LA");

    tft.setCursor(110, 140);
    tft.print("PANTALLA");
  }

  // =========================
  // PANTALLA NORMAL
  // =========================
  else {

    // =====================================================
    // DETECCIÓN DE MODO DESCANSO (Movido arriba para el título)
    // =====================================================
    String modoLow = pomodoroModo;
    modoLow.toLowerCase();
    // Corregido: "break" en minúsculas para coincidir con modoLow
    bool esDescanso = (modoLow.indexOf("break") >= 0 || modoLow.indexOf("descanso") >= 0);

    // =========================
    // TITULO DINÁMICO
    // =========================
    tft.setTextColor(TFT_BLACK, TFT_WHITE);
    tft.setTextSize(2);
    
    // Si es descanso, ponemos RECOMENDACIONES, si no MEDICIONES
    if (esDescanso) {
      tft.setCursor(60, 5);
      tft.print("RECOMENDACIONES");
    } else {
      tft.setCursor(100, 5);
      tft.print("MEDICIONES     ");
    }

    // =========================
    // POMODORO SIEMPRE VISIBLE
    // =========================

    tft.setTextFont(1);
    tft.setTextSize(2);

    // Texto rojo con fondo blanco
    tft.setTextColor(TFT_RED, TFT_WHITE);

    // Estado actual del pomodoro
    bool pomodoroActivo = !(pomodoroMinutos <= 0 && pomodoroSegundos <= 0);

    // Si cambió de estado, limpiar solo esa área
    if (pomodoroActivo != pomodoroActivoPrevio) {
      // Aumentamos el alto a 70 para cubrir el modo y el tiempo
      tft.fillRect(0, 135, 320, 70, TFT_WHITE);
      pomodoroActivoPrevio = pomodoroActivo;
    }

    if (!pomodoroActivo) {
      tft.setCursor(50, 150);
      tft.setTextSize(2);
      tft.print("Pomodoro Inactivo  ");
    } else {
      // 1. Capitalizar el modo (Work, Break, etc.)
      String modoCap = pomodoroModo;
      if (modoCap.length() > 0) {
        modoCap[0] = toupper(modoCap[0]);
        for (int i = 1; i < modoCap.length(); i++) {
          modoCap[i] = tolower(modoCap[i]);
        }
      }

      // 2. Mostrar Modo (Arriba) - Separado para Work y Break
      tft.setTextSize(3);
      
      // AQUÍ PUEDES CAMBIAR LA POSICIÓN DE CADA UNO
      if (esDescanso) {
        // Posición para "Break" o "Descanso"
        tft.setCursor(115, 120); 
        tft.print(modoCap);
      } else {
        // Posición para "Work" o "Trabajo"
        tft.setCursor(125, 120); 
        tft.print(modoCap);
      }

      // 3. Mostrar Tiempo (Abajo)
      tft.setTextSize(4);
      tft.setCursor(100, 155);
      char tiempo[15];
      sprintf(tiempo, "%02d:%02d   ", pomodoroMinutos, pomodoroSegundos);
      tft.print(tiempo);
    }

    // --- LIMPIEZA FORZADA AL CAMBIAR DE MODO ---
    if (esDescanso != esDescansoPrevio) {
      // Limpiamos el área del título (Superior) y el área central
      tft.fillRect(0, 0, 320, 30, TFT_WHITE); 
      tft.fillRect(0, 30, 320, 105, TFT_WHITE);
      esDescansoPrevio = esDescanso;
    }

    if (esDescanso) {
      // ---------------------------------------------------
      // VISTA DE DESCANSO: RECOMENDACIONES (3 ÍTEMS)
      // ---------------------------------------------------
      tft.setTextColor(TFT_BLUE, TFT_WHITE);
      
      if (pomodoroRecomendacion.length() > 0) {
        tft.setTextFont(1); 
        tft.setTextSize(2); 
        int yPos = 40; 
        
        String temp = pomodoroRecomendacion;
        int startIdx = 0;
        int endIdx = temp.indexOf('\n');
        
        while (endIdx != -1) {
          tft.setCursor(10, yPos);
          tft.print(temp.substring(startIdx, endIdx));
          yPos += 20; // Más espacio entre las 3 líneas (antes 18)
          startIdx = endIdx + 1;
          endIdx = temp.indexOf('\n', startIdx);
          
          if (yPos > 125) break;
        }
        // Última línea
        if (yPos <= 125) {
          tft.setCursor(10, yPos);
          tft.print(temp.substring(startIdx));
        }
        
      } else {
        tft.setTextSize(2);
        tft.setCursor(20, 75);
        tft.print("Estirate un poco...");
      }

    } else {
      // ---------------------------------------------------
      // VISTA NORMAL: SENSORES Y ACTUADORES
      // ---------------------------------------------------

      // =========================
      // CAMBIO DE TANDAS (cada 10s)
      // =========================
      if (ahora - tiempoAlternancia > 10000) {
        tiempoAlternancia = ahora;
        tandaVisible = !tandaVisible;
        tft.fillRect(0, 30, 320, 90, TFT_WHITE);
      }

      if (tandaVisible == 0) {
        // ... TANDA 1: SENSORES ...
        tft.setTextSize(2);
        tft.setTextColor(TFT_ORANGE, TFT_WHITE);
        tft.setCursor(20, 40);
        tft.print("Distancia:");
        tft.setCursor(20, 65);
        char distanciaTexto[20];
        sprintf(distanciaTexto, "%.1f cm   ", distancia);
        tft.print(distanciaTexto);

        tft.setTextColor(TFT_CYAN, TFT_WHITE);
        tft.setCursor(160, 40);
        tft.print("Temperatura:");
        tft.setCursor(160, 65);
        char tempTexto[20];
        if (isnan(temperatura)) {
          sprintf(tempTexto, "Error     ");
        } else {
          sprintf(tempTexto, "%.1f %cC   ", temperatura, 247);
        }
        tft.print(tempTexto);
      } else {
        // ... TANDA 2: ACTUADORES ...
        tft.setTextSize(2);
        tft.setCursor(30, 40);
        tft.setTextColor(TFT_BLUE, TFT_WHITE);
        tft.print(lampara == 1 ? "Luz: ON     " : "Luz: OFF    ");
        tft.setCursor(170, 40);
        tft.setTextColor(motor == 1 ? TFT_PURPLE : TFT_YELLOW, TFT_WHITE);
        tft.print(motor == 1 ? "Motor: ON   " : "Motor: OFF  ");
        tft.setCursor(90, 70);
        if (alertaDistanciaActiva()) {
          tft.setTextColor(TFT_RED, TFT_WHITE);
          tft.print("Alerta activa!");
        } else {
          tft.setTextColor(TFT_GREEN, TFT_WHITE);
          tft.print("Sistema: OK   ");
        }
      }
    }
  }
}