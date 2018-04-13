import imutils
from imutils import contours
from skimage import measure
import cv2
import numpy as np
import os
import os.path
import time
import argparse
import yaml
import logging as flog
from subprocess import call
import requests
import hashlib
from threading import Thread

drawing = False # true if mouse is pressed
dragging = False # true if mouse is moving (DOWN > MOVE > UP)

ix,iy = -1,-1
fx,fy = -1,-1

ls_areas = []
total_slots = 0
occupied_slots = 0
display_window = False
image_upload_interval = 3

reporting_interval = 2
lastReportTime = 0

background_model_frams = 10
frame_counter = 0
device_id = 'rpi_1'

# mouse callback function
def draw_box(event,x,y,flags,param):
    global ix,iy,drawing,mode,img,fx,fy,dragging

    if event == cv2.EVENT_LBUTTONDOWN:
        print 'MOUSE DOWN'
        drawing = True
        ix,iy = x,y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            dragging = True
#            print 'MOUSE MOVE'
            fx,fy = x,y

    elif event == cv2.EVENT_LBUTTONUP:
        print 'MOUSE UP'
        drawing = False
        dragging = False
        fx,fy = x,y
        if x != ix and y != iy and x>ix+10 and y>iy+10:
            ls_rect = [ix, iy, x, y, 0, 255, 0, 0, 0]
            ls_areas.append(ls_rect)
            append_line_in_file(ls_rect)
        else:
            print 'Invalid Bounding Box, please try again.'

# Add bounding box
def append_line_in_file(rt):
    f= open(bounding_box_file,'a+')
    line = `rt[0]` + " " + `rt[1]` + " " + `rt[2]` + " " + `rt[3]` + " " + `rt[4]` + " " + `rt[5]` + " " + `rt[6]` + " " + `rt[7]`+  " " + `rt[8]`+ "\n"
    f.write(str(line))
    f.close()

# Delete recently added bounding box
def delete_last_line_in_file():
    f= open(bounding_box_file,'r')
    lines = f.readlines()
    f.close()

    f= open(bounding_box_file,'w')
    del lines[-1]
    f.write(str(lines))
    f.close()

# Read bounding box file
def read_file():
    global ls_areas

    if os.path.isfile(bounding_box_file):
        flog.debug(str('file exists\n'))
        f=open(bounding_box_file, "r")
        if f.mode == 'r':
            f1 = f.readlines()
            for ln in f1:
#                print ln
                split_list = ln.split(" ")
                ls_rect = [int(split_list[0]), int(split_list[1]), int(split_list[2]), int(split_list[3]), int(split_list[4]), int(split_list[5]), int(split_list[6]), int(split_list[7]), int(split_list[8])]
                ls_areas.append(ls_rect)
        f.close()
        flog.debug(str('file closed\n'))

# Read config file
def read_file_config():
    global occupancy_threshold, time_threshold

    if os.path.isfile(config_file):
        flog.debug(str('file exists\n'))
        f=open(config_file, "r")
        if f.mode == 'r':
            f1 = f.readlines()
            for ln in f1:
#                print ln
                split_list = ln.split(" ")
                ot = int(split_list[0])
                if ot:
                    occupancy_threshold = ot
                tt = int(split_list[1])
                if tt:
                    time_threshold = tt
        f.close()
        flog.debug(str('file exists\n'))

# write bounding box file
def write_file():
    global ls_areas
    f= open(bounding_box_file,'w+')
    for ls in ls_areas:
        rt = ls
        line = `rt[0]` + " " + `rt[1]` + " " + `rt[2]` + " " + `rt[3]` + " " + `rt[4]` + " " + `rt[5]` + " " + `rt[6]` + " " + "0" + " " + "0" + "\n"
        f.write(str(line))
    f.close()

# write config file
def write_file_config(ov, tv):
    global occupancy_threshold, time_threshold
    delete_file_config()
    f= open(config_file,'w+')
    line = `ov` + " " + `tv`
    f.write(str(line))    
    f.close()
    if display_window:
        print 'Config file updated'

# undo (Remove last) bounding box
def undo():
    #undo bounding box
    print 'undo'
    # delete from list
    ls_areas.pop()
    #delete from file
    #delete_last_line_in_file()
    write_file()

# Delete bounding box file
def delete_file():
    global ls_areas
    if os.path.isfile(bounding_box_file):
        os.remove(bounding_box_file)
        ls_areas[:] = []
    if display_window:
        print "File Deleted !"

# Delete config file
def delete_file_config():
    global occupancy_threshold, time_threshold
    if os.path.isfile(config_file):
        os.remove(config_file)
        occupancy_threshold = 60
        time_threshold = 4
    if display_window:
        print "Config File Deleted !"

# Display plarking slot status
def show_status():
    print '============================'
    print 'total slots: %d' % total_slots
    print 'occupied_slots: %d' % occupied_slots
    empty = total_slots - occupied_slots
    print 'empty slots: %d' % empty

def show_output():
    if display_window:
        print '----------------------------'
        print 'output'
    out_string = ''
    for ls in ls_areas:
        out_string += `ls[8]`
        #print '%d' % ls[8]
    if display_window:
        print out_string
    flog.debug(str('output ' + out_string + '\n'))
    write_output_fifo(out_string)

# write optput to fifo file
def write_output_fifo(output):
    
    f= open(output_file,'w+')
    f.write(str(output))    
    f.close()
    if display_window:
        print 'Output file updated'
        
# Read inputs from treminal 
def read_input():
    global occupancy_threshold, time_threshold
    ov = occupancy_threshold
    tv = time_threshold
    print 'read_input call'
    try:
        input_var = raw_input('Enter Occupancy Threshold : [current value - %d percent]\n' % occupancy_threshold)
        print 'Entered: ' + input_var
        val = int (input_var)
        if val>0 and val<100:
            ov = val
            print 'Threshold set to ' + `ov`
        else:
            print 'Invalid Input !'

        input_var = raw_input('Enter Time Threshold : [current value - %d second]\n' % time_threshold)
        print 'Entered: ' + input_var
        val = int (input_var)
        if val>0 and val<100:
            tv = val
            print 'Threshold set to ' + `tv`
        else:
            print 'Invalid Input !'

        write_file_config(ov, tv)
        read_file_config()
        view_threshold_params()
    except ValueError:
        print 'Invalid input argument! Integer value is required.'

# Display threshold values
def view_threshold_params():
    print '\nConfiguration Parameters:'
    print 'occupancy threshold: ' + `occupancy_threshold`
    print 'time threshold: ' + `time_threshold`

# Send image to DDI platform
def send_image():
    flog.debug(str('uploading image\n'))
    if display_window:
        print 'uploading image'
    thread1 = Thread(target = upload_image)
    thread1.start()

# Get MD5 of image file
def get_image_md5(full_path):
    #return hashlib.md5(open(full_path, 'rb').read()).hexdigest();
    hash_md5 = hashlib.md5()
    with open(full_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_image():
    url = "http://13.90.101.85:8888/api/Upload/"
    filelist = [ f for f in os.listdir(image_file_path) if f.endswith(".jpg") ]
    for f in filelist:
        #files = {'file': (image_file_path + f, open(image_file_path + f, 'rb'))}
        files = {'file': (image_file_path + f, open(image_file_path + f, 'rb'), 'image/jpg')}

        r = requests.post(url, files=files)
        flog.debug(str(r.text))
        if display_window:
            print r.text
        break

# Delete old image from Images directory
def empty_images_dir():
    filelist = [ f for f in os.listdir(image_file_path) if f.endswith(".jpg") ]
    for f in filelist:
        os.remove(image_file_path + f)

# Get Device Id
def get_device_id():
    global device_id
    with open(id_config_file, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    device_id = cfg['deviceID']
    if display_window:
        print(device_id)

# ------- algo start -------

video_source_file_name = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/parking_video.mp4'
bounding_box_file = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/parking_bounding_boxes.txt'
config_file = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/parking_config.txt'
id_config_file = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/config.yaml'
output_file = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/output'
log_file = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/parking_bsm.log'
image_file_path = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/image_uploading/Images/'
support_image_file_path = '/home/pi/mobiliya/platform-rpi/background_subtraction_model/image_uploading/SupportImages/'

#flog = open(log_file, 'w+')
#flog.basicConfig(filename=log_file,level=flog.DEBUG)
flog.basicConfig(filename=log_file,level=flog.DEBUG,format='%(asctime)s %(message)s')
flog.debug(str('script begin\n'))

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--occupancythreshold", required=False,
        default="40",
        help="Threshold (%) for occupancy to consider an update")
ap.add_argument("-t", "--timethreshold", required=False,
        default="4",
        help="Threshold for time to consider an update")
ap.add_argument("-b", "--backgroundvideofile", required=True,
        default="/home/pi/mobiliya/platform-rpi/background_subtraction_model/pune_parking_bsm_night.mp4",
        help="Background resource video file path")
ap.add_argument("-i", "--inputsource", required=False,
        default="0",
    help="0: usb camera, 1: pi camera, 2: video file")
ap.add_argument("-w", "--displaywindow", required=False,
        default="1",
    help="1: Show display window, 0: Hide display window")
args = vars(ap.parse_args())

occupancy_threshold = int(args["occupancythreshold"])
time_threshold = int(args["timethreshold"])
input_source = int(args["inputsource"])
display_window = int(args["displaywindow"])
background_video_file = args["backgroundvideofile"]

video_bg_file_name = background_video_file

# input from camera, 0 - USB Camera, 1 - PI Camera
cap = None

# set video source for input
if input_source == 0:
    cap = cv2.VideoCapture(0)
elif input_source == 1:
    cap = cv2.VideoCapture(1)
else:
    cap = cv2.VideoCapture(video_source_file_name)

flog.debug(str('cv2.VideoCapture initialized\n'))

# initiate background subtractor
capbg = cv2.VideoCapture(video_bg_file_name)

# allow the camera to warmup
time.sleep(0.5)

# set width and height
cap.set(3,320)
cap.set(4,240)
capbg.set(3,320)
capbg.set(4,240)
ret, img = capbg.read()

flog.debug(str('first frame read\n'))

fgbg = cv2.BackgroundSubtractorMOG()
flog.debug(str('background subtractor initialized\n'))

if display_window:
    cv2.namedWindow('image')
    cv2.setMouseCallback('image',draw_box)

# initiate bounding boxes and configuration parameters
flog.debug(str('going to read bounding box file\n'))
read_file()
flog.debug(str('going to read bounding config file\n'))
read_file_config()
get_device_id()

# Display instructions
if display_window:
    print 'file_format: x1, x2, y1, y2, r, g, b, timestamp'
    print '\nBounding Boxes Options:'
    print 'u [Key Event]  - undo bounding box'
    print 's [Key Event]  - save file'
    print 'd [Key Event]  - delete bounding box file'
    
    print '\nThreshold Configuration:'
    print '-o [Input Parameter] - Threshold (%) for occupancy to consider an update'
    print '-t [Input Parameter] - Threshold for time to consider an update'
    print 'v [Key Event]        - View Threshold Parameters'
    print 'c [Key Event]        - Change threshold values'
    print 'r [Key Event]        - Reset threshold values'
    
    print '-w [Input Parameter] - 1: to display output window, else 0'
    
    print '\noccupancy threshold: ' + `occupancy_threshold`
    print 'time threshold: ' + `time_threshold`
    
    print '\nEsc, q - quit\n'

flog.debug(str('going in loop\n'))

last_frame_timestamp = time.time()

while(1):

    frame_counter += 1

    if frame_counter < background_model_frams:
#        frame_counter += 1
        ret, img = capbg.read()
        if display_window:
            print 'Preparing background_model'
        time.sleep(0.2)
    else:
        ret, img = cap.read()
#        print 'foreground_mask'

    if frame_counter == background_model_frams:
        capbg.release()

    fgmask = fgbg.apply(img)

    time_delta = time.time() - last_frame_timestamp
    if time_delta > image_upload_interval:
        empty_images_dir()
        #cv2.imwrite(image_file_path + device_id + `int(time.time())` + '.jpg', img)
        cv2.imwrite(image_file_path + device_id + '.jpg', img)
        md5_name = get_image_md5(image_file_path + device_id + '.jpg')
        os.rename(image_file_path + device_id + '.jpg', image_file_path + device_id + '_' + md5_name + '.jpg')
        send_image()
        last_frame_timestamp = time.time()
        if not display_window:
            #save ref image of background model
            cv2.imwrite(support_image_file_path + 'mask.jpg', fgmask)

    if display_window:
        cv2.imshow('mask', fgmask)

    total_slots = len(ls_areas)
    count_occupied = 0

#    time.sleep(1)

    for ls in ls_areas:
        rt = ls

        crop_img = fgmask[rt[1]:rt[3], rt[0]:rt[2]]
        white_pixels = cv2.countNonZero(crop_img)

        total_pixels = crop_img.size
        percentage_occupied = white_pixels * 100 / total_pixels

        ts = time.time()
        tdiff = ts - rt[7] # time-difference in seconds
          
        if rt[7] == 0:
            rt[7] = ts
        elif tdiff>time_threshold:

            if percentage_occupied>occupancy_threshold:
        
                rt[4]=255
                rt[5]=0
                rt[6]=0
                count_occupied += 1
                rt[8]=1
            else:
                rt[4]=0
                rt[5]=255
                rt[6]=0
                rt[7]=0
                rt[8]=0
#        else: 
#            print 'threshold not reached : ts - rt[7] = %d' % tdiff

        cv2.rectangle(img, (rt[0],rt[1]), (rt[2], rt[3]), (rt[6],rt[5],rt[4]), 2)

    if dragging == True:
        cv2.rectangle(img, (ix,iy), (fx,fy), (0,255,255), 2)
        

    if occupied_slots != count_occupied:
        flog.debug(str('change detexted\n'))
        occupied_slots = count_occupied
        if display_window:
            show_status()

    tsReport = time.time()
    if lastReportTime == 0:
        lastReportTime = tsReport
    else:
        tsCurrent = time.time()
        tsReportDiff = tsCurrent - lastReportTime # time-difference in seconds

        if tsReportDiff>reporting_interval:
            lastReportTime = tsCurrent
            show_output()

    # show the frame
    if display_window:
        cv2.imshow('image',img)

        k = cv2.waitKey(1) & 0xFF
        key = cv2.waitKey(1) & 0xFF

        if k == ord('s'):
             print 'Autosave is enabled, no need to save file.'
#             write_file()
        elif k == ord('u'):
            undo()
        elif k == ord('d'):
            delete_file()
        elif k == ord('r'):
            delete_file_config()
        elif k == ord('c'):
            read_input()
        elif k == ord('v'):
            view_threshold_params()
        elif k == 27:
            break

        if key == ord('q'):
            break
    else:
        if time_delta > image_upload_interval:
            #save ref inage of detected model
            cv2.imwrite(support_image_file_path + 'detection.jpg', img)

cap.release()
cv2.destroyAllWindows()

