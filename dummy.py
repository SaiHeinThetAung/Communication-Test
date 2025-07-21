import tkinter as tk
from queue import Queue, Empty
import threading
import time

ui_queue = Queue()

def generate_test_data():
    i = 0
    while True:
        ui_queue.put({
            'mmsi': 123456789 + i,
            'lat': 37.0 + i * 0.001,
            'lon': -122.0 - i * 0.001,
            'heading': (i * 10) % 360
        })
        i += 1
        time.sleep(1)

class AISDisplayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AIS Receiver Test")
        self.geometry("300x150")

        self.label_mmsi = tk.Label(self, text="MMSI: N/A", font=("Arial", 12))
        self.label_mmsi.pack(pady=5)

        self.label_lat = tk.Label(self, text="Latitude: N/A", font=("Arial", 12))
        self.label_lat.pack(pady=5)

        self.label_lon = tk.Label(self, text="Longitude: N/A", font=("Arial", 12))
        self.label_lon.pack(pady=5)

        self.label_heading = tk.Label(self, text="Heading: N/A", font=("Arial", 12))
        self.label_heading.pack(pady=5)

        self.update_ui()

    def update_ui(self):
        try:
            data = ui_queue.get_nowait()
            print("Dequeued data:", data)
            self.label_mmsi.config(text=f"MMSI: {data['mmsi']}")
            self.label_lat.config(text=f"Latitude: {data['lat']:.6f}")
            self.label_lon.config(text=f"Longitude: {data['lon']:.6f}")
            self.label_heading.config(text=f"Heading: {data['heading']}")
        except Empty:
            pass
        self.after(100, self.update_ui)

if __name__ == "__main__":
    threading.Thread(target=generate_test_data, daemon=True).start()
    app = AISDisplayApp()
    app.mainloop()
