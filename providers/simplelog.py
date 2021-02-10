#!/usr/bin/python3

########################################################################
# Copyright (c) 2018-2019 Robert Bosch GmbH
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0
########################################################################

# This provider gets data from a simple log file which contains lines
# formatted 
# lat,lon
# All other values will be reported as 0


import csv
import time
import threading
import os
from _operator import index
#from numpy.random.mtrand import shuffle
import random
envLoopStr = os.getenv('traccar_client_loop')

maxLinNumberStr = os.getenv('traccar_client_maxLineNumber')

shuffleTimesStr = os.getenv('traccar_client_shuffleTimes')


global envLoop,shuffleTimes,maxLinNumber

if(envLoopStr==None):
    envLoop=2
else:
    envLoop=int(envLoopStr)
    
if(shuffleTimesStr==None):
    shuffleTimes=1
else:
    shuffleTimes=int(shuffleTimesStr)

if(maxLinNumberStr==None):
    print("setting variable maxLinNumber=840")
    maxLinNumber=800
else:
    maxLinNumber=int(maxLineNumberStr)



#positionObj = { "valid":False, "lat":"0", "lon":"0", "alt":"0", "hdop":"0", "speed":"0" ,"line":0}

class positionObj:
    valid=False
    lat="0"
    alt="0"
    hdop="0"
    speed="0"
    line=0



allPositionObjsList=[]
allPositionObjsMap ={ }
positionFromLine=1

def fetchFromList_L2():
    global positionFromLine
    returnObj=positionObj()
    if(positionFromLine>maxLinNumber):
        positionFromLine=1
    
    # starting time
    start = time.time()
    ##print("Performance hit code" ,positionFromLine)
    #Below code can cause performance impact, as before finding a matching element, alll 
    #elements of the list are shuffled and then search is applied to find an element.
    for x in range(1,shuffleTimes):
        random.shuffle(allPositionObjsList)
    for x in range(1,len(allPositionObjsList)) :
        obj=  allPositionObjsList[x]
        ##print(obj.line)
        ##print("{obj.line}",obj.line)
        ##print("{positionFromLine}",positionFromLine)
        if(int(obj.line)==int(positionFromLine)):
            returnObj= obj
            ##print("found object")
    # end time
    end = time.time()
    
    timeDiffInMS=(end-start)*1000
    # total time taken
    print(f"Total time taken to find element at index '{positionFromLine}' is: {timeDiffInMS} milli seconds")
    return returnObj

def fetchFromList_L1():
    global positionFromLine
    returnObj=positionObj()
    if(positionFromLine>len(allPositionObjsList)):
        positionFromLine=1
    
    # starting time
    start = time.time()
    if(positionFromLine%2!=0):
        return allPositionObjsMap[positionFromLine]
    else:
        print("Performance hit code" ,positionFromLine)
        #Below code can cause performance impact, as before finding a matching element, alll 
        #elements of the list are shuffled and then search is applied to find an element.    
        for x in range(1,shuffleTimes):
            random.shuffle(allPositionObjsList)
        
        for x in range(1,len(allPositionObjsList)):
            obj=  allPositionObjsList[x]
            if(int(obj.line)==int(positionFromLine)):
                returnObj= obj
                break
    # end time
    end = time.time()
    
    # total time taken
    print(f"Total time taken to find element in case of performance impact code: {end - start}")
    return returnObj 

simplelog_interval=1
lock=threading.Lock()
RUNNING=True

def dumbloop(csv_reader):
    global RUNNING,simplelog_interval,lock,processedLine
    processedLine=1
    for line in csv_reader:
        if(processedLine==1):
            processedLine=processedLine+1
            continue
      
        if RUNNING == False:
            return
        if not len(line) >= 2:
            print("Simplelog skipping invalid line "+str(line))
            continue

        try:
            obj=positionObj()
            
            
            obj.lat=str(line[0])
            obj.lon=str(line[1])
            obj.line=str(line[2])
            obj.valid=True
            allPositionObjsList.append(obj)
            allPositionObjsMap.update({processedLine:obj})    
        except ValueError as err:
            print("Simplelog skipping invalid line "+str(line))
            continue
        processedLine=processedLine+1
   
        #print("Line is "+str(line))
        #print("line number is : "+ str(processedLine))
        
    print("Simplelog: FINISHED")

def loop(csv_reader):
    global RUNNING,simplelog_interval,lock,processedLine,singleObj
    singleObj=positionObj()
    processedLine=0
    for line in csv_reader:
        processedLine=processedLine+1
        time.sleep(simplelog_interval)

        if RUNNING == False:
            return

        if not len(line) == 2:
            print("Simplelog skipping invalid line "+str(line))
            continue

        try:
            lat=float(line[0])
            lon=float(line[1])
        except ValueError:
            print("Simplelog skipping invalid line "+str(line))
            continue

        lock.acquire()
        singleObj.line=processedLine
        singleObj.lat=str(line[0])
        singleObj.lon=str(line[1])
        singleObj.valid=True
        lock.release()
   
        #print("Line is "+str(line))
        #print("line number is : "+ str(processedLine))
        
    print("Simplelog: FINISHED")

def initProvider(config):
    global simplelog_interval
    print("Init simplelog provider...")
    if "Provider.simplelog" not in config:
        print("Provider.simplelog section missing from configuration, exiting")
        sys.exit(-1)
    
    provider_config=config['Provider.simplelog']
    simplelog_file=provider_config.get('file','log.csv')
    simplelog_interval=provider_config.getint('interval',1)

    print("Trying to read simeplelog from "+str(simplelog_file)+" with a position every  "+str(simplelog_interval)+" s")

    csv_f=open(simplelog_file)
    csv_reader=csv.reader(csv_f, delimiter=',')
    
    #loop(csv_reader)
    if(envLoop==None):
        t = threading.Thread(target=loop, args=(csv_reader,))
        print("Default loop is considered")
        t.start()
        return t
    else:
        dumbloop(csv_reader)
        print("dumb loop is considered")
    

def shutdown():
    global RUNNING
    RUNNING=False


def getPosition():
    global singleObj, lock,index,positionFromLine
    
    if(envLoop==None):
        lock.acquire()
        p=singleObj
        lock.release()
        return p
    elif envLoop==1:
        positionFromLine=positionFromLine+1
        return fetchFromList_L1()
    elif envLoop==2:
        positionFromLine=positionFromLine+1
        return fetchFromList_L2()
