import socket
import threading
from pymavlink import mavutil
from pyais import decode

# Configuration
TCP_IP = "127.0.0.1"
TCP_PORT = 5000  # Set your desired TCP listening port
UDP_IP = "0.0.0.0"
UDP_PORT = 5001  # Set your desired UDP listening port

BUFFER_SIZE = 1024

def handle_mavlink_data(data, source):
    try:
        mav = mavutil.mavlink_connection('fd', source_system=255)
        mav.write(data)
        msg = mav.recv_msg()
        if msg and msg.get_type() == 'AIS_VESSEL':
            print(f"\n[{source}] MAVLink AIS_VESSEL Received:")
            print(f" MMSI: {msg.mmsi}")
            print(f" Lat: {msg.lat / 1e7:.6f}")
            print(f" Lon: {msg.lon / 1e7:.6f}")
            print(f" COG: {msg.cog / 100:.2f}°")
            print(f" SOG: {msg.speed / 100:.2f} knots")
            print(f" Heading: {msg.heading}")
            print(f" Vessel Type: {msg.type}")
            print(f" Callsign: {msg.callsign.strip()}")
            print(f" Name: {msg.name.strip()}")
            
    except Exception as e:
        print(f"[{source}] MAVLink Parse Error: {e}")

def handle_nmea_sentence(sentence, source):
    try:
        decoded = decode(sentence).asdict()
        print(f"\n[{source}] NMEA Sentence Decoded:")
        print(f" MMSI: {decoded.get('mmsi')}")
        print(f" Lat: {decoded.get('y')}")
        print(f" Lon: {decoded.get('x')}")
        print(f" SOG: {decoded.get('speed')} knots")
        print(f" COG: {decoded.get('course')} degrees")
        print(f" Ship Name: {decoded.get('name')}")
        print(f" Callsign: {decoded.get('callsign')}")
        print(f" Type: {decoded.get('ship_type')}")
        print(f" Heading: {decoded.get('heading', 'N/A')}")

    except Exception as e:
        print(f"[{source}] NMEA Parse Error: {e}, Sentence: {sentence!r}")

def tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((TCP_IP, TCP_PORT))
    server.listen(5)
    print(f"[TCP] Listening on {TCP_IP}:{TCP_PORT}")

    while True:
        client_sock, client_addr = server.accept()
        threading.Thread(target=handle_tcp_client, args=(client_sock, client_addr), daemon=True).start()

def handle_tcp_client(client_sock, client_addr):
    source = f"TCP {client_addr}"
    print(f"[TCP] Connection from {source}")
    buffer = b""

    try:
        while True:
            data = client_sock.recv(BUFFER_SIZE)
            if not data:
                break
            buffer += data
            try:
                buffer_str = buffer.decode('utf-8', errors='ignore')
                while "\r\n" in buffer_str:
                    sentence, buffer_str = buffer_str.split("\r\n", 1)
                    if sentence:
                        handle_nmea_sentence(sentence, source)
                buffer = buffer_str.encode('utf-8')
            except UnicodeDecodeError:
                handle_mavlink_data(buffer, source)
                buffer = b""
    except Exception as e:
        print(f"[TCP] Error with {source}: {e}")
    finally:
        client_sock.close()
        print(f"[TCP] Connection closed: {source}")

def udp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((UDP_IP, UDP_PORT))
    print(f"[UDP] Listening on {UDP_IP}:{UDP_PORT}")

    while True:
        data, addr = server.recvfrom(BUFFER_SIZE)
        source = f"UDP {addr}"
        try:
            decoded_text = data.decode('utf-8', errors='ignore')
            if decoded_text.startswith('!AIVDM') or decoded_text.startswith('!'):
                handle_nmea_sentence(decoded_text, source)
            else:
                handle_mavlink_data(data, source)
        except UnicodeDecodeError:
            handle_mavlink_data(data, source)

def main():
    print("Starting AIS TCP and UDP Receiver...")

    threading.Thread(target=tcp_server, daemon=True).start()
    threading.Thread(target=udp_server, daemon=True).start()

    # Keep main thread alive
    while True:
        pass

if __name__ == "__main__":
    main()
