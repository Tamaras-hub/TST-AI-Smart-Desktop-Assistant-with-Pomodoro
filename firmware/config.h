#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include <DHT.h>

inline const char *WIFI_SSID = "Srod";
inline const char *WIFI_PASSWORD = "thomasgay";

inline const String SERVIDOR_FLASK = "http://172.20.10.4:5000";

#define TRIGGER_PIN 12
#define ECHO_PIN 14
#define RELE_PIN 32
#define BUZZER_PIN 27
#define MOTOR_PIN 26
#define DHTPIN 33
#define DHTTYPE DHT22

inline const int DISTANCIA_BUZZER = 40;
inline const int DISTANCIA_LUZ = 70;
inline const float TEMP_MOTOR = 30.0;

inline const unsigned long INTERVALO_DHT = 2000;
inline const unsigned long INTERVALO_FLASK = 2000;
inline const unsigned long RETARDO_RELE = 10000;
inline const unsigned long RETARDO_BUZZER = 2000;

#endif