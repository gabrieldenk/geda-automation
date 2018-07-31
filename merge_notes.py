#!/usr/bin/python

#Author:  Gabriel Denk
#Revision: 0.2

import sys
import os
import math


#==============================================================================
def IsTooldefLine(gerbLine):
    return gerbLine[0:4] == "%ADD"

#==============================================================================
def GetToolCode(gerbLine):
    #ignore file terminator line
    if gerbLine.find("M02") != -1: return ""

    idxD = gerbLine.find("ADD")
    idx1 = gerbLine.find("G54D")
    #handle tooldef line
    if idxD != -1:
        idxD +=2 #move to second "D" in "ADD"
        idxC = gerbLine.find("C",idxD)
        if idxC == -1: return ""
        return gerbLine[idxD:idxC]
    #handle tool select line
    elif idx1 != -1:
        idx1 += 3 #move to "D" in "G54D"
        idx2 = gerbLine.find("*",idx1)
        if idx2 == -1: return ""
        return gerbLine[idx1:idx2]
    else: return ""

#==============================================================================
def GetToolSize(gerbLine):
    idx1 = gerbLine.find(",")
    idx2 = gerbLine.find("*%",idx1)
    if idx1 == -1 or idx2 == -1: return -1
    return float(gerbLine[idx1+1:idx2])

#==============================================================================        
def ModifyToolSize(gerbLine, newSize):
    if not IsTooldefLine(gerbLine): return ""
    idx1 = gerbLine.find(",")
    idx2 = gerbLine.find("*%",idx1)
    if idx1 == -1 or idx2 == -1: return ""
    return "%s%1.4f%s" % (gerbLine[0:idx1+1],newSize,gerbLine[idx2:150])

#==============================================================================
def GetLayerName(fName):
    gerbFile = open(fName)
    result = ""
    for line in gerbFile:
        if line.find("G04 Title:") != -1:
            idx1 = line.find(", ")
            idx2 = line.find(" *")
            if idx1 == -1 or idx2 == -1: result = ""
            else: result = line[idx1+2:idx2]
            break
    gerbFile.close()
    return result

#==============================================================================


def DoMerge(projName,gerbDir):
    maxLineWidth = 0.005
    notesLayerName = "Notes"
    gerberPath = "./%s/" % gerbDir
    
    #find gerber file with layer name notesLayerName
    gfileList = os.listdir(gerberPath)
    inFileName = ""
    for fName in gfileList:
        if fName.find(".group") != -1:
            if GetLayerName(gerberPath + fName) == notesLayerName:
                inFileName = gerberPath + fName
                break
    if len(inFileName) < 2:
        raise Exception("Error: Could not find gerber file for layer named \"%s\"." % notesLayerName)
    
    inputFile = open(inFileName, 'r')
    print("Input file (with \"%s\" layer): %s" % (notesLayerName,inFileName))
    
    #determine output file name
    mergeFileName = gerberPath + projName + ".fab.gbr"
    print("Output, merged file: %s" % mergeFileName)

    #find smallest tool D code
    foundTooldefs = False
    smallestSize = 900.0
    smallestToolCode = ""
    smallestTooldefLine = ""
    for gerbLine in inputFile:
        if IsTooldefLine(gerbLine):
            foundTooldefs = True
            size = GetToolSize(gerbLine)
            if size < smallestSize and size > 0.001:
                smallestSize = size
                smallestTooldefLine = gerbLine
        elif foundTooldefs:
            break
    if len(smallestTooldefLine) < 10:
        raise Exception("Error: Could not find tooldefs in input file.")
    smallestToolCode = GetToolCode(smallestTooldefLine)
    
    print("Using tool %s with size %1.1f mils from input file." % (smallestToolCode, smallestSize*1000))
    
    #shrink tool size if needed
    if smallestSize > maxLineWidth:
        smallestSize = maxLineWidth
        smallestTooldefLine = ModifyToolSize(smallestTooldefLine, maxLineWidth)
        print("Changing line width to %1.1f mils." % (maxLineWidth*1000))
    
    #load merged file into memory
    mergeFile = open(mergeFileName,'r')
    mergeList = mergeFile.readlines()
    mergeFile.close()
        
    #add D code to merged file
    foundTooldefs = False
    for i in range(0, 100):
        if IsTooldefLine(mergeList[i]):
            mergeList.insert(i, smallestTooldefLine)
            foundTooldefs = True
            insLine = i
            break
    if not foundTooldefs: raise Exception("Error: Could not find tooldefs in merged file.")
    
    print("Adding tooldef to merge file at line %d." % insLine)
    
    #copy G54 block(s) from input file to merged file
    insertIdx = -1
    for i in range(0, 200):
        if mergeList[i].find("G54D") != -1:
            insertIdx = i
            break
    if insertIdx == -1: raise Exception("Error: Could not find any G54 codes in merged file.")
    
    inG54Sec = False
    inputFile.seek(0)
    numLinesCoppied = 0
    for gerbLine in inputFile:
        toolCode = GetToolCode(gerbLine)
        if len(toolCode) > 1 and not IsTooldefLine(gerbLine):
            inG54Sec = toolCode == smallestToolCode
        if inG54Sec:
            mergeList.insert(insertIdx, gerbLine)
            insertIdx += 1
            numLinesCoppied += 1
            
    print("Added %d lines from input file to merged file." % numLinesCoppied)
    
    #save merged file to memory
    mergeFile = open(mergeFileName, 'w')
    mergeFile.writelines(mergeList)
    mergeFile.close()
    
    #delete input file
    inputFile.close()
    os.remove(inFileName)
