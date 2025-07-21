import socket
import time

# Mission Planner UDP settings for AIS input
UDP_IP = "127.0.0.1"  # Mission Planner's IP (localhost if running locally)
UDP_PORT = 10110      # Mission Planner's default AIS listening port

# AIS NMEA sentences
nmea_sentences = [
    # Type 1: Position Report (MMSI: 123456789, Lat: 37.1234567, Lon: -122.1234567)
    "!AIVDM,1,1,,A,13u?etPv2;2ab7K6S9M2<Nl5J6E,0*2E\r\n",
    # Type 5: Static Data (MMSI: 123456789, Vessel Name: VESSEL1, Callsign: CALL123)
    "!AIVDM,2,1,1,A,53u?et@28I8L4@@6222222222222220H53H0`4lU1@E=4r2`0H0,0*4B\r\n",
    "!AIVDM,2,2,1,A,0000000000000000000,2*2D\r\n"
]

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    while True:
        for sentence in nmea_sentences:
            sock.sendto(sentence.encode(), (UDP_IP, UDP_PORT))
            print(f"Sent AIS NMEA: {sentence.strip()} to {UDP_IP}:{UDP_PORT}")
            time.sleep(1)  # Send each sentence 1 second apart
except KeyboardInterrupt:
    print("Stopped sending NMEA")
finally:
    sock.close()