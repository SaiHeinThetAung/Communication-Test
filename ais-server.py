import eventlet
eventlet.monkey_patch()

import socket
import threading
import signal
from queue import Queue, Empty
from pymavlink import mavutil
from pyais import decode
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import json
import datetime
import os

# Configuration
TCP_IP = "0.0.0.0"
TCP_PORT = 1280
UDP_IP = "0.0.0.0"
UDP_PORT = 1281
BUFFER_SIZE = 4096
LOG_DIR = "ais-logs"
os.makedirs(LOG_DIR, exist_ok=True)

shutdown_event = threading.Event()
ui_queue = Queue()
last_received_time = datetime.datetime.now()
connection_active = False
current_log_file = None
sender_ip = "Unknown"

# Store latest AIS data globally
latest_data = {
    'mmsi': "N/A",
    'lat': None,
    'lon': None,
    'heading': "N/A",
    'status': "Inactive",
    'sender': sender_ip,
    'mmsi_count': 0,
    'unique_mmsis': []
}

unique_mmsis = set()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

def get_new_log_filename():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"ais_log_{timestamp}.log")

def log_to_file(data):
    global current_log_file
    if current_log_file is None:
        current_log_file = get_new_log_filename()

    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'data': data
    }
    try:
        with open(current_log_file, 'a') as f:
            json.dump(log_entry, f)
            f.write('\n')
    except Exception as e:
        print(f"[LOG] Error writing to log file: {e}")

def update_ui_data(mmsi, lat, lon, heading, source_ip):
    global last_received_time, connection_active, current_log_file, sender_ip, unique_mmsis
    last_received_time = datetime.datetime.now()
    sender_ip = source_ip
    if not connection_active:
        connection_active = True
        current_log_file = get_new_log_filename()

    if mmsi is not None and mmsi != "N/A":
        unique_mmsis.add(mmsi)

    mmsi_count = len(unique_mmsis)

    data = {
        'mmsi': mmsi if mmsi is not None else "N/A",
        'lat': lat,
        'lon': lon,
        'heading': heading if heading is not None else "N/A",
        'status': "Active",
        'sender': source_ip,
        'mmsi_count': mmsi_count,
        # optional: remove unique_mmsis list if too large
        #'unique_mmsis': list(unique_mmsis)
    }
    ui_queue.put(data)
    log_to_file(data)
    print(f"[EMIT] Sending update: {data}")
    socketio.emit('update', data)

def monitor_connection_status():
    global connection_active, current_log_file
    while not shutdown_event.is_set():
        now = datetime.datetime.now()
        if connection_active and (now - last_received_time).total_seconds() > 5:
            data = {
                'mmsi': "N/A",
                'lat': None,
                'lon': None,
                'heading': "N/A",
                'status': "Inactive",
                'sender': sender_ip
            }
            ui_queue.put(data)
            log_to_file({"event": "No data for 5 seconds, marking inactive"})
            connection_active = False
            current_log_file = None
            socketio.emit('update', data)
        shutdown_event.wait(timeout=1)

def handle_mavlink_message(msg, source_ip):
    if msg.get_type() == 'AIS_VESSEL':
        try:
            mmsi = msg.mmsi
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            heading = msg.heading
            update_ui_data(mmsi, lat, lon, heading, source_ip)
        except Exception as e:
            print(f"[{source_ip}] Error extracting MAVLink AIS_VESSEL data: {e}")

def handle_nmea_sentence(sentence, source_ip):
    try:
        decoded = decode(sentence).asdict()
        mmsi = decoded.get('mmsi')
        lat = decoded.get('lat')
        lon = decoded.get('lon')
        heading = decoded.get('heading')
        if heading == 'N/A' or heading is None:
            heading = None
        update_ui_data(mmsi, lat, lon, heading, source_ip)
    except Exception as e:
        print(f"[{source_ip}] Failed to parse NMEA sentence: {e} Sentence: {sentence!r}")

def mavlink_parser_worker(data_queue, source_ip):
    mav = mavutil.mavlink.MAVLink(None)
    mav.srcSystem = 255
    while not shutdown_event.is_set():
        try:
            data = data_queue.get(timeout=0.5)
            if data is None:
                break
            for b in data:
                msg = mav.parse_char(chr(b))
                if msg:
                    handle_mavlink_message(msg, source_ip)
        except Empty:
            continue
        except Exception as e:
            print(f"[{source_ip}] MAVLink parsing error: {e}")

def tcp_client_handler(client_sock, client_addr):
    source_ip = client_addr[0]
    print(f"[TCP {source_ip}] Connected")
    data_queue = Queue()
    mav_thread = threading.Thread(target=mavlink_parser_worker, args=(data_queue, source_ip), daemon=True)
    mav_thread.start()
    buffer = b""
    try:
        while not shutdown_event.is_set():
            data = client_sock.recv(BUFFER_SIZE)
            if not data:
                print(f"[TCP {source_ip}] Client disconnected")
                break
            buffer += data
            try:
                text = buffer.decode('utf-8')
                while '\r\n' in text:
                    sentence, text = text.split('\r\n', 1)
                    sentence = sentence.strip()
                    if sentence:
                        if sentence.startswith('!') or sentence.startswith('$'):
                            handle_nmea_sentence(sentence, source_ip)
                        else:
                            data_queue.put(sentence.encode('utf-8'))
                buffer = text.encode('utf-8')
            except UnicodeDecodeError:
                data_queue.put(buffer)
                buffer = b""
    except Exception as e:
        print(f"[TCP {source_ip}] Client handler error: {e}")
    finally:
        client_sock.close()
        print(f"[TCP {source_ip}] Connection closed")
        data_queue.put(None)
        mav_thread.join(timeout=2)

def tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TCP_IP, TCP_PORT))
    server.listen(5)
    print(f"[TCP] Listening on {TCP_IP}:{TCP_PORT}")
    while not shutdown_event.is_set():
        try:
            server.settimeout(1.0)
            client_sock, client_addr = server.accept()
            threading.Thread(target=tcp_client_handler, args=(client_sock, client_addr), daemon=True).start()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[TCP] Server error: {e}")
    server.close()
    print("[TCP] Server shutdown")

def udp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((UDP_IP, UDP_PORT))
    print(f"[UDP] Listening on {UDP_IP}:{UDP_PORT}")
    mav = mavutil.mavlink.MAVLink(None)
    mav.srcSystem = 255
    while not shutdown_event.is_set():
        try:
            server.settimeout(1.0)
            data, addr = server.recvfrom(BUFFER_SIZE)
            source_ip = addr[0]
            try:
                text = data.decode('utf-8')
                if text.startswith('!') or text.startswith('$'):
                    handle_nmea_sentence(text.strip(), source_ip)
                else:
                    for b in data:
                        msg = mav.parse_char(chr(b))
                        if msg:
                            handle_mavlink_message(msg, source_ip)
            except UnicodeDecodeError:
                for b in data:
                    msg = mav.parse_char(chr(b))
                    if msg:
                        handle_mavlink_message(msg, source_ip)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[UDP] Server error: {e}")
    server.close()
    print("[UDP] Server shutdown")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/latest")
def api_latest():
    return jsonify(latest_data)

def update_latest_data():
    while not shutdown_event.is_set():
        try:
            data = ui_queue.get(timeout=1)
            latest_data.update(data)
        except Empty:
            continue

def signal_handler(sig, frame):
    print("Shutdown signal received. Exiting...")
    shutdown_event.set()

def start_network_threads():
    tcp_thread = threading.Thread(target=tcp_server, daemon=True, name="TCPServer")
    udp_thread = threading.Thread(target=udp_server, daemon=True, name="UDPServer")
    tcp_thread.start()
    udp_thread.start()
    return tcp_thread, udp_thread

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print("Starting AIS TCP and UDP Receiver...")
    tcp_thread, udp_thread = start_network_threads()
    updater_thread = threading.Thread(target=update_latest_data, daemon=True)
    status_monitor_thread = threading.Thread(target=monitor_connection_status, daemon=True)
    updater_thread.start()
    status_monitor_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
    print("Waiting for server threads to finish...")
    shutdown_event.set()
    tcp_thread.join(timeout=3)
    udp_thread.join(timeout=3)
    updater_thread.join(timeout=3)
    status_monitor_thread.join(timeout=3)
    print("Shutdown complete.")

if __name__ == "__main__":
    main()