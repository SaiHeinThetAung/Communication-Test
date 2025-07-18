from pymavlink import mavutil

master = mavutil.mavlink_connection('tcp:127.0.0.1:14550')  # MP TCP MAVLink
master.wait_heartbeat()
print("Connected to Mission Planner via MAVLink")

while True:
    msg = master.recv_match(type='AIS_VESSEL', blocking=True, timeout=5)
    if msg:
        print(f"Received AIS_VESSEL: MMSI {msg.mmsi}, Lat {msg.lat / 1e7}, Lon {msg.lon / 1e7}")
    else:
        print("No AIS_VESSEL received")
