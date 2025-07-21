import socket
import threading
import logging
import time
from pymavlink import mavutil

TCP_IP = "0.0.0.0"
TCP_PORT = 10111

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    filename='ais_receiver.log',
    filemode='w'
)

ais_buffer = []

def handle_client(client_sock, client_addr):
    connection_id = f"{client_addr[0]}:{client_addr[1]}"
    logging.info(f"[{connection_id}] Connection accepted")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{connection_id}] Connection accepted")

    # Create mavlink connection for reading from socket fd
    master = mavutil.mavlink_connection('fd', source_system=255)
    master.fd = client_sock.fileno()

    try:
        while True:
            msg = master.recv_match(type='AIS_VESSEL', blocking=True, timeout=1)
            if msg:
                ais_data = {
                    'MMSI': msg.MMSI,
                    'Lat': msg.lat / 1e7,
                    'Lon': msg.lon / 1e7,
                    'COG': msg.COG / 1e2,
                    'Heading': msg.heading / 1e2,
                    'Speed': msg.SOG / 1e2,
                    'Name': msg.name.strip(),
                    'Callsign': msg.callsign.strip(),
                    'Type': msg.vessel_type
                }
                ais_entry = (
                    f"MMSI {ais_data['MMSI']}, Lat {ais_data['Lat']:.6f}, Lon {ais_data['Lon']:.6f}, "
                    f"Speed {ais_data['Speed']:.1f} kn, Heading {ais_data['Heading']:.1f} deg, "
                    f"Name {ais_data['Name']}, Callsign {ais_data['Callsign']}, Type {ais_data['Type']}"
                )
                ais_buffer.append(ais_entry)
                logging.info(f"[{connection_id}] AIS_VESSEL: {ais_entry}")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{connection_id}] AIS_VESSEL: {ais_entry}")

            else:
                # No message received, loop to check again
                continue

    except Exception as e:
        logging.error(f"[{connection_id}] Client error: {e}")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{connection_id}] Client error: {e}")
    finally:
        client_sock.close()
        logging.info(f"[{connection_id}] Connection closed")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{connection_id}] Connection closed")

def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((TCP_IP, TCP_PORT))
    sock.listen(5)

    logging.info(f"Server listening on {TCP_IP}:{TCP_PORT}")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server listening on {TCP_IP}:{TCP_PORT}")

    try:
        while True:
            client_sock, client_addr = sock.accept()
            threading.Thread(target=handle_client, args=(client_sock, client_addr), daemon=True).start()
    except Exception as e:
        logging.error(f"Server error: {e}")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    run_server()
