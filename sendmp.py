# send_nmea_to_mp.py
import socket
import time

UDP_IP = '127.0.0.1'  # Replace with Mission Planner's IP if on another machine
UDP_PORT = 10110      # Mission Planner's AIS listening port

# Example NMEA AIS sentence (Type 1 Position Report)
nmea_ais_sentence = "!AIVDM,1,1,,A,13u?etPv2;2ab7K6S9M2<Nl5J6E,0*2E\r\n"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    while True:
        sock.sendto(nmea_ais_sentence.encode(), (UDP_IP, UDP_PORT))
        print(f"Sent AIS NMEA to Mission Planner on {UDP_IP}:{UDP_PORT}")
        time.sleep(2)  # Send every 2 seconds
except KeyboardInterrupt:
    print("Stopped sending NMEA")
finally:
    sock.close()
