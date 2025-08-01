import socket
import threading
import signal
import tkinter as tk
from queue import Queue, Empty
from pymavlink import mavutil
from pyais import decode

# Configuration
TCP_IP = "127.0.0.1"
TCP_PORT = 5000
UDP_IP = "0.0.0.0"
UDP_PORT = 5001

BUFFER_SIZE = 4096

shutdown_event = threading.Event()
ui_queue = Queue()

def update_ui_data(mmsi, lat, lon, heading):
    # Allow lat/lon to be None, convert to "N/A" in UI
    ui_queue.put({
        'mmsi': mmsi if mmsi is not None else "N/A",
        'lat': lat,
        'lon': lon,
        'heading': heading if heading is not None else "N/A"
    })
    print(f"Queued AIS data: MMSI={mmsi}, Lat={lat}, Lon={lon}, Heading={heading}")

def handle_mavlink_message(msg, source):
    if msg.get_type() == 'AIS_VESSEL':
        try:
            mmsi = msg.mmsi
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            heading = msg.heading
            print(f"[{source}] AIS MMSI={mmsi} Lat={lat:.6f} Lon={lon:.6f} Heading={heading}")
            update_ui_data(mmsi, lat, lon, heading)
        except Exception as e:
            print(f"[{source}] Error extracting MAVLink AIS_VESSEL data: {e}")

def handle_nmea_sentence(sentence, source):
    try:
        decoded = decode(sentence).asdict()
        print(f"[{source}] Decoded dict: {decoded}")
        mmsi = decoded.get('mmsi')
        lat = decoded.get('y')  # latitude or None
        lon = decoded.get('x')  # longitude or None
        heading = decoded.get('heading')

        # If heading missing or 'N/A', convert to None for consistent UI
        if heading == 'N/A' or heading is None:
            heading = None

        update_ui_data(mmsi, lat, lon, heading)
    except Exception as e:
        print(f"[{source}] Failed to parse NMEA sentence: {e} Sentence: {sentence!r}")

def mavlink_parser_worker(data_queue, source):
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
                    handle_mavlink_message(msg, source)
        except Empty:
            continue
        except Exception as e:
            print(f"[{source}] MAVLink parsing error: {e}")

def tcp_client_handler(client_sock, client_addr):
    source = f"TCP {client_addr}"
    print(f"[{source}] Connected")
    data_queue = Queue()

    mav_thread = threading.Thread(target=mavlink_parser_worker, args=(data_queue, source), daemon=True)
    mav_thread.start()

    buffer = b""

    try:
        while not shutdown_event.is_set():
            data = client_sock.recv(BUFFER_SIZE)
            if not data:
                print(f"[{source}] Client disconnected")
                break

            buffer += data

            try:
                text = buffer.decode('utf-8')
                while '\r\n' in text:
                    sentence, text = text.split('\r\n', 1)
                    sentence = sentence.strip()
                    if sentence:
                        if sentence.startswith('!') or sentence.startswith('$'):
                            handle_nmea_sentence(sentence, source)
                        else:
                            data_queue.put(sentence.encode('utf-8'))
                buffer = text.encode('utf-8')
            except UnicodeDecodeError:
                data_queue.put(buffer)
                buffer = b""

    except Exception as e:
        print(f"[{source}] TCP Client handler error: {e}")
    finally:
        client_sock.close()
        print(f"[{source}] Connection closed")
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
            source = f"UDP {addr}"

            try:
                text = data.decode('utf-8')
                if text.startswith('!') or text.startswith('$'):
                    handle_nmea_sentence(text.strip(), source)
                else:
                    for b in data:
                        msg = mav.parse_char(chr(b))
                        if msg:
                            handle_mavlink_message(msg, source)
            except UnicodeDecodeError:
                for b in data:
                    msg = mav.parse_char(chr(b))
                    if msg:
                        handle_mavlink_message(msg, source)

        except socket.timeout:
            continue
        except Exception as e:
            print(f"[UDP] Server error: {e}")

    server.close()
    print("[UDP] Server shutdown")

def signal_handler(sig, frame):
    print("Shutdown signal received. Exiting...")
    shutdown_event.set()

def start_network_threads():
    tcp_thread = threading.Thread(target=tcp_server, daemon=True, name="TCPServer")
    udp_thread = threading.Thread(target=udp_server, daemon=True, name="UDPServer")

    tcp_thread.start()
    udp_thread.start()

    return tcp_thread, udp_thread

class AISDisplayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AIS Receiver")
        self.geometry("320x160")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.label_mmsi = tk.Label(self, text="MMSI: N/A", font=("Arial", 12))
        self.label_mmsi.pack(pady=5)

        self.label_lat = tk.Label(self, text="Latitude: N/A", font=("Arial", 12))
        self.label_lat.pack(pady=5)

        self.label_lon = tk.Label(self, text="Longitude: N/A", font=("Arial", 12))
        self.label_lon.pack(pady=5)

        self.label_heading = tk.Label(self, text="Heading: N/A", font=("Arial", 12))
        self.label_heading.pack(pady=5)

        self.update_ui()

    def update_ui(self):
        try:
            data = ui_queue.get_nowait()
            print("Dequeued data:", data)
            self.label_mmsi.config(text=f"MMSI: {data['mmsi']}")
            lat_text = f"{data['lat']:.6f}" if data['lat'] is not None else "N/A"
            lon_text = f"{data['lon']:.6f}" if data['lon'] is not None else "N/A"
            self.label_lat.config(text=f"Latitude: {lat_text}")
            self.label_lon.config(text=f"Longitude: {lon_text}")
            self.label_heading.config(text=f"Heading: {data['heading']}")
        except Empty:
            pass
        except Exception as e:
            print("UI update error:", e)
        finally:
            self.after(100, self.update_ui)

    def on_close(self):
        shutdown_event.set()
        self.destroy()

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Starting AIS TCP and UDP Receiver...")
    tcp_thread, udp_thread = start_network_threads()

    app = AISDisplayApp()
    app.mainloop()

    print("Waiting for server threads to finish...")
    tcp_thread.join(timeout=3)
    udp_thread.join(timeout=3)
    print("Shutdown complete.")

if __name__ == "__main__":
    main()
