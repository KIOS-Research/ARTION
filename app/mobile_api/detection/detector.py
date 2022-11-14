import os
from pathlib import Path

import numpy as np
import cv2


# function that takes as input an image path and
# creates the detection image in the same path
def detect(path):

    # initialize the detector
    detector = Detector()
    # read the image
    image = cv2.imread(path)
    # detect the image
    img_det = detector.detect(image)
    # create the path of the new image
    path_det = path.split('.')[-2] + '_det.png'
    # write the image
    cv2.imwrite(path_det, img_det)
    return Path(path_det).name


class Detector():
    def __init__(self, weights="yolov4-tiny.weights", config_file="tiny-yolov4.cfg",
                 classes_file="coco.names", conf_thresh=0.25, nms_thresh=0.4,
                 netsize=[416, 416]):

        """ Detector class that implements yolo detector
              Parameters
              ----------
              weights : string
                  path to the weights file, eg. yolov4-tiny.weights
              config_file : string
                  path to the configs file, eg. tiny-yolov4.cfg
              classes_file : string
                  path to the classes file, eg. coco.names
              conf_thresh : float
                  confidence threshold for the detection
              nms_thresh : float
                  non maxima supression threshold for the detections
              netsize : tuple
                  netwrork's config size eg. [416,416]
              """
        cwd = os.path.abspath(os.getcwd())
        self.weights = os.path.join(cwd, 'mobile_api', 'detection', weights)
        self.config = os.path.join(cwd, 'mobile_api', 'detection', config_file)
        self.classes_file = os.path.join(cwd, 'mobile_api', 'detection', classes_file)
        # initialize the network
        self.net = cv2.dnn.readNet(self.weights, self.config)
        # self.net  = cv2.dnn.readNetFromDarknet(self.config, self.weights)
        # set the backend
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL_FP16)

        ln = self.net.getLayerNames()
        self.layers = [ln[i - 1] for i in self.net.getUnconnectedOutLayers()]
        self.netsize = netsize
        self.conf_thresh = conf_thresh
        self.nms_thresh = nms_thresh
        classes = []
        with open(self.classes_file, 'r') as f:
            classes = [line.strip() for line in f.readlines()]
        self.labels = np.array(classes, dtype=str)
        self.model = cv2.dnn_DetectionModel(self.net)
        self.model.setInputParams(size=(self.netsize[0], self.netsize[1]), scale=1 / 256)
        self.COLORS = np.random.randint(0, 255, size=(len(self.labels), 3), dtype="uint8")

    def detect(self, img_or):
        detections = []

        # copy the original image
        img = img_or.copy()
        # do some pre-processing (eg. resizing)
        image = self._preprocess(img)
        try:
            # detect the image
            classes, scores, boxes = self.model.detect(image, self.conf_thresh,
                                                       self.nms_thresh)
        except Exception as e:
            print(e)
        if len(boxes)==0:
           return img

        # de-normalize the results
        fixboxes = self.de_normalize(boxes,self.netsize, self.imgsize)
        boxes = np.array(fixboxes,dtype=np.int32)
        # draw the detections on the image
        image_det = self.postprocess( classes, scores, boxes, img)

        return image_det

    def _preprocess(self, frame):
        self.imgsize = [frame.shape[1], frame.shape[0]]
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return cv2.resize(img, (self.netsize[0], self.netsize[1]), interpolation=cv2.INTER_LINEAR)

    def de_normalize(self, boxes,netsize,imgsize):
        finBoxes = []
        for i in range(len(boxes)):
            box = boxes[i]
            x,y,w,h= int((box[0] / netsize[0]) * imgsize[0]),int((box[1] / netsize[1]) * imgsize[1]),\
                     int((box[2] / netsize[0]) * imgsize[0]), int((box[3] / netsize[1]) * imgsize[1])
            finBoxes.append((x,y,w,h))
        return finBoxes

    def postprocess(self, classes, scores, boxes, img):
        for i in range(len(boxes)):
            box = boxes[i]
            if scores[i] > self.conf_thresh:
                x,y,w,h = box
                color = [int(c) for c in self.COLORS[classes[i]]]
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                text = "{}: {:.4f}".format(self.labels[classes[i]], scores[i])
                cv2.putText(img, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, color, 2)
        return img
