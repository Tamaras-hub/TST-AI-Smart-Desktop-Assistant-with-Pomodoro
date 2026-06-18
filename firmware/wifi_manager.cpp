#include <WiFi.h>
#include <TFT_eSPI.h>
#include "config.h"

extern TFT_eSPI tft;

void conectarWiFi() {
  // Modo cliente WiFi
  WiFi.mode(WIFI_STA);

  Serial.print("Conectando WiFi");

  // Dibujar estado en la pantalla TFT
  tft.fillScreen(TFT_WHITE);
  tft.setTextColor(TFT_BLACK, TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(50, 80);
  tft.print("Conectando a WiFi...");
  
  tft.setCursor(40, 115);
  tft.setTextSize(2);
  tft.print("SSID: ");
  tft.print(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  tft.setCursor(60, 150);
  tft.setTextSize(3);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    tft.print(".");
  }

  Serial.println("\nWiFi conectado");
  
  // Breve mensaje de éxito en pantalla
  tft.fillScreen(TFT_WHITE);
  tft.setTextColor(TFT_GREEN, TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(70, 100);
  tft.print("WiFi Conectado!");
  
  delay(1000);
  tft.fillScreen(TFT_WHITE);
}