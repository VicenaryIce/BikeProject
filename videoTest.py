from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import time
global cam 
cam = Picamera2()


recording_count = 0

while True:

    media_choice = input("click y for photo, n for video")
    if media_choice.lower() == "y":
        config = cam.create_still_configuration()
        cam.configure(config)
        cam.start()
        input("press smth to take a photo")
        cam.capture_file("/home/sid/Desktop/BikeProject/picture.jpg", format="jpeg") 
        print("bogos saved")
        again = input("wanna take more?(y/n)")
        if again.lower() != "y":
            break
        cam.stop
        
    elif media_choice.lower() == "n":
        config = cam.create_video_configuration(main={"size": (1280, 720)})
        cam.configure(config)
        cam.start()
        input("Press smth start a video")
        recording_count +=1
        name = f"video_{recording_count}.mp4"
        encoder = H264Encoder()
        output = FfmpegOutput(name)
        cam.start_recording(encoder, output)



        input("want to stop the video????")
        cam.stop_recording()
        cam.stop()

        again = input("record another video?(y/n)")
        if again.lower() != "y":
            break





    


