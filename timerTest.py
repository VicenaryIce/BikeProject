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
client = Groq(api_key="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")

time.sleep(2)
start_time = time.time()




while True:
    elapsed_time = time.time()-start_time
    if elapsed_time >=5:
        cam.capture_file("/home/sid/Desktop/BikeProject/ringo.jpg", format = "jpeg")
        print("photo taken")

       
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
        responseReady = True
        if responseReady ==True:


            print(response.choices[0].message.content)
            responseReady = False
        start_time = time.time()
        time.sleep(0.1)
