# =============================================================================
# app.py — Punto de entrada principal. Aquí se crea y configura Flask.
# =============================================================================

from flask import Flask, render_template
from routes.api import api_blueprint

# Flask(__name__) crea la aplicación. __name__ le dice a Flask dónde
# buscar las carpetas templates/ y static/.
app = Flask(__name__)

# Configuración básica. DEBUG=True recarga el servidor automáticamente
# al guardar cambios. NUNCA usar en producción.
app.config['DEBUG'] = True
app.config['JSON_SORT_KEYS'] = False  # Respeta el orden de las claves en JSON

# Registra el módulo de rutas. url_prefix='/api' significa que todas las rutas
# del blueprint tendrán ese prefijo: /api/status, /api/iot/registro, etc.
app.register_blueprint(api_blueprint, url_prefix='/api')


# =============================================================================
# RUTA RAÍZ — Sirve la interfaz web de productividad por etapas.
#
# Flask busca automáticamente:
#   - templates/index.html  (HTML)
#   - static/css/styles.css (CSS, accesible vía /static/css/styles.css)
#   - static/js/app.js      (JS,  accesible vía /static/js/app.js)
# =============================================================================

@app.route('/', methods=['GET'])
def index():
    """GET / — Renderiza la web del asistente de productividad."""
    return render_template('index.html')


if __name__ == '__main__':
    # Esta condición asegura que el servidor solo inicie si ejecutamos
    # este archivo directamente con: python app.py
    # Si otro archivo importa app.py, el servidor NO arranca solo.
    print("=" * 50)
    print("  Servidor iniciando en http://172.20.10.4:5000")
    print("  ESP32 debe conectar en http://172.20.10.4:5000")
    print("=" * 50)

    # host='0.0.0.0' = acepta conexiones de la red local (necesario para ESP32)
    app.run(host='0.0.0.0', port=5000, debug=True)
