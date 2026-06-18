#include <ArduinoJson.h>
#include <WiFi.h>
#include <HTTPClient.h>

#include "config.h"

// =============================================================================
// Variables globales del módulo
//
// En lugar de llevar un contador local (que se desfasa cuando el HTTP bloquea),
// guardamos el VALOR DEL SERVIDOR y el MOMENTO en que lo recibimos.
// El .ino calcula el tiempo mostrado como:
//   tiempoMostrado = tiempoRestanteSync - (millis() - momentoSync) / 1000
// Esto elimina los saltos porque nunca hay un contador local que se atrascó.
// =============================================================================
int          tiempoRestanteSync = 0;   // segundos que devolvió el servidor
unsigned long momentoSync       = 0;   // millis() cuando llegó esa respuesta
String       pomodoroModo       = "idle";
bool         pomodoroActivo     = false;
bool         pomodoroPausado    = false;  // true cuando el servidor reporta pausa
String       pomodoroRecomendacion = "";  // Mensaje de descanso

void enviarDatosFlask(
  float temperatura,
  float distancia,
  int presencia,
  int ventilador,
  int lampara,
  int buzzer
) {

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("WiFi desconectado");

    return;
  }

  // Cliente TCP/IP
  WiFiClient client;

  // Cliente HTTP
  HTTPClient http;

  String url = SERVIDOR_FLASK + "/api/iot/registro";

  Serial.print("URL: ");

  Serial.println(url);

  // Conexión HTTP usando WiFiClient
  http.begin(client, url);
  http.setTimeout(1200); // máximo 1.2s de espera

  http.addHeader("Content-Type", "application/json");

  // ---------------------------------------------------------------------------
  // JSON
  // ---------------------------------------------------------------------------

  String json = "{";

  json += "\"temperatura\":" + String(temperatura, 1) + ",";
  json += "\"distancia\":" + String(distancia, 1) + ",";
  json += "\"presencia\":" + String(presencia) + ",";

  json += "\"actuadores\":{";

  json += "\"ventilador\":" + String(ventilador) + ",";
  json += "\"lampara\":" + String(lampara) + ",";
  json += "\"buzzer\":" + String(buzzer);

  json += "}}";

  Serial.println("JSON enviado:");

  Serial.println(json);

  // ---------------------------------------------------------------------------
  // POST
  // ---------------------------------------------------------------------------

  int codigo = http.POST(json);

  Serial.print("Codigo HTTP: ");

  Serial.println(codigo);

  if (codigo > 0) {

    String respuesta = http.getString();

    Serial.println("Respuesta Flask:");

    Serial.println(respuesta);

  } else {

    Serial.print("Error HTTP: ");

    Serial.println(http.errorToString(codigo));
  }

  http.end();

}
void obtenerEstadoEsp32Flask() {

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado");
    return;
  }

  WiFiClient client;
  HTTPClient http;

  String url = SERVIDOR_FLASK + "/api/esp32/status";

  Serial.print("Consultando estado ESP32: ");
  Serial.println(url);

  http.begin(client, url);
  http.setTimeout(1200); // máximo 1.2s de espera

  int codigo = http.GET();

  Serial.print("Codigo HTTP GET: ");
  Serial.println(codigo);

  if (codigo == 200) {

    String respuesta = http.getString();

    // Guardamos el instante ANTES de parsear para que momentoSync sea
    // lo más preciso posible (la respuesta ya llegó en este punto).
    unsigned long recibi = millis();

    Serial.println("Estado recibido:");
    Serial.println(respuesta);

    StaticJsonDocument<4096> doc; // Aumentado a 4096 para textos largos de IA

    DeserializationError error = deserializeJson(doc, respuesta);

    if (error) {
      Serial.print("Error parseando JSON (posiblemente muy largo): ");
      Serial.println(error.c_str());
      http.end();
      return;
    }

    // 1. Obtener el tiempo restante real
    int restante = doc["parametros"]["duracion"] | 0;
    tiempoRestanteSync = restante;
    momentoSync        = recibi;   // ancla para cálculos locales

    // 2. --- DETECCIÓN ROBUSTA DE PAUSA ---
    bool pausadoJson = false;
    JsonObject params = doc["parametros"];
    JsonObject ui = doc["ui"];

    if (params.containsKey("pausado")) pausadoJson = params["pausado"].as<bool>() || (params["pausado"].as<int>() == 1);
    else if (params.containsKey("paused")) pausadoJson = params["paused"].as<bool>() || (params["paused"].as<int>() == 1);
    else if (params.containsKey("running")) pausadoJson = !(params["running"].as<bool>() || (params["running"].as<int>() == 1));
    else if (ui.containsKey("pausado")) pausadoJson = ui["pausado"].as<bool>() || (ui["pausado"].as<int>() == 1);
    
    String modo = doc["ui"]["modo"].as<String>();
    String modoLow = modo;
    modoLow.toLowerCase();
    pomodoroModo   = modo;
    pomodoroActivo = (modoLow != "idle");

    if (modoLow.indexOf("pause") >= 0 || modoLow.indexOf("pausa") >= 0) {
      pausadoJson = true;
    }
    pomodoroPausado = pausadoJson;

    // --- CAPTURAR RECOMENDACIONES (Las 4 que envía el servidor) ---
    String encontrada = "";
    JsonArray recoArray = doc["ui"]["recomendaciones"];
    if (recoArray.size() > 0) {
      for (size_t i = 0; i < recoArray.size(); i++) {
        encontrada += recoArray[i].as<String>();
        if (i < recoArray.size() - 1) encontrada += "\n";
      }
    } else {
      // Fallback si no hay array (por compatibilidad o error)
      if (doc.containsKey("recomendacion")) encontrada = doc["recomendacion"].as<String>();
      else if (params.containsKey("recomendacion")) encontrada = params["recomendacion"].as<String>();
      else if (ui.containsKey("mensaje")) encontrada = ui["mensaje"].as<String>();
    }
    
    pomodoroRecomendacion = encontrada;

    // SI ESTAMOS EN DESCANSO Y NO HAY RECO, IMPRIMIR TODO PARA DEBUGEAR
    if (modoLow.indexOf("break") >= 0 || modoLow.indexOf("descanso") >= 0) {
      if (pomodoroRecomendacion.length() == 0) {
        Serial.println("!!! AVISO: Modo descanso activo pero recomendacion VACIA.");
        Serial.println("JSON recibido:");
        Serial.println(respuesta); 
      } else {
        Serial.print("Recomendacion OK: ");
        Serial.println(pomodoroRecomendacion);
      }
    }

    Serial.print(">>> SYNC: ");
    Serial.print(tiempoRestanteSync);
    Serial.print("s | Modo: ");
    Serial.print(pomodoroModo);
    Serial.print(" | Pausado: ");
    Serial.println(pomodoroPausado ? "SI" : "NO");

  } else {
    Serial.print("Error HTTP GET: ");
    Serial.println(http.errorToString(codigo));
  }

  http.end();
}