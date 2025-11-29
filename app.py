from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import threading
import json

# ------------------------------------
# CONFIGURACIÓN MQTT (igual que tu ESP32)
# ------------------------------------
MQTT_HOST = "c222bcdb.ala.us-east-1.emqxsl.com"
MQTT_PORT = 8883
MQTT_USER = "emqx_online_test_4e7e484e"
MQTT_PASS = "cK#8|74be7<967P!88_95c2C60Y515Xf"

TOPIC_SUB = "Salida/01"      # El ESP32 envía
TOPIC_PUB = "Control/01"     # La web controla

estado_estacionamiento = 1   # 1 libre, 0 ocupado
ultimo_valor = ""

mqtt_client = None  # Cliente MQTT global


# ------------------------------------
# CALLBACKS MQTT
# ------------------------------------
def on_connect(client, userdata, flags, rc):
    print("🔌 MQTT conectado → rc =", rc)
    if rc == 0:
        print("📡 Suscrito a:", TOPIC_SUB)
        client.subscribe(TOPIC_SUB)
    else:
        print("❌ Error conectando al broker")


def on_message(client, userdata, msg):
    global estado_estacionamiento, ultimo_valor

    payload = msg.payload.decode()
    ultimo_valor = payload

    print("\n📥 MQTT - MENSAJE RECIBIDO")
    print("   ➤ Topic:", msg.topic)
    print("   ➤ Payload:", payload)
    print("----------------------------------")

    try:
        data = json.loads(payload)
        estado_estacionamiento = data.get("valor", estado_estacionamiento)
    except:
        print("⚠ Error al interpretar JSON:", payload)


# ------------------------------------
# HILO MQTT (NO BLOQUEA FLASK)
# ------------------------------------
def mqtt_thread():
    global mqtt_client
    mqtt_client = mqtt.Client()

    mqtt_client.enable_logger()  # Activa logs detallados en consola

    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
    mqtt_client.tls_set()  # Requerido para 8883 SSL

    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    print("⏳ Conectando al broker MQTT...")
    mqtt_client.connect(MQTT_HOST, MQTT_PORT)

    mqtt_client.loop_forever()  # Mantiene conexión viva


# Iniciar el hilo MQTT antes de iniciar Flask
threading.Thread(target=mqtt_thread, daemon=True).start()


# ------------------------------------
# FLASK APP
# ------------------------------------
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/estado")
def estado():
    return jsonify({
        "estado": estado_estacionamiento,
        "raw": ultimo_valor
    })


@app.route("/control", methods=["POST"])
def control():
    accion = request.json.get("accion")

    if accion not in ["start", "stop"]:
        return jsonify({"error": "Acción no válida"}), 400

    payload = json.dumps({"activo": True if accion == "start" else False})

    print("\n📤 PUBLICANDO AL ESP32:", payload)
    mqtt_client.publish(TOPIC_PUB, payload)

    return jsonify({"ok": True})


# ------------------------------------
# RUN LOCAL
# ------------------------------------
if __name__ == "__main__":
    print("🚀 Servidor Flask ejecutándose...")
    app.run(debug=True, host="0.0.0.0")
