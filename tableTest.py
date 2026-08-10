import sqlite3
from picamera2 import Picamera2
import time
import base64
import os
import serial
import pynmea2
from groq import Groq
from datetime import datetime

client = Groq(api_key="hello")
photos_dir = "/home/sid/Desktop/BikeProject/photos"
os.makedirs(photos_dir, exist_ok=True)

conn = sqlite3.connect("/home/sid/Desktop/BikeProject/table3.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        description TEXT NOT NULL,
        image_path TEXT,
        latitude REAL,
        longitude REAL
    )
""")

gps_serial = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

def get_gps():
    for _ in range(20):
        try:
            line = gps_serial.readline().decode("ascii", errors="replace")
            if line.startswith("$GPRMC") or line.startswith("$GPGGA"):
                msg = pynmea2.parse(line)
                if hasattr(msg, "latitude") and msg.latitude != 0:
                    return msg.latitude, msg.longitude
        except:
            pass
    return None, None

cam = Picamera2()
cam.start()
time.sleep(2)
start_time = time.time()

try:
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time >= 5:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_path = f"{photos_dir}/{timestamp}.jpg"
            cam.capture_file(photo_path, format="jpeg")
            print("photo taken")

            lat, lon = get_gps()
            print(f"GPS: {lat}, {lon}")

            with open(photo_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            response = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe what you see in this photo in 2-3 short bullet points, as if you were telling a friend what's in it. Don't mention panels, collages, or image structure. Just describe the content naturally. Do not show your thinking or reasoning process, only return the final bullet points."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }]
            )

            print(response.choices[0].message.content)
            cursor.execute(
                "INSERT INTO photos (timestamp, description, image_path, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
                (timestamp, response.choices[0].message.content, photo_path, lat, lon)
            )
            conn.commit()
            start_time = time.time()
        time.sleep(0.1)
finally:
    conn.close()
    cam.stop()
    gps_serial.close()
    print("Database connection and camera closed safely.")