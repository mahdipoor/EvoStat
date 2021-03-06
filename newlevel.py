#!/usr/bin/python -u
from __future__ import print_function
import sys, os, time, socket, subprocess, re, traceback
import datetime
from os  import popen
import glob
import base64, urllib2
from suppress_stdout_stderr import suppress_stdout_stderr
import numpy as np
import cv2
import cv2.cv as cv
import evocv2
from util import *   # settings, 

( blue, green, red, maxIntensity ) = ( 0, 1, 2, 255.0 )
color = green
kernal = np.ones((2,2),np.uint8)

def erodeDilate(img,iter=1,erode=1,dilate=1) :
    for i in range(iter):
        img = cv2.erode(img,kernal,iterations=erode)
        img = cv2.dilate(img,kernal,iterations=dilate)
    return img

params = settings()
cam = cv2.VideoCapture(params['camera'])
for i in range(30) : # Break in the camera by throwing away
    cam.read()       # split frames, letting exposure settle

def lagoon_level_bbox_xy(lnum) :
    global params
    (y1,x1,y2,x2) = params['lagoonRegion']
    quarterWidth = int((x2-x1)/4)
    eighthWidth = int((x2-x1)/8)
    sixteenthWidth = int(eighthWidth/2)
    left = x1 + sixteenthWidth + 8
    right = x1 + sixteenthWidth + eighthWidth - 8
    return ((left+(lnum*quarterWidth), y1+8),(right+(lnum*quarterWidth),y2-8))

def showUser(img, label=(".",0,0),multiplier=1) :
    if (params['debugpause'] > 10) :
        (text, y, x) = label
        cv2.putText(img,text, (y,x),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,0,255),1)
        cv2.imshow("camera", img)
        if cv.WaitKey(multiplier*params['debugpause']) == 27:
            exit(0)

def exportImage(image) :
    global params
    if (image != None ) :
        (y1,x1,y2,x2) = params['lagoonRegion']
        cv2.rectangle(image,(x1,y1),(x2,y2),(250,250,0),2)
        for i in range(4):
            ((lx1,ly1),(lx2,ly2)) = lagoon_level_bbox_xy(i)
            cv2.rectangle(image,(lx1,ly1),(lx2,ly2),(100,255-i*60,i*60),2)
        (cy1,cx1,cy2,cx2) = params['cellstatRegion']
        cv2.rectangle(image,(cx1,cy1),(cx2,cy2),(0,200,200),2)
        filename = "./web/phagestat.jpg"
        cv2.imwrite(filename,cv2.resize(image,params['imageSize']))
                    
def contrast(image, iter=1, scale=2.0, offset=-80) :
    if (image == None) :
        plog("contrast called with null Image")
    for i in range(iter) :
        plog("Try contrast "+str((iter,scale,offset)))
        if (image == None) :
            plog("contrast loop: Image is None")
        else :
            showUser(image)
        image = cv2.add(cv2.multiply(image,scale),offset)
        if (image == None) :
            plog( "image(None) after add/mulitply in contrast!")
        image = erodeDilate(image, 1, 1, 1)
    showUser(image,label= ("cdone",image.shape[0]/2,image.shape[1]/2) )
    (ret,img) = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
    if (ret == False) :
        plog( "Thresholding failed?")
        return None
    if (img == None) :
        plog( "img is None after binary threshold in contrast")
    showUser(img)
    return img
    
def emphasis(img, color=1, scale=2, fraction=0.5) :
    """Return monochrome image with selected color scaled
    minus sum of the fractions of the other colors.
    Where color is Blue (0), default Green (1), or Red (2)"""
    plog("Color="+str(color))
    return cv2.subtract(cv2.multiply(img[:,:,color],scale),
                        cv2.multiply(cv2.add( img[:,:,(color+1)%3],
                                                  img[:,:,(color+2)%3]),fraction))
    
def release() :
    global cam
    if (cam != None) :
        cam.release()
    cv2.destroyAllWindows()

def incrColor(color,plus) :
    (b,g,r) = color
    if (b>plus):
        nb = b-plus
    else :
        nb = b
    if (g>plus):
        ng = g-plus
    else :
        ng = g
    if (r>plus):
        nr = r-plus
    else :
        nr = r
    return (nb,ng,nr)

def showBox(img, bb, colorin, size) :
    (x1,y1,x2,y2) = bb
    color = incrColor(colorin,-90)
    showCoord(img, (x1,y1), color, size)
    showCoord(img, (x2,y2), color, size)
    cv2.line(img,(x1,y2),(x2,y2),color,size)
    cv2.line(img,(x1,y1),(x2,y1),incrColor(color,30),size)
    cv2.line(img,(x1,y1),(x1,y2),incrColor(color,60),size)
    cv2.line(img,(x2,y1),(x2,y2),incrColor(color,80),size)

def rotateImage(img, angle=90):
    """+-90 degree rotations are fast and do not crop"""
    plog("rotating by " + str(angle))
    if (angle == 90) :
        return(cv2.flip(cv2.transpose(img),flipCode=0))
    elif (angle == -90) :
        return(cv2.flip(cv2.transpose(img),flipCode=1))
    else :
        center = (img.shape[1]/2.0,img.shape[0]/2.0)
        rotate = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(img, rotate, (img.shape[1], img.shape[0]))

def showCoord(img,pt,color,size) :
    cv2.putText(img,str(pt), pt, cv2.FONT_HERSHEY_PLAIN,size,color,size)

def showLevel(img, bb, lvl, color) :  # Returns percentage level 
    height = bb[2]-bb[0]
    width = bb[3]-bb[1]
    (px,py) = ( bb[3]-width/2, bb[0]+lvl )
    pc = 100-100*lvl/height
    cv2.line(img,(px,py),(px+(width/2),py), color, 2)
    cv2.putText(img,"  "+str(pc)+"%",(px-10,py-8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, color,2)
    return(pc)

def croppedImage(brect):
    plog("Evocv cropping "+str(brect))
    (y1,x1,y2,x2) = brect
    image = grab()
    plog(str(image.shape))
    showUser(image)
    if (image == None) :
        plog("camera(fail).")
        exit(0)
    cimg = image[y1:y2,x1:x2,:]
    plog(str(cimg.shape))
    showUser(cimg)
    return cv2.copyMakeBorder(cimg, 2,2,2,2, cv2.BORDER_CONSTANT,(0,0,0))

def cropImage(image, brect):
    if (image is None) :
        plog("cropImage given None image")
        exit(0)
    plog("Evocv cropping "+str(brect))
    (y1,x1,y2,x2) = brect
    showUser(image)
    if (image == None) :
        plog("camera(fail).")
        exit(0)
    cimg = image[y1:y2,x1:x2,:]
    plog(str(cimg.shape))
    showUser(cimg)
    return cv2.copyMakeBorder(cimg, 2,2,2,2, cv2.BORDER_CONSTANT,(0,0,0))

def level(img) :
    """Return the uppermost horizontal line in the image (e.g. liquid level)
    Returns:   -1 when there is a problem with the data
    1000 when there is no line within proper range"""
    if (img == None) :
        plog("Level detector called with invalid image")
        return -1
    else :
        plog("inside level")
    (h,w) = img.shape
    if (h == 0 or w == 0) :
        plog( "Level called with degenerate image SHAPE" + str(img.shape))
        return -1
    img = contrast(img)
    if (img==None) :
        plog("Contrast returned None  (shape =" + str(img.shape))
        return -1
    edges = cv2.Canny(img, 90, 100)
    if (edges == None) :
        plog("Bad Canny output so not calling HoughLinesP in level()")
        return -1
    alllines = cv2.HoughLinesP(edges, 2, np.pi/2.0, 1, 8, 4)
    if (alllines == None) :
        plog("No horizontal lines found in image")
        return -1
    topline = 1000 + len(alllines)
    plog( "ALLINES " + str(alllines))
    for lines in alllines:
        plog( "LINES " + str(lines))
        for l in lines : # Find the highest (minY) line (not on the edge)
            plog( "LINE " + str(l))
            if (l[1] == l[3]) : # Horizontal?
                if ( l[1] < topline and l[1] > 5 and l[1] < h-5) :
                    plog( "\nHighest so far: " + str(l))
                    topline = l[1]
                else :
                    plog( " NOT RIGHT " + str(l) + " H = " + str(h))
    plog("level(): topline coordinate is: "+str(topline))
    return topline

# BB (bounding box) is (y1, x1, y2, x2)
# Color  is one of [0,1,2] [Blue, Green, Red]
# Contrast = (#Iterations, Multiply, Offset(usually negative)) try (3, 1.35, -70)

def getLevel(image, bb, color, con) :
    """Level value is a y position in the region"""
    plog("getLevel " + str(bb))
    frame = cropImage(image, bb)
    mono = frame[:,:,color]
    plog("before showUser(mono)")
    showUser(mono)
    plog("after showUser(mono)")
    plog("contrast tuple = " + str(con))
    (it, sc, off) = con
    mono = contrast(mono,it,sc,off)
    if (mono == None) :
        plog("Image is None after contrast in getLevel")
    showUser(mono)
    plog("calling level")
    lvl = level(mono)
    if (lvl == -1):
        return -1
    plog("getLevel() "+str(lvl))
    if (lvl == None or lvl > bb[2] ) :
        plog("getLevel failed")
    if (lvl > 0 and lvl < bb[2]) : # Level in range
        return lvl
    plog(str(lvl) + " out of range :" + str(bb))
    return 0

def addImages(img, num) :
    new = grab()
    new = cv2.add(new, img)
    for i in range(num-1):
        n2 = grab()
        new = cv2.add(new, n2)
    return new

def grab():
    global cam, params
    (rval,img) = cam.read()
    if (rval):
        plog(str(params['rotate']))
        showUser(img)
        if (params['rotate']) :
            return rotateImage(img, params['rotate'])
        else :
            return img
    return None

if __name__ == "__main__" :
    img = grab()
    with suppress_stdout_stderr() :
        cv2.namedWindow("camera", cv2.CV_WINDOW_AUTOSIZE)
        if cv2.__dict__['moveWindow'] != None :
            cv2.moveWindow("camera", 100, 0)
        else :
            plog("no moveWindow in cv2, update your OpenCV installation.")
    plog("openCV('" + str(cv2.__version__) + "').")
    if ('gen' in sys.argv) :   # Python .settings file updated
        exportImage(img)
        exit(0)
    img2 = img             #    img2 = addImages(img,4)
    plog("alllevels: " + str(img2.shape))
    brect = params['lagoonRegion']
    quarterWidth = (brect[3]-brect[1])/4
    eighthWidth = quarterWidth/2
    plog("QUARTER width " + str(quarterWidth))
    llist = []
    for i in range(params['numLagoons']) :
        x1 = brect[1] + i * eighthWidth
        x2 = brect[1] + int((i+1)*(1.2)*eighthWidth)
        lbb = (brect[0], x1, brect[2], x2)
        ( (lx1,ly1), (lx2,ly2) ) = lagoon_level_bbox_xy(i)
        lbb = (ly1,lx1,ly2,lx2)
        llev = getLevel( img2,
                         lbb,
                         green,
                         params['lagoonContrast'])
        plog("LBB " + str(lbb) + " level " + str(llev))
        llist.append(showLevel(img, lbb, llev, (128,128,255)))
    levelPhase = 1
    brect = params['cellstatRegion']
    num = 1
    lev = getLevel(img, brect, blue, params['cellstatContrast'])
    plog("CBB " + str(brect) + " level " + str(lev))
    (wi,he,de) = img.shape
    cv2.putText(img,time.asctime(time.localtime()),(wi/16,3*he/4),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255),2)
    llist.insert(0, showLevel(img, brect, lev, (255,255,0)))
    exportImage(img)
    print(termIntList('levels',llist))
    release()

