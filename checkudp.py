import socket
import time

UDP_IP = "127.0.0.1"
UDP_PORT = 10110

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)

try:
    sock.bind((UDP_IP, UDP_PORT))
    print(f"Listening for UDP packets on {UDP_IP}:{UDP_PORT}...")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            print(f"Received UDP packet from {addr}: {data.decode().strip()}")
        except socket.timeout:
            print("No data received in the last 5 seconds.")
except Exception as e:
    print(f"Error binding to port {UDP_PORT}: {e}")
finally:
    sock.close()
    