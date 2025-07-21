import socket
import time
import threading
from pymavlink import mavutil

def heartbeat_sender(stop_event):
    while not stop_event.is_set():
        # In this manual approach, heartbeat is not sent via mavutil connection
        # So you can implement if you want by packing messages yourself.
        time.sleep(1)

def send_ais_vessel_messages(sock, stop_event):
    mav = mavutil.mavlink.MAVLink(None)  # None for no file object, we'll pack manually
    mav.srcSystem = 1
    mav.srcComponent = 1

    while not stop_event.is_set():
        try:
            # Create message
            msg = mav.ais_vessel_send(
                MMSI=123456789,
                lat=int(37.123456 * 1e7),
                lon=int(-122.123456 * 1e7),
                COG=int(180.0 * 100),
                SOG=int(10.0 * 100),
                heading=int(175.0 * 100),
                vessel_type=70,
                callsign="CALL123",
                name="VESSEL1"
            )
            # Pack message to bytes
            raw = msg.pack(mav)
            sock.sendall(raw)
            print(f"Sent AIS_VESSEL MAVLink message ({len(raw)} bytes)")
            time.sleep(1)
        except Exception as e:
            print(f"Error sending AIS message: {e}")
            break

def main_sender():
    TCP_IP = "127.0.0.1"
    TCP_PORT = 10111

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    stop_event = threading.Event()

    try:
        print(f"Connecting to {TCP_IP}:{TCP_PORT}...")
        sock.connect((TCP_IP, TCP_PORT))
        print("Connected!")

        hb_thread = threading.Thread(target=heartbeat_sender, args=(stop_event,), daemon=True)
        hb_thread.start()

        send_ais_vessel_messages(sock, stop_event)

    except KeyboardInterrupt:
        print("Sender interrupted by user")
    except Exception as e:
        print(f"Sender error: {e}")
    finally:
        stop_event.set()
        sock.close()
        print("Sender stopped.")

if __name__ == "__main__":
    main_sender()
