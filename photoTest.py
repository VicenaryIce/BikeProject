import time
from libcamera import controls, Transform
from picamera2 import Picamera2


cam = Picamera2()
config = cam.create_still_configuration(
    main={"size": (2304, 1296)},
    transform=Transform(hflip=True, vflip=True)
)
cam.configure(config)
cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
cam.start()
time.sleep(2)
cam.capture_file("/home/sid/Desktop/BikeProject/picture.jpg", format = "jpeg")
print("done")