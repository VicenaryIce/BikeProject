import base64
import glob
import json
import os
import queue
import signal
import threading
import time
from datetime import datetime

import pynmea2
import serial
from groq import Groq
from libcamera import controls, Transform
from picamera2 import Picamera2
from supabase import create_client

SUPABASE_URL = "https://mgvxkmhgqhtzclsykanh.supabase.co"
SUPABASE_KEY = "#####"


GROQ_API_KEY = "#######"
MODEL = "qwen/qwen3.8-27b"
PHOTOS_DIR = "/home/sid/BikeProject/photos"

PROMPT = (
    "You are inspecting a photo taken from a bicycle for a road safety report. "
    "Only flag a problem if it is serious enough to be a real hazard to a cyclist "
    "or to meaningfully disrupt the ride, for example: a pothole or crack deep or "
    "wide enough to cause a crash or damage a wheel, a missing or broken drain "
    "cover, a large patch of broken or crumbling asphalt, loose gravel or debris "
    "blocking the path, a fallen sign or one that is missing where it is clearly "
    "needed, or road markings so worn that the lane or crossing is unclear. "
    "Do NOT flag minor wear: hairline cracks, small patches, faded paint that is "
    "still readable, dirt, leaves, shadows, wet road surfaces, normal bumps, "
    "or anything that would not slow down or endanger a cyclist. "
    "If you are unsure, say 'Clear'. "
    "If there is a real hazard, reply in this exact format and nothing else: "
    "'HAZARD (High/Medium): <what it is and where in the frame>'. "
    "If there is none, reply with exactly: 'Clear'."
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = Groq(api_key=GROQ_API_KEY, timeout=30)
os.makedirs(PHOTOS_DIR, exist_ok=True)

gps_serial = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)
photo_queue = queue.Queue()
stop_event = threading.Event()


def photo_path(ts):
    return f"{PHOTOS_DIR}/{ts}.jpg"


def meta_path(ts):
    return f"{PHOTOS_DIR}/{ts}.json"


def save_meta(ts, meta):
    tmp = meta_path(ts) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(meta, f)
    os.replace(tmp, meta_path(ts))


def load_meta(ts):
    with open(meta_path(ts)) as f:
        return json.load(f)


def with_retries(fn, label, tries=3):
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            print(f"{label} failed (attempt {attempt + 1}/{tries}): {e}", flush=True)
            bad_key = "403" in str(e) or "401" in str(e)
            last = attempt == tries - 1
            if bad_key or last or stop_event.is_set():
                raise
            stop_event.wait(2 ** attempt)


def get_gps():
    gps_serial.reset_input_buffer()
    for _ in range(50):
        try:
            line = gps_serial.readline().decode("ascii", errors="replace")
            if line.startswith(("$GPRMC", "$GPGGA", "$GNRMC", "$GNGGA")):
                msg = pynmea2.parse(line)
                if hasattr(msg, "latitude") and msg.latitude != 0:
                    return msg.latitude, msg.longitude
        except Exception:
            pass
    return None, None


def process_photo(ts):
    meta = load_meta(ts)
    if meta.get("logged"):
        return

    with open(photo_path(ts), "rb") as f:
        image_bytes = f.read()

    if not meta.get("photo_url"):
        with_retries(
            lambda: supabase.storage.from_("photos").upload(
                f"{ts}.jpg", image_bytes,
                {"content-type": "image/jpeg", "upsert": "true"}),
            "upload",
        )
        meta["photo_url"] = supabase.storage.from_("photos").get_public_url(f"{ts}.jpg")
        save_meta(ts, meta)

    if not meta.get("description"):
        image_data = base64.b64encode(image_bytes).decode("utf-8")
        response = with_retries(
            lambda: client.chat.completions.create(
                model=MODEL,
                reasoning_effort="low",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    ],
                }],
            ),
            "describe",
        )
        meta["description"] = response.choices[0].message.content
        save_meta(ts, meta)

    with_retries(
        lambda: supabase.table("PiProject").insert({
            "timestamp": ts,
            "description": meta["description"],
            "image_url": meta["photo_url"],
            "latitude": meta.get("lat"),
            "longitude": meta.get("lon"),
        }).execute(),
        "insert",
    )
    meta["logged"] = True
    save_meta(ts, meta)
    print(f"logged {ts}", flush=True)


def capture_loop(cam):
    last_capture = 0
    while not stop_event.is_set():
        now = time.time()
        if now - last_capture >= 5:
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cam.capture_file(photo_path(ts), format="jpeg")
                lat, lon = get_gps()
                save_meta(ts, {"timestamp": ts, "lat": lat, "lon": lon})
                print(f"photo taken, GPS: {lat}, {lon}", flush=True)
                photo_queue.put(ts)
            except Exception as e:
                print(f"Capture error: {e}", flush=True)
            last_capture = now
        time.sleep(0.1)


def process_loop():
    while True:
        ts = photo_queue.get()
        try:
            process_photo(ts)
        except Exception as e:
            print(f"Skipping {ts}, will retry next startup: {e}", flush=True)
        finally:
            photo_queue.task_done()


def handle_stop(signum, frame):
    if stop_event.is_set():
        print("Force quitting.", flush=True)
        os._exit(1)
    stop_event.set()
    print("Stopping... press Ctrl+C again to force quit.", flush=True)


signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)

# retry anything from earlier runs that never made it to Supabase
for path in sorted(glob.glob(f"{PHOTOS_DIR}/*.json")):
    ts = os.path.basename(path)[:-5]
    try:
        if os.path.exists(photo_path(ts)) and not load_meta(ts).get("logged"):
            photo_queue.put(ts)
    except Exception:
        pass
print(f"{photo_queue.qsize()} old photo(s) queued for retry", flush=True)

cam = Picamera2()
cam_config = cam.create_still_configuration(
    main={"size": (2304, 1296)},
    transform=Transform(hflip=True, vflip=True),
)
cam.configure(cam_config)
cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
cam.start()
time.sleep(2)

capture_thread = threading.Thread(target=capture_loop, args=(cam,), daemon=True)
process_thread = threading.Thread(target=process_loop, daemon=True)
capture_thread.start()
process_thread.start()

try:
    while not stop_event.is_set():
        time.sleep(0.5)
finally:
    capture_thread.join(timeout=5)
    print("Finishing uploads (up to 15 seconds)...", flush=True)
    deadline = time.time() + 15
    while photo_queue.unfinished_tasks and time.time() < deadline:
        time.sleep(0.5)
    cam.stop()
    gps_serial.close()
    print("Done.", flush=True)
    os._exit(0)