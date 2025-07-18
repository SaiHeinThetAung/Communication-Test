import threading
import time
import logging
from pymavlink import mavutil

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s: %(message)s', filename='mavlink_ais_real_20250717.log')

# Global buffers
mavlink_buffer = {}
ais_buffer = []

# MAVLink receiver function for multiple connections
def receive_mavlink_data(ip, port, connection_id):
    global mavlink_buffer, ais_buffer
    try:
        logging.info(f"[{connection_id}] Connecting to MAVLink at tcp:{ip}:{port}")
        connection = mavutil.mavlink_connection(f'tcp:{ip}:{port}', retries=5)

        logging.info(f"[{connection_id}] Waiting for heartbeat")
        connection.wait_heartbeat(timeout=10)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{connection_id}] MAVLink Connected: System ID {connection.target_system}, Component ID {connection.target_component}")
        logging.info(f"[{connection_id}] Connected: System ID {connection.target_system}, Component ID {connection.target_component}")

        connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0
        )
        logging.info(f"[{connection_id}] Sent GCS heartbeat")

        while True:
            msg = connection.recv_match(blocking=True, timeout=1.0)
            if not msg:
                logging.debug(f"[{connection_id}] No MAVLink message received in last second")
                continue

            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            logging.debug(f"[{connection_id}] Received MAVLink message: {msg.get_type()}")

            if msg.get_type() == 'HEARTBEAT':
                mavlink_buffer[f'{connection_id}_heartbeat'] = f" Mode {msg.custom_mode}, Status {msg.system_status}"

            elif msg.get_type() == 'GLOBAL_POSITION_INT':
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt = msg.alt / 1e3
                mavlink_buffer[f'{connection_id}_position'] = f"Lat {lat:.6f}, Lon {lon:.6f}, Alt {alt:.2f}m"

            elif msg.get_type() == 'ATTITUDE':
                mavlink_buffer[f'{connection_id}_attitude'] = f"Roll {msg.roll:.2f}, Pitch {msg.pitch:.2f}, Yaw {msg.yaw:.2f}"

            elif msg.get_type() == 'AIS_VESSEL':
                logging.debug(f"[{connection_id}] Received AIS_VESSEL: {msg.to_dict()}")
                ais_data = {
                    'MMSI': msg.mmsi,
                    'Lat': msg.lat / 1e7,
                    'Lon': msg.lon / 1e7,
                    'COG': msg.cog / 1e2,
                    'Heading': msg.heading,
                    'Speed': msg.speed / 1e2,
                    'Name': msg.name.strip(),
                    'Callsign': msg.callsign.strip(),
                    'Type': msg.type
                }
                ais_buffer.append(
                    f"MMSI {ais_data['MMSI']}, Lat {ais_data['Lat']:.6f}, Lon {ais_data['Lon']:.6f}, "
                    f"Speed {ais_data['Speed']:.1f} kn, Heading {ais_data['Heading']} deg, "
                    f"Name {ais_data['Name']}, Callsign {ais_data['Callsign']}, Type {ais_data['Type']}"
                )

    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{connection_id}] MAVLink Error: {e}")
        logging.error(f"[{connection_id}] MAVLink Error: {e}")
    finally:
        try:
            connection.close()
            logging.info(f"[{connection_id}] MAVLink connection closed")
        except Exception:
            pass

# Printer function
def print_data():
    global mavlink_buffer, ais_buffer
    last_print = 0
    while True:
        if time.time() - last_print >= 2:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] --- Data Update ---")
            if not mavlink_buffer:
                print(f"[{timestamp}] MAVLink: No data received")
            for key, value in mavlink_buffer.items():
                print(f"[{timestamp}] MAVLink {key}: {value}")
            if ais_buffer:
                print(f"[{timestamp}] AIS: {ais_buffer[-1]}")
            else:
                print(f"[{timestamp}] AIS: No AIS data received yet")
            last_print = time.time()
        time.sleep(0.1)

# Main function
def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting MAVLink and AIS receivers")
    logging.info("Starting MAVLink and AIS receivers")

    # Define multiple MAVLink TCP connections: (IP, PORT, IDENTIFIER)
    mavlink_connections = [
        ('192.168.0.182', 5762, 'MP1'),
        ('192.168.0.183', 5763, 'MP2'),
        ('192.168.0.184', 5764, 'MP3'),
    ]

    # Start MAVLink threads
    for ip, port, conn_id in mavlink_connections:
        threading.Thread(target=receive_mavlink_data, args=(ip, port, conn_id), daemon=True).start()

    # Start printer thread
    print_thread = threading.Thread(target=print_data, daemon=True)
    print_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stopping all receivers")
        logging.info("Stopping all receivers")

if __name__ == "__main__":
    main()
