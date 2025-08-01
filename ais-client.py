import socket
import time
from pymavlink.dialects.v20 import common as mavlink2

# CONFIGURATION
SEND_PROTOCOL = 'tcp'  # 'tcp' or 'udp'
TARGET_IP = '127.0.0.1'
TARGET_PORT = 1280  # Match the receiver's TCP or UDP port
SEND_NMEA = True   # True = Send NMEA, False = Send MAVLink AIS_VESSEL

# NMEA Sample AIS Sentences
nmea_sentences = [
    "!AIVDM,1,1,,A,13u?et@01G?Q@<L1R0<:wvP00000,0*0D\r\n",
    "!AIVDM,1,1,,A,15N:;P0P00PD;88MD5MTDww@0<2Q,0*5C\r\n"
]

def send_nmea(sock, is_udp=False):
    while True:
        for sentence in nmea_sentences:
            data = sentence.encode('utf-8')
            if is_udp:
                sock.sendto(data, (TARGET_IP, TARGET_PORT))
            else:
                sock.sendall(data)
            print(f"[SENDER] Sent NMEA: {sentence.strip()}")
            time.sleep(2)

def send_mavlink(sock, is_udp=False):
    mav = mavlink2.MAVLink(sock)
    mav.srcSystem = 1

    # Define dronefleet style fields
    mmsi = 123456789
    lat = int(35.0767086 * 1e7)
    lon = int(129.0921086 * 1e7)
    cog = int(180.0 * 100)     # centi-degrees
    sog = int(12.0 * 100)     # centiknots
    heading = 175             # degrees
    rot = 0
    nav_status = 0
    vessel_type = 70
    callsign = "CALL123"
    name = "VESSEL1"
    dim_a = 0
    dim_b = 0
    dim_c = 0
    dim_d = 0
    eta = 0
    draught = 0

    while True:
        packet = mav.ais_vessel_encode(
            mmsi,
            lat,
            lon,
            cog,
            sog,
            heading,
            rot,
            nav_status,
            vessel_type,
            callsign,
            name,
            dim_a,
            dim_b,
            dim_c,
            dim_d,
            eta,
            draught
        )
        data = packet.pack(mav)
        if is_udp:
            sock.sendto(data, (TARGET_IP, TARGET_PORT))
        else:
            sock.sendall(data)
        print("[SENDER] Sent MAVLink AIS_VESSEL")
        time.sleep(2)

def tcp_sender():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((TARGET_IP, TARGET_PORT))
        print(f"[SENDER] TCP connected to {TARGET_IP}:{TARGET_PORT}")
        if SEND_NMEA:
            send_nmea(sock)
        else:
            send_mavlink(sock)

def udp_sender():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        print(f"[SENDER] UDP sending to {TARGET_IP}:{TARGET_PORT}")
        if SEND_NMEA:
            send_nmea(sock, is_udp=True)
        else:
            send_mavlink(sock, is_udp=True)

def main():
    print(f"[SENDER] Starting simulation: {'NMEA' if SEND_NMEA else 'MAVLink AIS_VESSEL'} over {SEND_PROTOCOL.upper()}")
    if SEND_PROTOCOL == 'tcp':
        tcp_sender()
    elif SEND_PROTOCOL == 'udp':
        udp_sender()
    else:
        print("Invalid SEND_PROTOCOL. Use 'tcp' or 'udp'.")

if __name__ == "__main__":
    main()