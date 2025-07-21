from pymavlink import mavutil
import time

# Mission Planner TCP server settings
TCP_IP = "127.0.0.1"  # Mission Planner's IP (localhost if running locally)
TCP_PORT = 14550       # Default MAVLink TCP port in Mission Planner

# Create a TCP MAVLink connection
def create_tcp_connection(ip, port):
    try:
        # Create a TCP connection using pymavlink's tcp: device string
        device = f"tcp:{ip}:{port}"
        print(f"Connecting to Mission Planner at {device}...")
        mav = mavutil.mavlink_connection(device)
        # Send a heartbeat to prompt Mission Planner
        mav.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0
        )
        print("Connected successfully and heartbeat sent!")
        return mav
    except Exception as e:
        print(f"Failed to connect to {ip}:{port}: {e}")
        return None

# Process MAVLink messages
def process_mavlink_messages(mav):
    try:
        while True:
            # Receive raw data for debugging
            data = mav.recv()
            if data:
                print(f"Raw data received: {data}")
            # Receive MAVLink message
            msg = mav.recv_msg()
            if msg is None:
                continue
            print(f"Received {msg.get_type()} message")
            # Check for AIS_VESSEL message
            if msg.get_type() == "AIS_VESSEL":
                print("\nReceived AIS_VESSEL message:")
                print(f"  MMSI: {msg.MMSI}")
                print(f"  Latitude: {msg.lat / 1e7} degrees")
                print(f"  Longitude: {msg.lon / 1e7} degrees")
                print(f"  COG: {msg.COG / 100.0} degrees")  # Course over ground
                print(f"  SOG: {msg.SOG / 100.0} knots")   # Speed over ground
                print(f"  Heading: {msg.heading / 100.0} degrees")
                print(f"  Vessel Type: {msg.vessel_type}")
                print(f"  Callsign: {msg.callsign.strip()}")
                print(f"  Name: {msg.name.strip()}")
    except KeyboardInterrupt:
        print("\nStopped receiving MAVLink messages")
    except Exception as e:
        print(f"Error processing MAVLink messages: {e}")
    finally:
        mav.close()

def main():
    # Connect to Mission Planner's TCP server
    mav = create_tcp_connection(TCP_IP, TCP_PORT)
    if mav is None:
        return
    
    # Process incoming MAVLink messages
    process_mavlink_messages(mav)

if __name__ == "__main__":
    main()