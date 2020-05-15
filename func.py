import cv2
import os
import numpy as np

front = cv2.CascadeClassifier("files/haarcascade_frontalface_alt.xml")
profile = cv2.CascadeClassifier("files/haarcascade_profileface.xml")
modelFile = "model/res10_300x300_ssd_iter_140000_fp16.caffemodel"
configFile = "model/deploy.prototxt"

def iou(x11,y11,x12,y12,x21,y21,x22,y22):
    xi1 = max(x11,x21)
    yi1 = max(y11,y21)
    xi2 = min(x12,x22)
    yi2 = min(y12,y22)
    l1 = max(xi2-xi1+1,0)
    l2 = max(yi2-yi1+1,0)
    s_i = l1*l2
    s_1 = (x12-x11+1)*(y12-y11+1)
    s_2 = (x22 - x21 + 1) * (y22 - y21 + 1)
    s_u = s_1 + s_2 - s_i
    s_iou = s_i/s_u
    return s_iou


def if_not_intersect(x11,y11,x12,y12,faces):
    for (x,y,w,h) in faces:
        if iou(x11,y11,x12,y12,x,y,x+w-1,y+h-1)>0.45:
            return False
    return True


def find_faces_dnn(img, param):
    (height, width) = img.shape[:2]
    new_h = max(300, int(round(param * height)))
    new_w = max(300, int(round(param * width)))
    blob = cv2.dnn.blobFromImage(img, 1.0, (new_h, new_w), (104.0, 177.0, 123.0))
    net = cv2.dnn.readNetFromCaffe(configFile, modelFile)
    net.setInput(blob)
    detections = net.forward()
    square = []
    faces = []
    current_number = 0
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            current_number += 1
            box = detections[0, 0, i, 3:7] * np.array([width, height, width, height])
            (x_1, y_1, x_2, y_2) = box.astype("int")
            faces.append((x_1, y_1, x_2-x_1+1, y_2-y_1+1))
            square.append((x_2-x_1+1) * (y_2-y_1+1) / (height * width))
    if len(faces) == 0:
        return current_number, 0, faces
    max_square = max(square)
    return current_number, max_square, faces

def find_faces_viola(img, param):
    g_pic = img.copy()
    g_pic = cv2.cvtColor(g_pic, cv2.COLOR_BGR2GRAY)
    faces = profile.detectMultiScale(g_pic, param)
    faces1 = front.detectMultiScale(g_pic, param)
    faces_final = []
    square = []

    for (x, y, w, h) in faces1:
        faces_final.append((x, y, w, h))
        square.append(w * h/(img.shape[0]*img.shape[1]))

    current_number = len(faces1)

    for (x, y, w, h) in faces:
        if if_not_intersect(x, y, x + w-1, y + h-1, faces1):
            current_number += 1
            faces_final.append((x, y, w, h))
            square.append(w * h/(img.shape[0]*img.shape[1]))
    if len(faces_final) == 0:
        return current_number, 0, faces_final
    max_square = max(square)
    return current_number, max_square, faces_final

def image_processing(name):
    parameter_viola = {'small': 1.035, 'medium': 1.105, 'large': 1.175}
    parameter_dnn = {'small': 1, 'medium': 0.9, 'large': 0.4}
    image_path = os.getcwd() + '/static/'
    image_full_path = image_path+name
    image = cv2.imread(image_full_path)
    res = find_faces_dnn(image, parameter_dnn['large'])
    flag = 0
    if res[1] < 0.006 and res[1] >= 0.002:
        flag = 1
        new_res = find_faces_viola(image, parameter_viola['medium'])
    if res[1] < 0.002:
        flag = 1
        new_res = find_faces_viola(image, parameter_viola['small'])
    if flag:
        current_number = new_res[0]
        for (x, y, w, h) in new_res[2]:
            cv2.rectangle(image, (x, y), (x + w - 1, y + h - 1), (0, 255, 255), 2)
    else:
        current_number = res[0]
        for (x, y, w, h) in res[2]:
            cv2.rectangle(image, (x, y), (x + w-1, y + h-1), (0, 255, 255), 2)

    new_name = 'new_'+name
    new_image_path = image_path + new_name
    cv2.imwrite(new_image_path, image)
    return current_number

