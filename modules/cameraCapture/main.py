# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import time
import sys
import os
import requests
import json
import cv2
from azure.iot.device import IoTHubModuleClient, Message
from flask import Flask, render_template, Response

app = Flask(__name__)

# global counters
SENT_IMAGES = 0

# global client
CLIENT = None

# Send a message to IoT Hub
# Route output1 to $upstream in deployment.template.json
def send_to_hub(strMessage):
    message = Message(bytearray(strMessage, 'utf8'))
    CLIENT.send_message_to_output(message, "output1")
    global SENT_IMAGES
    SENT_IMAGES += 1
    print( "Total images sent: {}".format(SENT_IMAGES) )

# Send an image to the image classifying server
# Return the JSON response from the server with the prediction result
def sendFrameForProcessing(imagePath, imageProcessingEndpoint):
    headers = {'Content-Type': 'application/octet-stream'}

    #with open(imagePath, mode="rb") as test_image:

    #test_image = imagePath
    
    try:
        response = requests.post(imageProcessingEndpoint, headers = headers, data = imagePath)
        print("Response from classification service: (" + str(response.status_code) + ") " + json.dumps(response.json()) + "\n")
    except Exception as e:
        print(e)
        print("No response from classification service")
        return None

    return json.dumps(response.json())


def main(imagePath, imageProcessingEndpoint):
    try:
        print ( "Simulated camera module for Azure IoT Edge. Press Ctrl-C to exit." )

        try:
            global CLIENT
            CLIENT = IoTHubModuleClient.create_from_edge_environment()
        except Exception as iothub_error:
            print ( "Unexpected error {} from IoTHub".format(iothub_error) )
            return

        print ( "The sample is now sending images for processing and will indefinitely.")

        cap = cv2.VideoCapture(imagePath)

    
        while(cap.isOpened()):
        #while True:
            success, img = cap.read()
            if not success:
                print('No Video')
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                ret,buffer = cv2.imencode('.jpg', img)  
                img=buffer.tobytes()
                #ewImg= cv2.imencode('.jpg', img)[1].tobytes()
                # concat frame one by one and show result
                classification = sendFrameForProcessing(img, imageProcessingEndpoint)
                if classification:
                    send_to_hub(classification)
                time.sleep(3)
    
                

    except KeyboardInterrupt:
        print ( "IoT Edge module sample stopped" )


def gen_frames():  
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    try:
        # Retrieve the image location and image classifying server endpoint from container environment
        IMAGE_PATH = os.getenv('IMAGE_PATH', "")
        IMAGE_PROCESSING_ENDPOINT = os.getenv('IMAGE_PROCESSING_ENDPOINT', "")
    except ValueError as error:
        print ( error )
        sys.exit(1)

    if ((IMAGE_PATH and IMAGE_PROCESSING_ENDPOINT) != ""):
        app.run(debug=True, port=8080, host='0.0.0.0')
        main(IMAGE_PATH, IMAGE_PROCESSING_ENDPOINT)
    else: 
        print ( "Error: Image path or image-processing endpoint missing" )
