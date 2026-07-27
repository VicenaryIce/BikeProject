from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import time
global cam 
import requests
import base64

cam = Picamera2()

cam.start()
time.sleep(2)



input("Press enter to take a photo")
cam.capture_file("/home/sid/Desktop/BikeProject/ringo.jpg", format = "jpeg")
print("done")

with open("/home/sid/Desktop/BikeProject/ringo.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

response = requests.post("http://localhost:11434/api/generate",json={
    "model": "moondream",
    "prompt": "Describe what you see in this image.",
    "images": [image_data],
    "stream": False
}
)

print(response.json()["response"])



