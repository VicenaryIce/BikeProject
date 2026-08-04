from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import time
global cam 
import requests
import base64
from groq import Groq
cam = Picamera2()

cam.start()
time.sleep(2)



input("Press enter to take a photo")
cam.capture_file("/home/sid/Desktop/BikeProject/ringo.jpg", format = "jpeg")
print("done")






client = Groq(api_key="YOUR_GROQ_API_KEY")
with open("/home/sid/Desktop/BikeProject/ringo.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="qwen/qwen3.6-27b",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe what you see in this image. Descrive the image as a whole, not each panel individually. be concise an use bullet points"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]
    }]
)

print(response.choices[0].message.content)