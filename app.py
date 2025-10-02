from flask import Flask, request, jsonify, send_from_directory
import os
import pywifi
from pywifi import const
import time
import subprocess

app = Flask(__name__, static_folder="public", static_url_path="")

# Forside
@app.route("/")
def index():
    return app.send_static_file("index.html")

# Wi-Fi side
@app.route("/wifi.html")
def wifi():
    return send_from_directory(app.static_folder, "wifi.html")

# Scan Wi-Fi med SSID + signal
@app.route("/api/scan")
def scan_wifi():
    try:
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]
        iface.scan()
        time.sleep(3)
        results = iface.scan_results()

        networks = []
        seen = set()
        for net in results:
            if net.ssid and net.ssid not in seen:
                networks.append({"ssid": net.ssid, "signal": net.signal})
                seen.add(net.ssid)

        return jsonify(networks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Forbind Wi-Fi
@app.route("/api/connect", methods=["POST"])
def connect_wifi():
    data = request.json
    ssid = data.get("ssid")
    password = data.get("password")
    if not ssid or not password:
        return "Manglende data", 400

    try:
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]

        profile = pywifi.Profile()
        profile.ssid = ssid
        profile.auth = const.AUTH_ALG_OPEN
        profile.akm.append(const.AKM_TYPE_WPA2PSK)
        profile.cipher = const.CIPHER_TYPE_CCMP
        profile.key = password

        iface.remove_all_network_profiles()
        tmp_profile = iface.add_network_profile(profile)

        iface.connect(tmp_profile)
        time.sleep(5)

        if iface.status() == const.IFACE_CONNECTED:
            return "Forbundet"
        else:
            return "Kunne ikke forbinde", 500

    except Exception as e:
        return f"Fejl: {e}", 500

# Status via netsh for korrekt SSID
@app.route("/api/status")
def status():
    try:
        result = subprocess.run(
            ["powershell", "-Command", "netsh wlan show interfaces"],
            capture_output=True, text=True
        )
        out = result.stdout
        ssid_line = [l for l in out.splitlines() if "SSID" in l and "BSSID" not in l]
        if ssid_line:
            ssid = ssid_line[0].split(":",1)[1].strip()
            return jsonify({"connected": True, "ssid": ssid})
        return jsonify({"connected": False, "ssid": None})
    except Exception:
        return jsonify({"connected": False, "ssid": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
