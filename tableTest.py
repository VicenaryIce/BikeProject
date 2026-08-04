import sqlite3
from picamera2 import Picamera2
import time
import base64
import os
from groq import Groq
from datetime import datetime

client = Groq(api_key="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")

photos_dir = "/home/sid/Desktop/BikeProject/photos"
os.makedirs(photos_dir, exist_ok=True)

conn = sqlite3.connect("/home/sid/Desktop/BikeProject/table3.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        description TEXT NOT NULL,
        image_path TEXT
    )
""")

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

            with open(photo_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            response = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in 2-3 bullet points. Be very concise."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }]
            )

            print(response.choices[0].message.content)
            cursor.execute(
                "INSERT INTO photos (timestamp, description, image_path) VALUES (?, ?, ?)",
                (timestamp, response.choices[0].message.content, photo_path)
            )
            conn.commit()
            start_time = time.time()
        time.sleep(0.1)
finally:
    conn.close()
    cam.stop()
    print("Database connection and camera closed safely.")