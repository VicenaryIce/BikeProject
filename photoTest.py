from picamera2 import Picamera2
import time

cam = Picamera2()
cam.start()
time.sleep(2)

cam.capture_file("/home/sid/Desktop/BikeProject/picture.jpg", format = "jpeg")
print("done")