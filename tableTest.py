from picamera2 import Picamera2
from PIL import Image
import time
import base64
import os
import serial
import pynmea2
from groq import Groq
from datetime import datetime
from supabase import create_client
import threading
import queue

SUPABASE_URL = "hidden"
SUPABASE_KEY = "hidden"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = Groq(api_key="hidden ")
photos_dir = "/home/sid/BikeProject/photos"
os.makedirs(photos_dir, exist_ok=True)

gps_serial = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

photo_queue = queue.Queue()

def get_gps():
    for _ in range(20):
        try:
            line = gps_serial.readline().decode("ascii", errors="replace")
            if line.startswith("$GPRMC") or line.startswith("$GPGGA") or line.startswith("$GNRMC") or line.startswith("$GNGGA"):
                msg = pynmea2.parse(line)
                if hasattr(msg, "latitude") and msg.latitude != 0:
                    return msg.latitude, msg.longitude
        except:
            pass
    return None, None

def capture_loop(cam):
    last_capture = 0
    while True:
        now = time.time()
        if now - last_capture >= 5:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_path = f"{photos_dir}/{timestamp}.jpg"
            cam.capture_file(photo_path, format="jpeg")

            img = Image.open(photo_path)
            img = img.rotate(180)
            img.save(photo_path)

            lat, lon = get_gps()
            print(f"photo taken — GPS: {lat}, {lon}")

            photo_queue.put((timestamp, photo_path, lat, lon))
            last_capture = now
        time.sleep(0.1)


def process_loop():
    while True:
        timestamp, photo_path, lat, lon = photo_queue.get()

        with open(photo_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        with open(photo_path, "rb") as f:
            supabase.storage.from_("photos").upload(
                f"{timestamp}.jpg",
                f,
                {"content-type": "image/jpeg"}
            )

        photo_url = supabase.storage.from_("photos").get_public_url(f"{timestamp}.jpg")

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            reasoning_effort="low",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what you see in this photo in 2-3 short bullet points, as if you were telling a friend what's in it. Don't mention panels, collages, or image structure. Just describe the content naturally. Do not show your thinking or reasoning process, only return the final bullet points."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }]
        )

        description = response.choices[0].message.content
        print(description)

        supabase.table("PiProject").insert({
            "timestamp": timestamp,
            "description": description,
            "image_url": photo_url,
            "latitude": lat,
            "longitude": lon,
        }).execute()

        print("logged to Supabase")
        photo_queue.task_done()

cam = Picamera2()
cam.start()
time.sleep(2)

capture_thread = threading.Thread(target=capture_loop, args=(cam,), daemon=True)
process_thread = threading.Thread(target=process_loop, daemon=True)

capture_thread.start()
process_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping...")
finally:
    cam.stop()
    gps_serial.close()
    print("Done.")