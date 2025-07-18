import re
import time
import os
import threading
from pymavlink import mavutil
from datetime import datetime

def find_latest_log_file(directory, extension='.log'):
    log_files = [f for f in os.listdir(directory) if f.endswith(extension)]
    if not log_files:
        return None
    log_files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
    return os.path.join(directory, log_files[0])

def parse_log_file(file_path):
    logs = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip():
                    line_clean = re.sub(r'home_location=\{.*?\},\s?', '', line.strip())
                    line_clean = re.sub(r'waypoints=\[.*?\],\s?', '', line_clean)

                    raw = line_clean.strip('{}')
                    parts = re.split(r',\s(?=\w+=)', raw)

                    data_dict = {}
                    for part in parts:
                        if '=' not in part:
                            continue
                        key, value = part.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        if value.lower() == 'null':
                            data_dict[key] = None
                        elif re.match(r'^-?\d+\.\d+$', value):
                            data_dict[key] = float(value)
                        elif re.match(r'^-?\d+$', value):
                            data_dict[key] = int(value)
                        else:
                            data_dict[key] = value
                    logs.append(data_dict)
        print(f"Parsed {len(logs)} log entries from '{file_path}'.")
        return logs
    except Exception as e:
        print(f"Failed to parse log file: {e}")
        return []

def heartbeat_sender(master, stop_event):
    while not stop_event.is_set():
        master.mav.heartbeat_send(
            type=21,  # QuadPlane
            autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode=0,
            custom_mode=0,
            system_status=mavutil.mavlink.MAV_STATE_ACTIVE,
            mavlink_version=3
        )
        time.sleep(1)

def send_sys_status(master):
    master.mav.sys_status_send(
        onboard_control_sensors_present=0,
        onboard_control_sensors_enabled=0,
        onboard_control_sensors_health=0,
        load=500,
        voltage_battery=12000,
        current_battery=-1,
        battery_remaining=80,
        drop_rate_comm=0,
        errors_comm=0,
        errors_count1=0,
        errors_count2=0,
        errors_count3=0,
        errors_count4=0
    )

def safe_float(val):
    try:
        return float(str(val).strip('}]} '))
    except:
        return 0.0

def send_log_messages(master, logs):
    prev_timestamp = None
    deg_to_rad = 3.141592653589793 / 180

    for log_entry in logs:
        try:
            current_timestamp = datetime.fromisoformat(log_entry['timestamp']).timestamp()
            if prev_timestamp is not None:
                delay = current_timestamp - prev_timestamp
                if delay > 0:
                    time.sleep(delay)
            prev_timestamp = current_timestamp
        except:
            time.sleep(1)

        master.mav.global_position_int_send(
            time_boot_ms=int(safe_float(log_entry['time_in_air']) * 1000),
            lat=int(safe_float(log_entry['lat']) * 1e7),
            lon=int(safe_float(log_entry['lon']) * 1e7),
            alt=int(safe_float(log_entry['alt']) * 1000),
            relative_alt=int(safe_float(log_entry['alt']) * 1000),
            vx=int(safe_float(log_entry['ground_speed']) * 100),
            vy=0,
            vz=int(safe_float(log_entry['vertical_speed']) * 100),
            hdg=int(safe_float(log_entry['heading']) * 100)
        )

        master.mav.attitude_send(
            time_boot_ms=int(safe_float(log_entry['time_in_air']) * 1000),
            roll=safe_float(log_entry['roll']) * deg_to_rad,
            pitch=safe_float(log_entry['pitch']) * deg_to_rad,
            yaw=safe_float(log_entry['yaw']) * deg_to_rad,
            rollspeed=0,
            pitchspeed=0,
            yawspeed=0
        )

        master.mav.vfr_hud_send(
            airspeed=safe_float(log_entry['airspeed']),
            groundspeed=safe_float(log_entry['ground_speed']),
            heading=int(safe_float(log_entry['heading'])),
            throttle=int(safe_float(log_entry['ch3percent'])),
            alt=safe_float(log_entry['alt']),
            climb=safe_float(log_entry['vertical_speed'])
        )

        master.mav.nav_controller_output_send(
            nav_roll=safe_float(log_entry['roll']),
            nav_pitch=safe_float(log_entry['pitch']),
            nav_bearing=int(safe_float(log_entry['heading'])),
            target_bearing=int(safe_float(log_entry['target_heading'])),
            wp_dist=int(safe_float(log_entry['wp_dist'])),
            alt_error=0,
            aspd_error=0,
            xtrack_error=0
        )

        print(f"Sent MAVLink messages for timestamp {log_entry['timestamp']}")

def main():
    log_folder = '.'
    log_file_path = find_latest_log_file(log_folder)

    if not log_file_path:
        print("No .log file found. Exiting.")
        return

    print(f"Using log file: {log_file_path}")
    logs = parse_log_file(log_file_path)
    if not logs:
        print("No logs parsed, exiting.")
        return

    gcs_ip = '127.0.0.1'
    port = 15001
    system_id = 1
    component_id = 1

    master = mavutil.mavlink_connection(
        f'udpout:{gcs_ip}:{port}',
        source_system=system_id,
        source_component=component_id
    )
    print(f"Connected to Mission Planner at {gcs_ip}:{port}")

    master.mav.heartbeat_send(
        type=21,
        autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
        base_mode=0,
        custom_mode=0,
        system_status=mavutil.mavlink.MAV_STATE_ACTIVE,
        mavlink_version=3
    )
    print("Initial heartbeat sent")

    send_sys_status(master)
    print("SYS_STATUS sent")

    stop_event = threading.Event()
    hb_thread = threading.Thread(target=heartbeat_sender, args=(master, stop_event), daemon=True)
    hb_thread.start()
    print("Heartbeat thread started")

    try:
        send_log_messages(master, logs)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        stop_event.set()
        hb_thread.join()
        print("Heartbeat thread stopped. Exiting.")

if __name__ == '__main__':
    main()