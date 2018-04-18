import cv2
import requests
import base64

def getRawImage() :

    #print ("Into get raw Image fnction")
    cam = cv2.VideoCapture(1)
    ret_val, img = cam.read()
    retval, buffer = cv2.imencode('.jpg', img)
    jpg_as_text = base64.b64encode(buffer)
    print(jpg_as_text)
    cv2.imshow('my webcam', img)
    #cv2.waitKey(0) 
    #url = 'http://10.9.44.39/api/Upload'
    #files = {'media': open('test.jpg', 'rb')}
    #files = {'media': img}
    #requests.post(url, files=files)
#        break  # esc to quit
        
        
#print "Into Python"
getRawImage()

