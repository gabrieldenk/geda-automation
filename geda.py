#!/usr/local/bin/python3
##!/usr/bin/python

#ToDo
#Auto-generate drc.scm from ~/.gEDA/gschemrc.
#Make footprint finder able to promote embedded attribute.
#Move references to Eclipse and TextEdit to G class.

__version__ = "0.1.12"

import os
import sys
import re
import merge_notes
import schparse
import traceback
import time
import math
import readline #importing this makes the input() function work sooo much better even though it appears unused
import multiprocessing
from tkinter import Tk


schDirs = ["Schematic","schematic","sch","Sch"]
layoutDirs = ["Layout","layout"]
#bomHeadings = ["Item","Quantity","Reference","Value","Description","Rating","Tolerance","Vendor","Vendor Part","Distrib","Distrib Number","Details","Footprint"]
bomHeadings = ["Item","Quantity","Reference","Value","Description","Rating","Tolerance","Vendor","Vendor Part","Details","Footprint"]
folderHoldingThisScript = os.path.split(os.path.realpath(__file__))[0] + os.path.sep

class G(object):
    VerboseMode = False
    EngineerName = "Gabriel Denk"
    GerbDir = "Gerber"
    ElemDir = os.path.join(os.path.expanduser('~'), "geda/elements")
    GedaCfgDir = ".gEDA"
    FootprintAttrib = "footprint"
    RefDesAttrib = "refdes"
    ValueAttrib = "value"
    DescAttrib = "description"
    VendorAttrib = "vendor"
    PNumAttrib = "vendor_part"
    RatingAttrib = "rating"
    TolAttrib = "tolerance"
    DetailsAttrib = "details"
    NetAttrib = "net"
    SlotAttrib = "slot"
    CurrentAttrib = "current"
    SchRevStr = "REVISION"
    SchFileStr = "FILE"
    SchPageStr = "PAGE"
    SchCompanyBracket = '|'
    PrintScmPath = os.path.join(folderHoldingThisScript, "print.scm")
    Interpage = "interpage"
    InterpageTypes = ["to", "from", "bidir"]
    InterpgTo = 0
    InterpgFrom = 1
    InterpgBidi = 2
    NonGerberLayerNames = ["Keepouts"]
    NonGerberLayerTypes = ["notes"]
    TemplateDir = "~/geda/template"
    PrintablePageWidth = (8.5-1) * 25.4
    PrintablePageHeight = (11-1) * 25.4

    
class Local_gafrc(object):
    __drcScmPath = ""
    __localGafrcPath = ""
    
    @staticmethod
    def Create():
        Local_gafrc.__drcScmPath = os.path.join(os.path.expanduser('~'), ".gEDA", "drc.scm")
        if not os.path.exists(Local_gafrc.__drcScmPath):
            raise Exception('Could not find file "%s" containing component-library def.' % Local_gafrc.__drcScmPath)
        Local_gafrc.__localGafrcPath = os.path.join(DirSet.SchematicDir, "gafrc")
        os.system("cp %s %s" % (Local_gafrc.__drcScmPath, Local_gafrc.__localGafrcPath))
        
    @staticmethod
    def Cleanup():
        if Local_gafrc.__localGafrcPath: os.remove(Local_gafrc.__localGafrcPath)


class DirSet(object):
    __curDir = "" #set to t for top, l for layout, s for schematic, empty for not yet set
    TopDir = ""
    SchematicDir = ""
    LayoutDir = ""
    
    @staticmethod
    def FindPaths():
        dr = os.getcwd().split(os.sep)
        outDr = []
        for d in dr:
            if d in schDirs: break
            elif d in layoutDirs: break
            else: outDr.append(d)
        DirSet.TopDir = os.sep.join(outDr)
        os.chdir(DirSet.TopDir)
        #print("TopDir: %s" % DirSet.TopDir)

        found = False
        for d in schDirs:
            schd = os.path.join(DirSet.TopDir, d)
            if os.path.isdir(schd):
                found = True
                DirSet.SchematicDir = os.path.join(DirSet.TopDir, schd)
                break
        if not found: raise Exception("Schematic subdir not found.")
        #print("SchDir: %s" % DirSet.SchematicDir)

        found = False
        for d in layoutDirs:
            layoutd = os.path.join(DirSet.TopDir, d)
            if os.path.isdir(layoutd):
                found = True
                DirSet.LayoutDir = os.path.join(DirSet.TopDir, layoutd)
                break
        if not found: raise Exception("Layout subdir not found.")
        #print("LayoutDir: %s" % DirSet.LayoutDir)

    
    @staticmethod
    def TopLevel():
        if DirSet.__curDir == 't': return
        __curDir = 't'
        os.chdir(DirSet.TopDir)
    
    @staticmethod
    def Schematic():
        if DirSet.__curDir == 's': return

        os.chdir(DirSet.SchematicDir)
    
    @staticmethod
    def Layout():
        if DirSet.__curDir == 'l': return
        os.chdir(DirSet.LayoutDir)

class CmdThread(multiprocessing.Process):
    def __init__(self, commands, printStrings):
        super().__init__()
        self.__commands = commands
        self.__pStrs = printStrings
        for cmd in commands:
            if cmd.endswith('&'):
                print("Warning: CmdThread invoked with forked command.")
    def run(self):
        for i in range(len(self.__commands)):
            if i < len(self.__pStrs): print(self.__pStrs[i])
            os.system(self.__commands[i])
        i += 1
        if i < len(self.__pStrs): print(self.__pStrs[i])

def AddS(count):
    if count == 1: return ""
    else: return "s"

def SchPgName(pg, pgs, pName, prefix=""):
    if pg == -1:
        if pgs == 1:
            fName = "%s%s.sch" % (prefix, pName)
        else:
            fName = " ".join([prefix + pName + "_p%d.sch" % (i+1) for i in range(pgs)])
    elif pg >= 1 and pg <= pgs:
        if pgs == 1:
            fName = "%s%s.sch" % (prefix,pName)
        else:
            fName = "%s%s_p%d.sch" % (prefix, pName, pg)
    else: raise Exception("Schematic page number %d is invalid." % pg)
    return fName

def GetScreenDims():
    root = Tk()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return w, h

def FixDialogGeometry():
    width, height = GetScreenDims()
    if G.VerboseMode: print("Detected screen res %dx%d" % (width, height))
    baseFName = os.path.join(os.path.expanduser('~'), G.GedaCfgDir, "gschem-dialog-geometry")
    fName =  "%s_%dx%d" % (baseFName, width, height)
    if os.path.exists(fName):
        print("Using %s for dialog geometry." % fName)
        os.system("cp %s %s" % (fName, baseFName))
    else:
        fName = "%s_default" % baseFName
        if os.path.exists(fName):
            print("Using default dialog geometry.")
            os.system("cp %s %s" % (fName, baseFName))
        else: print('Warning: Missing default dialog geometry file "%s"' % fName)
  
def EditSchem(pgs, pName):
    FixDialogGeometry()
    DirSet.Schematic()
    pgName = SchPgName(-1, pgs, pName)
    if pgs == 1:
        print("Opening schematic %s.sch..." % pName)
        os.system('gschem %s &' % pgName)
    else:
        print("Opening schematic %s_p1-%d..." % (pName, pgs))
        os.system('gschem %s &' % pgName)

def FixLayoutColors():
    DirSet.Layout()
    prefsFName = os.path.expanduser('~') + "/.pcb/preferences"
    if G.VerboseMode: print('Editing prefs file "%s".' % prefsFName)
    with open(prefsFName, 'r') as prefsFile:
        prefsLines = prefsFile.readlines()
    for i, line in enumerate(prefsLines):
        if line.split(' ')[0] == "color-file":
            prefsLines[i] = "color-file = " + os.path.abspath(os.getcwd()) + "/colors" + os.linesep
            with open(prefsFName, 'w') as prefsFile:
                prefsFile.writelines(prefsLines)
            break
    if G.VerboseMode: print("Layout colors loaded from colors file.")

def EditLayout(pName):
    FixLayoutColors()
    DirSet.Layout()
    os.system('pcb %s.pcb &' % pName)

def GetElementPin1(elementName):
    elemPath = os.path.join(G.ElemDir, elementName)
    if not os.path.isfile(elemPath):
        raise Exception('Element file "%s" not found.' % elemPath)
    with open(elemPath, 'r') as elemFile:
        for line in elemFile:
            line = line.strip()
            if line.startswith("#XY_Pin1"):
                return line.split("=")[1].strip()
            elif line.startswith("Pad["):
                parts = line[len("Pad["):-1].split(" ")
                pinNum = parts[8][1:-1]
                if pinNum == '1': return '1'
            elif line.startswith("Pin["):
                parts = line[len("Pin["):-1].split(" ")
                pinNum = parts[7][1:-1]
                if pinNum == '1': return '1'
        return ''

def GenXYFile(pName):
    DirSet.Layout()
    warnings = 0
    print("Generating X-Y file %s-xy.txt..." % pName)
    #make temporary PCB file with pin 1 designation added to parts with alphabetic pun numbers
    with open("%s.pcb" % pName, 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    i = 0
    while i < len(pcbLines):
        line = pcbLines[i].strip()
        #find Element headers
        if line.startswith("Element["):
            parts = line[len("Element["):-1].split(' ')
            elementName = parts[1][1:-1]
            refDes = parts[2][1:-1]
            if not elementName:
                print("W: Unnamed element at line %d." % (i+1))
                warnings += 1
                i += 3
                continue
            if G.VerboseMode: print('Checking element "%s" for %s...' % (elementName, refDes))
            #find corresponding element file in library
            pinOne = GetElementPin1(elementName)
            if not pinOne:
                print('W: Element "%s" for %s has no pin 1 and no "#XY_Pin1=x" line.' % (elementName, refDes))
                warnings += 1
                i += 3 #advance by minimum Element section length
                continue
            elif pinOne == '1':
                i += 3
                continue
            else:
                #rename appropriate pin
                while True:
                    i += 1
                    line = pcbLines[i].strip()
                    if line == ')':
                        raise Exception('Can''t find pin "%s" in element "%s", %s.' % (pinOne, elementName, refDes))
                    else:
                        if line.startswith('Pad['):
                            argPos = 8
                            lineHdr = 'Pad'
                        elif line.startswith('Pin['):
                            argPos = 7
                            lineHdr = 'Pin'
                        else: continue
                        parts = line[len(lineHdr)+1:-1].split(" ")
                        pinNum = parts[argPos][1:-1]
                        if pinNum == pinOne:
                            parts[argPos] = '"1"'
                            pcbLines[i] = "\t%s[%s]\n" % (lineHdr, " ".join(parts))
                            if G.VerboseMode:
                                print('Using pin "%s" as pin 1 in element "%s", %s.' % (pinOne, elementName, refDes))
                            break
        else: i += 1

    with open("%s_XY_temp.pcb" % projName, 'w') as tmpFile:
        tmpFile.writelines(pcbLines)
    
    #generate xy file using PCB Designer
    os.system('pcb -x bom --xyfile %s-xy.txt %s_XY_temp.pcb' % (pName, pName))
    
    #delete temporary PCB file and BOM file generated during processing
    os.remove("%s_XY_temp.pcb" % projName)
    os.remove("%s_XY_temp.bom" % projName)
    
    print("%d warnings." % warnings)
    
    
#Note:  If print.scm is modified, delete the file "~/.cache/guile/ccache/2.0-LE-8-2.0/Users/gabrield/Documents/Scripts/geda/print.scm.go"
#Note:  Default paper size must be set in ~/.gEDA/gschemrc.  Add line like "(paper-size 17.0 11.0)".
def GenSchPDF(pgs, pName):
    DirSet.Schematic()
    print("Creating schematic PDF as %s-sch.pdf..." % pName)
    #Make PDFs from gschem PostScript output
    if pgs == 1:
        os.system("gschem -p -o %s.ps -s %s %s.sch" % (pName, G.PrintScmPath, pName))
        os.system("ps2pdf -sPAPERSIZE=11x17 %s.ps %s-Sch.pdf" % (pName, pName))
        os.remove("%s.ps" % pName)
    else:
        pageFNames = []
        for i in range(pgs):
            pn = "%s_p%d" % (pName, i+1)
            os.system("gschem -p -o %s.ps -s %s %s.sch" % (pn, G.PrintScmPath, pn))
            os.system("ps2pdf -sPAPERSIZE=11x17 %s.ps" % pn)
            os.remove("%s.ps" % pn) #remove temporary .ps files
            pageFNames.append(pn + ".pdf")
        #Combine PDFs into one document
        os.system("gs -q -sDEVICE=pdfwrite -sOutputFile=%s-Sch.pdf -dBATCH -dNOPAUSE %s" % (pName, " ".join(pageFNames)))
        #Delete individual PDFs
        for fn in pageFNames: os.remove(fn)
        
def GenLayoutPDF(pName):
    psFile = "temp.ps"
    #psFile = "%s.ps" % pName
    DirSet.Layout()
    FixLayoutColors()
    print("Creating layout PDF as %s-Layout.pdf..." % pName)
    width, height, lwidth, lheight = GetBoardDims(pName, printResult=False)
    if lwidth > lheight: #swap dimensions if PCB decided to go landscape
        x = lwidth; lwidth = lheight; lheight = x
    xScale = G.PrintablePageWidth / lwidth
    yScale = G.PrintablePageHeight / lheight
    #print("w:%f, h:%f, xs: %f, ys:%f" % (lwidth, lheight, xScale, yScale))
    scale = min(xScale, yScale)
    if scale >= 1.0:
        print("  Scaling by %d%% to fill page." % round(scale*100))
    else:
        print("  Scaling by %d%% to fit in page." % round(scale*100))
    cmd1 = "pcb -x ps --psfile temp.ps --outline --ps-color --scale %0.2f --auto-mirror %s.pcb" % (scale,pName)
    cmd2 = "ps2pdf %s %s-Layout.pdf" % (psFile, pName)
    if G.VerboseMode:
        print("Shell commands:")
        print("   %s" % cmd1)
        print("   %s" % cmd2)
    os.system(cmd1)
    os.system(cmd2)
    if G.VerboseMode: print('Deleting file "%s".' % psFile)
    os.remove(psFile)

def GenLayoutPNG(pName, dpi=1000):
    #startTime = time.monotonic()
    DirSet.Layout()
    print("Generating photographic PNGs of layout at %ddpi (this takes time)..." % dpi)
    silk = "white"
    mask = "green"
    plating = "tinned"
    silkColors = ['white','yellow','black']
    maskColors = ['green', 'red', 'blue', 'purple', 'black', 'white']
    layerPat = re.compile('Layer\\([1-9]+ "')
    lineArcPat = re.compile('\\s*(Line|Arc)\\[[0-9]+')
    finishPat = re.compile('[ \t]*Text\\[([0-9\\.]+(mil|mm)? +){4,4}"finish[ :]', re.IGNORECASE)
    maskPat = re.compile('[ \t]*Text\\[([0-9\\.]+(mil|mm)? +){4,4}".*mask[ :]', re.IGNORECASE)
    silkPat = re.compile('[ \t]*Text\\[([0-9\\.]+(mil|mm)? +){4,4}"(silk|legend)[ :/]', re.IGNORECASE)
    pcb = open("%s.pcb" % pName, 'r')
    tmp = open("tmp-file", 'w')
    layer = ""
    outlineCount = 0
    lineCount = 1
    for txtLine in pcb:
        if layerPat.match(txtLine) is not None:
            layer = txtLine.split('"')[1]
            if G.VerboseMode:
                if layer == 'outline': print("Found outline layer at line %d." % lineCount)
                elif layer == 'Notes': print("Found Notes layer at line %d." % lineCount)
        elif layer == 'outline' and lineArcPat.match(txtLine) is not None:
            #make outline lines/arcs very thin to work around bug in PNG renderer
            parts = txtLine.strip().split(" ")
            parts[4] = '0.01mil'
            txtLine = "\t" + " ".join(parts) + "\n"
            outlineCount += 1
        elif layer == 'Notes':
            #find notes relating to colors and platings
            if finishPat.match(txtLine) is not None:
                pat = re.compile('enig|gold', re.IGNORECASE)
                m = pat.search(txtLine)
                if m is None: gold = 501
                else: gold = m.start()
                silver = txtLine.lower().find("silver", 17)
                if silver < 0: silver = 502
                pat = re.compile('hasl|tin', re.IGNORECASE)
                m = pat.search(txtLine)
                if m is None: tinned = 500
                else: tinned = m.start()
                if G.VerboseMode: print("tin:%d gold:%d silver:%d" % (tinned, gold, silver))
                if tinned < gold and tinned < silver: plating = "tinned"
                elif gold < silver: plating = "gold"
                else: plating = "silver"
            elif maskPat.match(txtLine) is not None:
                for color in maskColors:
                    if txtLine.lower().find(color,17) > 0:
                        mask = color
                        break
                if G.VerboseMode: print('Found mask color "%s" at line %d.' % (mask, lineCount))
            elif silkPat.match(txtLine) is not None:
                for color in silkColors:
                    if txtLine.lower().find(color,17) > 0:
                        silk = color
                        break
                if G.VerboseMode: print('Found silk color "%s" at line %d.' % (silk, lineCount))
            
        tmp.write(txtLine)
        lineCount += 1
    pcb.close()
    tmp.close()
    if G.VerboseMode: print("Narrowed %d outline strokes." % outlineCount)
    cmdTop = "pcb -x png --outfile %s-top.png " % pName
    cmdBot = "pcb -x png --outfile %s-bot.png --photo-flip-x " % pName
    cmd = "--dpi %d --format PNG --photo-mode --photo-mask-colour %s --photo-plating %s " % (dpi,mask,plating)
    cmd += "--photo-silk-colour %s tmp-file" % silk
    topStrs = ["   generating top image..."]
    topCmds = [cmdTop + cmd]
    botStrs = ["   generating bottom image..."]
    botCmds = [cmdBot + cmd]
    if G.VerboseMode:
        print("PCB command lines:")
        print("   %s%s" % (cmdTop,cmd))
        print("   %s%s" % (cmdBot,cmd))
    topStrs.append("   cropping top image...")
    botStrs.append("   cropping bottom image...")
    #using ImageMagick
    cmd = "convert %s-top.png -trim +repage -bordercolor black -border 100x100 %s-top.png" % (pName, pName)
    if G.VerboseMode:
        print("   %s" % cmd)
    topCmds.append(cmd)
    cmd = "convert %s-bot.png -trim +repage -bordercolor black -border 100x100 %s-bot.png" % (pName, pName)
    if G.VerboseMode:
        print("   %s" % cmd)
    botCmds.append(cmd)
    topStrs.append("   Top image done.")
    botStrs.append("   Bottom image done.")
    TopCmd = CmdThread(topCmds, topStrs)
    TopCmd.start()
    BotCmd = CmdThread(botCmds, botStrs)
    BotCmd.start()
    TopCmd.join()
    BotCmd.join()
    os.remove("tmp-file")
    #endTime = time.monotonic()
    #print("%fs" % (endTime-startTime))

def FindSimilarHeading(hdgName):
    hdgName = hdgName.replace('_', ' ').lower().strip()
    i = 0
    for hdr in bomHeadings:
        if hdgName == hdr.lower(): return i
        i += 1
    i = 0
    for hdr in bomHeadings:
        if hdgName[0:3] == hdr.lower()[0:3]: return i
        i += 1
    if hdgName == "qty": hdgName = "quantity"
    i = 0
    for hdr in bomHeadings:
        if hdgName == hdr.lower(): return i
        i += 1
    return -1

def GenColumnAssociations(fileHeadings):
    associations = []
    for heading in fileHeadings:
        colNum = FindSimilarHeading(heading)
        if colNum == -1: raise Exception('Unknown column heading "%s".' % heading)
        associations.append(colNum)
    return associations

def RCValToNum(valStr):
    unitStart = -1
    for i in range(len(valStr)):
        if not valStr[i].isdigit() and valStr[i] != '.':
            unitStart = i
            break
    if unitStart == -1:
        valStr += '@'
        unitStart = len(valStr) -1
    try:
        val = float(valStr[0:unitStart])
    except:
        val = 0
    siPrefix = valStr[unitStart]
    if siPrefix == 'p': mult = 1e-12
    elif siPrefix == 'n': mult = 1e-9
    elif siPrefix == 'u': mult = 1e-6
    elif siPrefix == 'm': mult = 1e-3
    elif siPrefix == '@': mult = 1
    elif siPrefix in ['k', 'K']: mult = 1e3
    elif siPrefix == 'M': mult = 1e6
    else: mult = 1
    return val * mult
    
def CheckBoMForErrors(bomLines):
    numWarnings = 0
    itemCol = FindSimilarHeading("item")
    refdesCol = FindSimilarHeading("reference")
    valueCol = FindSimilarHeading("value")
    ratingCol = FindSimilarHeading("rating")
    toleranceCol = FindSimilarHeading("tolerance")
    descCol = FindSimilarHeading("description")
    vendorCol = FindSimilarHeading("vendor")
    vendorPartCol = FindSimilarHeading("vendor_part")
    footprintCol = FindSimilarHeading("footprint")
    #check for duplicate lines
    cap = {}
    res = {}
    part = {}
    for bline in bomLines[1:]:
        fields = bline.split("\t")
        if fields[valueCol].startswith("DNI"): continue
        if fields[refdesCol].startswith('C') or fields[refdesCol].startswith('DC'):
            val = "%0.1f" % (RCValToNum(fields[valueCol]) * 1e12) #everything in pF
            cap[int(fields[itemCol])] = "%s %s" % (val, fields[ratingCol])
        elif fields[refdesCol].startswith('R'):
            val = "%0.1f" % (RCValToNum(fields[valueCol]) * 1e3) #everything in m-ohms
            res[int(fields[itemCol])] = "%s %s %s" % (val, fields[toleranceCol], fields[footprintCol])
        part[int(fields[itemCol])] = "%s %s" % (fields[vendorCol].lower(), fields[vendorPartCol])
    print("Checking for duplicate capacitor BoM lines...")
    capList = list(cap.values())
    for C in cap:
        if capList.count(cap[C]) > 1:
            fields = bomLines[C].split('\t')
            print("  W: Item %d, %s, %s" % (C, fields[valueCol], fields[ratingCol]))
            numWarnings += 1
    print("Checking for duplicate resistor BoM lines...")
    resList = list(res.values())
    for R in res:
        if resList.count(res[R]) > 1:
            fields = bomLines[R].split('\t')
            print("  W: Item %d, %s, %s" % (R, fields[valueCol], fields[toleranceCol]))
            numWarnings += 1
    print("Checking for lines with duplicate manufacturer part numbers...")
    partList = list(part.values())
    for P in part:
        if partList.count(part[P]) > 1:
            fields = bomLines[P].split('\t')
            print("  W: Item %d, %s, %s %s" % (P, fields[valueCol], fields[vendorCol], fields[vendorPartCol]))
            numWarnings += 1
    #check for missing fields
    print("Checking for missing attributes...")
    for bline in bomLines[1:]:
        fields = bline.split("\t")
        if not fields[valueCol]:
            print("  W: Item %s missing Value attribute (%s; %s)" % (fields[itemCol],fields[descCol], fields[refdesCol]))
            numWarnings += 1
        if not fields[vendorCol] or not fields[vendorPartCol]:
            print("  W: Item %s missing Vendor/VendorPart attribute (%s; %s)" % (fields[itemCol],fields[descCol], fields[refdesCol]))
            numWarnings += 1
    if numWarnings == 0: print("No problems found.")
    else: print("%d warnings found." % numWarnings)

def GetSchCompany(pgs, pName):
    DirSet.Schematic()
    companyLst = []
    for pg in range(pgs):
        fName = SchPgName(pg+1, pgs, pName)
        if G.VerboseMode: print('Retrieving company name from file "%s"' % fName)
        if not os.path.isfile(fName): raise Exception('Schematic file "%s" not found' % fName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        foundCName = False
        for item in sch.Items:
            if not isinstance(item, schparse.Text): continue
            comp = item.Value[0].strip()
            if comp.startswith(G.SchCompanyBracket) and comp.endswith(G.SchCompanyBracket):
                companyLst.append(comp[1:-1].strip())
                foundCName = True
                break
        if not foundCName: raise Exception("Company name text not found on page %d." % (pg+1))
    companyName = companyLst[0]
    for cname in companyLst:
        if cname != companyName:
            raise Exception("Company names not consistent across schematic pages.")
    return companyName

def CreateBoM(pgs, pName):
    DirSet.Schematic()
    print("Creating bill of materials (BoM) from schematic...")
    Local_gafrc.Create()
    cmd = "gnetlist -g bom2 -o tempfile %s " % SchPgName(-1, pgs, pName)
    if G.VerboseMode: print("Command:  %s" % cmd)
    os.system(cmd)
    with open("tempfile", 'r') as bomFile:
        bomLines = bomFile.readlines()
    os.remove("tempfile")
    colHeadings = bomLines[0].split(':')
    del bomLines[0]
    bomLines.sort()
    assoc = GenColumnAssociations(colHeadings)
    itemCol = FindSimilarHeading("item")
    if itemCol == -1: raise Exception("Can't find item column among formatted headers.")
    descCol = FindSimilarHeading("description")
    if descCol == -1: raise Exception("Can't find description column among formatted headers.")
    refdesCol = FindSimilarHeading("reference")
    if refdesCol == -1: raise Exception("Can't find reference designator column among formatted headers.")
    fmtBom = []
    fmtBom.append("\t".join(bomHeadings) + os.linesep)
    j = 1
    for line in bomLines:
        fmtFields = list(range(len(bomHeadings)))
        fields = line.strip().split(':')
        if len(fields) > len(colHeadings):
            raise Exception("Colon character found in part field.  Line...\n%s" % line)
        i = 0
        for field in fields:
            if field == "unknown": field = ""
            fmtFields[assoc[i]] = field
            i += 1
        fmtFields[itemCol] = "%d" % j
        fmtFields[refdesCol] = fmtFields[refdesCol].replace(',', ', ')
        if fmtFields[descCol] != "no_bom":
            fmtBom.append("\t".join(fmtFields) + os.linesep)
            j += 1
    header = ['Bill Of Materials' + os.linesep]
    mismatch, revs = GetSchRevs(pgs, pName)
    if mismatch: print('Warning: Inconsistent revision numbers across schematic pages.')
    header.append('%s r%s%s' % (pName, revs[0], os.linesep))
    t = time.localtime()
    header.append('%d/%d/%d %d:%02d%s' % (t.tm_mon, t.tm_mday, t.tm_year, t.tm_hour, t.tm_min, os.linesep))
    header.append(os.linesep)
    companyName = GetSchCompany(pgs, pName)
    print("Found company name '%s'" % companyName)
    header.append('%s%s' % (companyName, os.linesep))
    header.append(os.linesep)
    header.append('Engineer:  %s%s' % (G.EngineerName, os.linesep))
    header.append(os.linesep)
    header.append(os.linesep)
    with open("bom.tsv", 'w') as bomFile:
        bomFile.writelines(header)
        bomFile.writelines(fmtBom)
    print("BoM generated with %d line items." % (j-1))
    Local_gafrc.Cleanup()
    CheckBoMForErrors(fmtBom)

def MergeNotes(pName):
    DirSet.Layout()
    print("Merging notes layer into fab layer...")
    merge_notes.DoMerge(pName, G.GerbDir)
    gerbFiles = {}
    for fName in os.listdir(G.GerbDir):
        if fName.find(".group") != -1:
            gerbFiles[merge_notes.GetLayerName(os.path.join(G.GerbDir,fName))] = fName
    with open(pName+".pcb", 'r') as pcbFile:
        for line in pcbFile:
            if line.startswith("Layer"):
                args = line[line.find("(")+1:line.find(")")].split(" ")
                number = int(args[0])
                lName = args[1][1:-1]
                lType = args[2][1:-1]
                if lName in G.NonGerberLayerNames and lType in G.NonGerberLayerTypes:
                    filepath = gerbFiles[lName]
                    print('"%s" layer number %d called "%s" identified as temporary, deleting file "%s"' % (lType, number, lName, filepath))
                    os.remove(os.path.join(G.GerbDir, filepath))

def EditAttribs(pgs, pName):
    DirSet.Schematic()
    Local_gafrc.Create()
    cmd = "gattrib -v %s &" % SchPgName(-1, pgs, pName)
    if G.VerboseMode: print("Command:  %s." % cmd)
    os.system(cmd)
    time.sleep(5)
    Local_gafrc.Cleanup()
  
def GenGerbers(pName):
    DirSet.Layout()
    print("Generating Gerber files...")
    if not os.path.isdir(G.GerbDir):
        os.makedirs(G.GerbDir)
        if G.VerboseMode: print("Gerber directory created.")
    cmd = "rm %s%s*" % (G.GerbDir, os.sep)
    if G.VerboseMode: print("Command: %s" % cmd)
    os.system(cmd)
    cmd = "pcb -x gerber --gerberfile %s%s%s %s.pcb" % (G.GerbDir,os.sep,pName,pName)
    if G.VerboseMode: print("Command: %s" % cmd)
    os.system(cmd)
    
def ViewGerber():
    DirSet.Layout()
    os.system("gerbv %s/* &" % G.GerbDir)
    
def G2P(pgs, pName):
    DirSet.TopLevel()
    print("Exporting schematic to layout...")
    Local_gafrc.Create()
    cmd = "gsch2pcb -v --skip-m4 --elements-dir %s " % G.ElemDir
    cmd += "--use-files %s " % SchPgName(-1, pgs, pName, "./Schematic/")
    cmd += "-o ./Layout/%s" % pName
    if G.VerboseMode: print("Command:  %s" % cmd)
    os.system(cmd)
    Local_gafrc.Cleanup()

class OPC(object):
    def __init__(self, direction, pages, net, page):
        self.Direction = direction
        self.Pages = pages
        self.Net = net
        self.Page = page
    def Print(self):
        print("OnPg: %2d Dir: %5s Pg: %6s Net: %s" % (self.Page, G.InterpageTypes[self.Direction], ",".join(["%d"%z for z in self.Pages]), self.Net))
    
def CheckOffpageConnectors(pgs, pName):
    if pgs == 1:
        print("Nothing to check on a 1-page schematic.")
        return
    DirSet.Schematic()
    warnings = 0
    errors = 0
    #parse schematic files, build database of OPCs
    db = {}
    for page in range(pgs):
        fName = SchPgName(page+1, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        for item in sch.Items:
            if isinstance(item, schparse.Component):
                interpgPos = item.Basename.find(G.Interpage)
                if interpgPos != -1:
                    interpgPos += len(G.Interpage)
                    if item.Basename[interpgPos] == '_': interpgPos += 1
                    e = item.Basename.find('-', interpgPos)
                    d = G.InterpageTypes.index(item.Basename[interpgPos:e])
                    n = item.GetAttrib("net")
                    if not n:
                        print("E: Missing or empty net attribute for OPC on page %d." % (page+1))
                        errors += 1
                        continue
                    n = n[0:n.rfind(':')] #trim off pin number
                    pp = item.GetAttrib("pages")
                    if not pp:
                        print('E: Missing or empty pages attribute (pg. %d, net "%s").' % (page+1, n))
                        errors += 1
                        continue
                    p = pp[pp.find(' '):len(pp)].replace(' ', '')
                    p = p.split(',')
                    if len(p) == 1 and p[0] == '?':
                        print("W: Skipping OPC with unassigned pages (pg. %d, net %s)." % (page+1, n))
                        warnings += 1
                        continue
                    try:
                        p = [int(z) for z in p]
                    except:
                        print('E: Bad pages attribute formatting "%s" (pg. %d, net "%s").' % (pp, page+1, n))
                        errors += 1
                        continue
                    opc = OPC(d, p, n, page+1)
                    if n in db: db[n].append(opc)
                    else: db[n] = [opc]
    if G.VerboseMode:
        for net in db:
            for opc in db[net]:
                opc.Print()
    print("\nChecking for duplicate OPCs...")
    for net in db:
        i = 1
        for opc in db[net]:
            for j in range(i, len(db[net])):
                if opc.Page == db[net][j].Page:
                    print("E: Duplicate OPCs on page %d for net %s." % (opc.Page, net))
                    errors += 1
            i += 1
    print("\nChecking for matching OPCs on indicated pages...")
    for net in db:
        for opc in db[net]:
            for pg in opc.Pages:
                found = False
                for o in db[net]:
                    if o.Page == pg:
                        found = True
                        break
                if not found:
                    print("E: Missing OPC match on page %d for %s on page %d." % (pg, net, opc.Page))
                    errors += 1
    print("\nChecking for OPCs with missing page indications...")
    for net in db:
        pageList = []
        for opc in db[net]:
            if not opc.Page in pageList:
                pageList.append(opc.Page)
        for opc in db[net]:
            missingPages = []
            for page in pageList:
                if page == opc.Page: continue #skip my own page
                if opc.Direction == G.InterpgFrom: #skip requirement if both are "from" direction
                    matchingOpc = 0
                    for op in db[net]:
                        if op.Page == page: matchingOpc = op
                    if matchingOpc != 0 and matchingOpc.Direction == G.InterpgFrom: continue
                if opc.Direction == G.InterpgTo: #skip requirement if both are "to" direction (this error will be caught later and shouldn't be reported twice)
                    matchingOpc = 0
                    for op in db[net]:
                        if op.Page == page: matchingOpc = op
                    if matchingOpc != 0 and matchingOpc.Direction == G.InterpgTo: continue
                if not page in opc.Pages: missingPages.append(page)
            if len(missingPages) > 0:
                if len(missingPages) == 1: pstr = "page"
                else: pstr = "pages"
                print("E: OPC on page %d for net %s is missing references to %s %s." % (opc.Page, net, pstr, ", ".join(["%d"%z for z in missingPages])))
                errors += 1
    print("\nChecking connection design rules...")
    for net in db:
        toCount = 0
        toList = []
        bidiCount = 0
        for opc in db[net]:
            if opc.Direction == G.InterpgTo:
                toCount += 1
                toList.append(opc.Page)
            if opc.Direction == G.InterpgBidi: bidiCount += 1
        if toCount > 1:
            print('E: Multiple "%s" OPCs for net %s (pp. %s).' % (G.InterpageTypes[G.InterpgTo], net, ", ".join(['%d'%z for z in toList])))
            errors += 1
        if toCount == 0 and bidiCount == 0:
            print('E: No OPC drivers for net %s' % net)
            errors += 1
        if bidiCount == 1:
            print('W: Net %s has only one "%s" OPC.' % (net, G.InterpageTypes[G.InterpgBidi]))
    print("")
    if warnings == 0: print("No warnings.")
    elif warnings == 1: print("1 warning found!")
    else: print("%d warnings found!" % warnings)
    if errors == 0: print("No errors.")
    elif errors == 1: print("1 error found!")
    else: print("%d errors found!" % errors)
    print("")
    
    
def RunDRC(pgs, pName):
    DirSet.Schematic()
    print("Running DRC on schematic...")
    Local_gafrc.Create()
    cmd = "gnetlist -o drc-%s.out -g drc2 -l scheme/drc2_rules.scm " % pName
    cmd += SchPgName(-1, pgs, pName)
    if G.VerboseMode: print("Command:  %s" % cmd)
    os.system(cmd)
    os.system("open drc-%s.out -a TextEdit" % pName)
    Local_gafrc.Cleanup()
    
def FindFootprints(pgs, pName):
    DirSet.Schematic()
    print("Looking for element files called out in footprint attributes...")
    numFPs = 0
    numErr = 0
    numMissing = 0
    for pg in range(pgs):
        if pgs > 1: print("Page %d:" % (pg+1))
        fName = SchPgName(pg+1, pgs, pName)
        if G.VerboseMode: print('Checking file "%s"' % fName)
        if not os.path.isfile(fName): raise Exception('Schematic file "%s" not found' % fName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        for item in sch.Items:
            if not isinstance(item, schparse.Component): continue
            refDes = item.GetAttrib(G.RefDesAttrib)
            if refDes:
                numFPs += 1
                footprint = item.GetAttrib(G.FootprintAttrib)
                if not footprint or footprint.startswith('?'):
                    print('   -Missing footprint for %s (%s | %s).' % (refDes, item.GetAttrib(G.ValueAttrib), item.GetAttrib(G.DescAttrib)))
                    numMissing += 1
                elif footprint == 'none':
                    if G.VerboseMode:
                        print('   "none" footprint for %s (%s | %s).' % (refDes, item.GetAttrib(G.ValueAttrib), item.GetAttrib(G.DescAttrib)))
                elif not os.path.isfile(os.path.join(G.ElemDir, footprint)):
                    print('   %s element not found for %s (%s | %s).' % (footprint, refDes, item.GetAttrib(G.ValueAttrib), item.GetAttrib(G.DescAttrib)))
                    numErr += 1
    print("")
    print("%d footprints checked, %d not found, %d missing." % (numFPs, numErr, numMissing))
            
def GetSchPageRev(pg, pgs, pName):
    DirSet.Schematic()
    rev = -1
    fName = SchPgName(pg, pgs, pName)
    parenCount = 0
    with open(fName, 'r') as schFile:
        for line in schFile:
            line = line.strip()
            if line in ["[", "{"]: parenCount += 1
            elif line in ["]", "}"]: parenCount -= 1
            elif parenCount == 0: 
                parts = line.split(':')
                if parts[0] == G.SchRevStr:
                    if len(parts) != 2: raise Exception("Title block revision text missing colon.")
                    rev = parts[1].strip()
    if rev == -1: raise Exception("Title block version text not found on page %d." % pg)
    if G.VerboseMode: print("Checking rev of %s:  %s" % (fName, rev))
    return rev

def GetSchRevs(pgs, pName):
    revs = []
    mismatch = False
    for pg in range(schPages):
        revs.append(GetSchPageRev(pg+1, schPages, projName))
    if schPages > 1:
        for pg in range(schPages-1):
            if revs[pg] != revs[pg+1]: mismatch = True
    return mismatch, revs

def SetSchPageRev(pg, pgs, pName, newRev):
    DirSet.Schematic()
    didChange = False
    fName = SchPgName(pg, pgs, pName)
    parenCount = 0
    with open(fName, 'r') as schFile:
        lines = schFile.readlines()
    idx = 0
    for line in lines:
        line = line.strip()
        if line in ["[", "{"]: parenCount += 1
        elif line in ["]", "}"]: parenCount -= 1
        elif parenCount == 0: 
            parts = line.split(':')
            if parts[0] == G.SchRevStr:
                line = "%s:  %s\n" % (G.SchRevStr, newRev)
                lines[idx] = line
                didChange = True;
        idx += 1
    if didChange:
        with open(fName, 'w') as schFile:
            schFile.writelines(lines)
    else: raise Exception("Title block version text not found on page %d." % pg)
    if G.VerboseMode: print("Changed rev of %s to %s" % (fName, newRev))
    
def FixTitleBlock(pg, pgs, pName):
    DirSet.Schematic()
    fName = SchPgName(pg, pgs, pName)
    parenCount = 0
    fixedFile = False
    fixedPNums = False
    with open(fName, 'r') as schFile:
        lines = schFile.readlines()
    idx = 0
    for line in lines:
        line = line.strip()
        if line in ["[", "{"]: parenCount += 1
        elif line in ["]", "}"]: parenCount -= 1
        elif parenCount == 0: 
            parts = line.split(':')
            if parts[0] == G.SchFileStr:
                line = "%s:  %s\n" % (G.SchFileStr, fName)
                lines[idx] = line
                fixedFile = True
            elif parts[0] == G.SchPageStr:
                line = "%s:  %d of %d\n" % (G.SchPageStr, pg, pgs)
                lines[idx] = line
                fixedPNums = True
        idx += 1
    if fixedFile or fixedPNums:
        with open(fName, 'w') as schFile:
            schFile.writelines(lines)
    if not fixedFile: raise Exception("%s text not found." % G.SchFileStr)
    if not fixedPNums: raise Exception("%s text not found." % G.SchPageStr)
    if G.VerboseMode: print("Fixed title block text of %s" % fName)
    
def IsElementSelected(pcbLines, idx):
    while True:
        line = pcbLines[idx].strip()
        if line == ")": return False
        if line.find("selected") >= 0: return True
        idx += 1
def SetTextScale(pName, scale, scope='selected'):
    if not scope in ['selected','all']: raise Exception("Invalid scope for SetTextScale.")
    DirSet.Layout()
    elementsChanged = 0
    with open(pName+".pcb", 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    lineNum = 0
    for line in pcbLines:
        if line.strip().startswith("Element["):
            if scope == "all" or IsElementSelected(pcbLines, lineNum):
                args = line[line.find("[")+1:line.find("]")].split(" ")
                args[9] = "%s" % scale
                pcbLines[lineNum] = "Element[%s]\n" % " ".join(args)
                elementsChanged += 1
        lineNum += 1
    if elementsChanged > 0:
        with open(pName+".pcb", 'w') as pcbFile:
            pcbFile.writelines(pcbLines)
    return elementsChanged

def SetSelectedTraceWidth(pName, width):
    DirSet.Layout()
    tracesChanged = 0
    with open(pName+".pcb", 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    lineNum = 0
    for line in pcbLines:
        line = line.strip()
        if line.startswith("Line"):
            args = line[line.find("[")+1:line.find("]")].split(" ")
            if 'selected' in args[6][1:-1].split(","):
                args[4] = width
                pcbLines[lineNum] = "\tLine[%s]\n" % " ".join(args)
                tracesChanged += 1
        lineNum += 1
    if tracesChanged > 0:
        with open(pName+".pcb", 'w') as pcbFile:
            pcbFile.writelines(pcbLines)
    return tracesChanged

def RemoveDuplicateTraces(pName):
    DirSet.Layout()
    tracesRemoved = 0
    totalTracesRemoved = 0
    with open(pName+".pcb", 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    lineNum = 0
    absLineNum = 0
    inCopperLayer = False
    layerNum = -1
    layerName = ""
    linesSeen = []
    numLines = len(pcbLines)
    parenCount = 0
    while lineNum < numLines:
        line = pcbLines[lineNum].strip()
        if not inCopperLayer:
            if line.startswith("Layer"):
                args = line[line.find("(")+1:line.find(")")].split(" ")
                if args[2] == '"copper"':
                    inCopperLayer = True
                    tracesRemoved = 0
                    linesSeen = []
                    layerNum = args[0]
                    layerName = args[1][1:-1]
        else: #in copper layer section
            if line == "(":
                parenCount += 1
            elif line.startswith("Line") or line.startswith("Arc"):
                try:
                    linesSeen.index(line)
                    if G.VerboseMode:
                        print("Deleting %05d %s" % (absLineNum, line))
                    del pcbLines[lineNum]
                    lineNum -= 1
                    numLines -= 1
                    tracesRemoved += 1
                except:
                    linesSeen.append(line)
            elif line == ")":
                parenCount -= 1
                if parenCount == 0:
                    print("%d lines/arcs removed from layer %s (%s)" % (tracesRemoved, layerNum, layerName))
                    totalTracesRemoved += tracesRemoved
                    inCopperLayer = False
        lineNum += 1
        absLineNum += 1
    if totalTracesRemoved > 0:
        with open(pName+".pcb", 'w') as pcbFile:
            pcbFile.writelines(pcbLines)
    print("%d total lines/arcs removed." % totalTracesRemoved)

def GetTraceAngle(args):
    coords = []
    for i in range(4):
        if args[i].endswith('mm'):
            coords.append(float(args[i][0:-2]))
        elif args[i].endswith('mil'):
            coords.append(float(args[i][0:-3]) * 0.0254)
        elif args[i].isdigit():
            coords.append(int(args[i]) * 0.000254)
        else: raise Exception('Unrecognized coordinate format "%s".' % args[i])
    dx = coords[2] - coords[0]
    dy = coords[3] - coords[1]
    return round(math.atan2(dy, -dx) * 180 / math.pi, 3)

def SelectOddAngledTraces(pName):
    DirSet.Layout()
    tracesSelected = 0
    totalTracesSelected = 0
    with open(pName+".pcb", 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    lineNum = 0
    inCopperLayer = False
    layerNum = -1
    layerName = ""
    parenCount = 0
    for lineNum, line in enumerate(pcbLines):
        line = line.strip()
        if not inCopperLayer:
            if line.startswith("Layer"):
                args = line[line.find("(")+1:line.find(")")].split(" ")
                if args[2] == '"copper"':
                    inCopperLayer = True
                    tracesSelected = 0
                    layerNum = args[0]
                    layerName = args[1][1:-1]
        else: #in copper layer section
            if line == "(":
                parenCount += 1
            elif line.startswith("Line"):
                args = line[line.find('[')+1:line.find(']')].split(' ')
                angle = GetTraceAngle(args)
                if not angle in [0.0, 45.0, 90.0, 135.0, 180.0, -135.0, -90.0, -45.0]:
                    flags = args[6][1:-1].split(",")
                    if len(flags) == 1 and not flags[0]: flags = []
                    if not "selected" in flags:
                        flags.append("selected")
                        pcbLines[lineNum] = '\tLine[%s "%s"]\n' % (" ".join(args[0:6]), ",".join(flags))
                        if G.VerboseMode:
                            print("Selecting %05d %s A=%0.4f" % (lineNum, line, angle))
                        tracesSelected += 1
            elif line == ")":
                parenCount -= 1
                if parenCount == 0:
                    print("%d lines selected in layer %s (%s)" % (tracesSelected, layerNum, layerName))
                    totalTracesSelected += tracesSelected
                    inCopperLayer = False
    if totalTracesSelected > 0:
        with open(pName+".pcb", 'w') as pcbFile:
            pcbFile.writelines(pcbLines)
    print("%d total lines selected." % totalTracesSelected)

def PcbCoordToMm(coord):
    coord = coord.strip().lower()
    if coord.endswith('mm'): return float(coord[:-2])
    if coord.endswith('mil'): return float(coord[:-3]) * 0.001 * 25.4
    else: return float(coord) * 1e-5 * 25.4

def ValidateRefDes(refs):
    for ref in refs:
        ltrPart = True
        for i in range(len(ref)):
            if ref[i] >= 'A' and ref[i] <= 'Z':
                if ltrPart:
                    if i > 4: raise Exception('Invalid RefDes "%s": too many letters.' % ref)
                else: raise Exception('Invalid RefDes "%s": letter follows number.' % ref)
            elif ref[i].isnumeric():
                if ltrPart:
                    if i == 0: raise Exception('Invalid RefDes "%s": no leading letter.' % ref)
                    else: ltrPart = False
            else: raise Exception('Invalid RefDes "%s": bad character.' % ref)

def MovePartsOnLayout(pName, parts, coords, pgs=-1, dryRun=False):
    if parts == 'boxes':
        if pgs == -1: raise Exception("Missing pages argument for MovePartsOnLayout.")
        DirSet.Schematic()
        refDes = []
        for page in range(1,pgs+1):
            fName = SchPgName(page, pgs, pName)
            sch = schparse.Schematic()
            sch.FromFile(fName)
            refs = []
            #find bounding boxes
            boxes = []
            for item in sch.Items:
                if not isinstance(item, schparse.Box): continue
                if item.FillType == schparse.eFillType.HATCH: boxes.append(item)
            for item in sch.Items:
                if not isinstance(item, schparse.Component): continue
                if not item.GetAttrib(G.FootprintAttrib): continue #don't mess with parts that have no footprint
                ref = item.RefDes
                if not ref: continue
                inABox = False
                for box in boxes:
                    inABox = inABox or box.IsCoordWithinFigure(item.X, item.Y)
                if inABox:
                    refs.append(ref)
            if len(refs) > 0:
                print("Found %d boxed parts on page %d." % (len(refs), page))
                refDes.extend(refs)
    elif parts.endswith('.sch') and parts.find(',') == -1:
        print('Moving parts on grouping schematic "%s" to new coordinates...' % parts)
        DirSet.Schematic()
        groupSch = schparse.Schematic()
        groupSch.FromFile(parts)
        refDes = []
        for part in groupSch.Items:
            if isinstance(part, schparse.Component):
                ref = part.RefDes
                if ref: refDes.append(ref)
    else:
        print("Moving referenced parts to new coordinates...")
        refDes = parts.strip().split(',')
    if len(refDes) == 0: raise Exception("No parts designated to be moved.")
    ValidateRefDes(refDes)
    #find duplicates
    refs = refDes.copy()
    refs.sort()
    for i in range(len(refs)-1):
        if refs[i] == refs[i+1]:
            print('Warning: RefDes "%s" is duplicated in the list.' % refs[i])
            refDes.remove(refs[i])
    coords = coords.strip().split(',')
    try:
        X = "%0.4fmm" % PcbCoordToMm(coords[0])
        Y = "%0.4fmm" % PcbCoordToMm(coords[1])
    except Exception:
        raise Exception('Invalid X,Y coordinate entered.')
    print("References: %s" % (", ".join(refDes)))
    print("New coordinates: (%s, %s)" % (X, Y))
    if dryRun:
        print("Dry run, no parts moved.")
        return
    DirSet.Layout()
    with open(pName+".pcb", 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    movedCount = 0
    for lineNum, line in enumerate(pcbLines):
        line = line.strip()
        if not line.startswith("Element"): continue
        args = line[line.find("[")+1:line.find("]")].split(" ")
        ref = args[2][1:-1] #trim off quote marks
        if ref in refDes:
            args[4] = X
            args[5] = Y
            if line.endswith("("): paren = "("
            else: paren = ""
            line = "Element[%s]%s\n" % (" ".join(args), paren)
            pcbLines[lineNum] = line
            print("%s moved." % ref)
            refDes.remove(ref)
            movedCount += 1
    if movedCount > 0:
        with open(pName+".pcb", 'w') as pcbFile:
            pcbFile.writelines(pcbLines)        
    if len(refDes) > 0: print("Warning: Some references were not found - %s" % (", ".join(refDes)))
    print("%d parts moved." % movedCount)

def AnnotateSchematic(pgs, pName, pJump, force=False):
    if force: print("Re-annotating schematic...")
    else: print("Annotating schematic...")
    DirSet.Schematic()
    cmd = "refdes_renum "
    if pJump > 0:
        # Check for minimum page-jump here
        cmd += "--pgskip %d " % pJump
    if force: cmd += "--force "
    cmd += SchPgName(-1, pgs, pName)
    if G.VerboseMode: print("Command:  %s" % cmd)
    exitCode = os.system(cmd)
    codeStrings = ["Success", "Error opening or reading input file", "Error opening or writing output file",
                   "Too many components for page-jump value", "Internal error (program bug encountered)"]
    print("ExitCode = %s" % codeStrings[exitCode])

def GetPartByRefDes(pgs, pName, refDes):
    DirSet.Schematic()
    matches = []
    for page in range(pgs):
        fName = SchPgName(page+1, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        for item in sch.Items:
            if not isinstance(item, schparse.Component): continue
            if item.GetAttrib(G.RefDesAttrib) == refDes: matches.append(item)
    return matches

def OpenFootprintByRefDes(pgs, pName, refDes):
    parts = GetPartByRefDes(pgs, pName, refDes)
    if len(parts) < 1: raise Exception('No part with reference "%s" was found.' % refDes)
    if len(parts) > 1:
        slots = set()
        for part in parts:
            slot = part.GetAttrib(G.SlotAttrib)
            if slot:
                if not slot.isnumeric(): raise Exception("Part with non-numeric slot number found.")
                slots.add(int(slot))      
        if not {1}.issubset(slots): print("Warning: Slotted part has no slot 1.")
        if len(slots) != len(parts):
            raise Exception('More than one part with reference "%s" exists.' % refDes)
    footprint = parts[0].GetAttrib(G.FootprintAttrib)
    for part in parts:
        if part.GetAttrib(G.FootprintAttrib) != footprint:
            raise Exception("Slotted part has non-uniform footprints.")
    print('Opening footprint "%s" in pcb...' % footprint)
    cmd = "pcb %s%s%s &" % (G.ElemDir, os.sep, footprint)
    if G.VerboseMode: print("Command:  %s" % cmd)
    os.system(cmd)

def DispPartInfo(part, prefix):
    if G.VerboseMode:
        print("%sBaseName = %s" % (prefix,part.Basename))
    attribs = part.GetAttribs()        
    for attrib in attribs:
        print('%s%s = %s' % (prefix, attrib, attribs[attrib]))

def FindSchematicPart(pgs, pName, refDes):
    #title block geometry--this should not be hard-coded!
    tbBorder = 300
    tbXDiv = 8070
    tbYDiv = 6300
    print("Searching for %s in schematic..." % refDes)
    DirSet.Schematic()
    foundIt = False
    for page in range(pgs):
        results = []
        cornerX = 10000000000000000
        cornerY = 10000000000000000
        fName = SchPgName(page+1, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        for item in sch.Items:
            if not isinstance(item, schparse.Component): continue
            ref = item.GetAttrib(G.RefDesAttrib)
            if ref == refDes: results.append(item)
            cornerX = min(cornerX, item.X)
            cornerY = min(cornerY, item.Y)
        for r in results:
            x = (r.X-cornerX-tbBorder) // tbXDiv + 1
            y = (r.Y-cornerY-tbBorder) // tbYDiv + ord('A')
            print("Found %s on page %d at %s%d." % (refDes, page+1, chr(y), x))
            DispPartInfo(r, '   ')
            foundIt = True
    if not foundIt: print("Part not found.")
    
def FindSchematicPartByAttr(pgs, pName, attr):
    DirSet.Schematic()
    foundCount = 0
    for page in range(pgs):
        fName = SchPgName(page+1, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        parts = sch.GetComponentsByAttrib('*', attr)
        for part in parts:
            print("Found %s on page %d:" % (part.GetAttrib(G.RefDesAttrib), page+1))
            DispPartInfo(part, '   ')
            foundCount += 1
    if foundCount == 0: print("No matching parts found.")
    elif foundCount == 1: print("Found 1 matching part.")
    else: print("Found %d matching parts." % foundCount)
        

def SumCurrents(pgs, pName, pwrNet):
    print("Summing currents on net %s..." % pwrNet)
    DirSet.Schematic()
    total = 0
    for page in range(1,pgs+1):
        pgTotal = 0
        fName = SchPgName(page, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        for item in sch.Items:
            if not isinstance(item, schparse.Component): continue
            net = item.GetAttrib(G.NetAttrib)
            if not net: continue
            if net.find(":") == -1:
                print('Warning: Malformed net attribute %s on page %d.' % (net, page))
                continue
            current = item.GetAttrib(G.CurrentAttrib)
            if not current: continue
            if net.startswith(pwrNet):
                try:
                    current = float(current)
                except:
                    print('Warning: Invalid current number format "%s" on page %d' % (current, page))
                    continue
                pgTotal += current
        print("  Page %d total: %0.3fmA" % (page, pgTotal))
        total += pgTotal
    print("Total current draw on %s rail is %0.3fmA" % (pwrNet, total))

def SetSchematicAttributes(pgs, pName, attr, newVal, refList):
    refList = refList.strip().split(',')
    print("Setting %s attribute to %s for parts %s" % (attr, newVal, ", ".join(refList)))
    DirSet.Schematic()
    changeCount = 0
    for page in range(1,pgs+1):
        fName = SchPgName(page, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        changed = False
        print("Processing page %d..." % page)
        for item in sch.Items:
            if not isinstance(item, schparse.Component): continue
            ref = item.RefDes
            if ref in refList:
                if item.GetAttrib(attr):
                    print("   %s attribute set." % ref)
                else:
                    print("   %s attribute added." % ref)
                item.SetAttrib(attr, newVal, createIfMissing=True)
                changeCount += 1
                changed = True
        if changed: sch.ToFile(fName)
    print("%d part%s changed." % (changeCount, AddS(changeCount)))

def SetSchematicVendorInfo(pgs, pName, vendor, partNum, refList):
    SetSchematicAttributes(pgs, pName, G.VendorAttrib, vendor, refList)
    SetSchematicAttributes(pgs, pName, G.PNumAttrib, partNum, refList)

def SetSchematicSymbol(pgs, pName, symbol, refList):
    refList = refList.strip().split(',')
    symbol += ".sym"
    print("Setting symbol to %s for part%s %s" % (symbol, AddS(len(refList)), ", ".join(refList)))
    DirSet.Schematic()
    changeCount = 0
    warningCount = 0
    for page in range(1,pgs+1):
        fName = SchPgName(page, pgs, pName)
        sch = schparse.Schematic()
        sch.FromFile(fName)
        changed = False
        print("Processing page %d..." % page)
        for item in sch.Items:
            if not isinstance(item, schparse.Component): continue
            ref = item.GetAttrib(G.RefDesAttrib)
            if ref in refList:
                if item.Embedded:
                    print("W: Component %s is embedded, can't set symbol (yet)." % ref)
                    warningCount += 1
                    continue
                item.Basename = symbol
                changeCount += 1
                changed = True
                print("   %s symbol changed to %s." % (ref, symbol))
        if changed: sch.ToFile(fName)
    print("%d part%s changed." % (changeCount, AddS(changeCount)))
    print("%d warning%s." % (warningCount, AddS(warningCount)))
    

def IsAngleInArc(ang, startAng, endAng):
    if endAng < startAng:
        if startAng > ang:
            startAng -= 360
        else:
            endAng += 360
    return startAng < ang and endAng > ang        
    
def ArcBoundingBox(radius, startAng, endAng, x, y):
    if IsAngleInArc(0, startAng, endAng):
        cosine = 1
    else:
        cosine = math.cos(math.radians(startAng))
        cosine = max(cosine, math.cos(math.radians(endAng)))
    minX = x - radius * cosine
    
    if IsAngleInArc(180, startAng, endAng):
        cosine = -1
    else:
        cosine = math.cos(math.radians(startAng))
        cosine = min(cosine, math.cos(math.radians(endAng)))
    maxX = x - radius * cosine
    
    if IsAngleInArc(90, startAng, endAng):
        sine = 1
    else:
        sine = math.sin(math.radians(startAng))
        sine = max(sine, math.sin(math.radians(endAng)))
    maxY = y + radius * sine
    
    if IsAngleInArc(270, startAng, endAng):
        sine = -1
    else:
        sine = math.sin(math.radians(startAng))
        sine = min(sine, math.sin(math.radians(endAng)))
    minY = y + radius * sine
    
    return minX, maxX, minY, maxY

def GetBoardDims(pName, printResult=True):
    DirSet.Layout()
    with open(pName+".pcb", 'r') as pcbFile:
        pcbLines = pcbFile.readlines()
    lineNum = 0
    for line in pcbLines:
        line = line.strip()
        if line.lower().startswith('pcb'):
            line = line[line.find('[')+1:line.find(']')]
            inquote = False
            args = []
            idx = 0
            for i, ch in enumerate(line):
                if ch == '"': inquote = not inquote
                elif not inquote and ch == ' ':
                    args.append(line[idx:i])
                    idx = i + 1
            args.append(line[idx:])
            layoutName, width, height = args
            layoutWidth = PcbCoordToMm(width)
            layoutHeight = PcbCoordToMm(height)
            print("Layout workspace dimensions: %s by %s" % (width, height))
        if line.lower().startswith('layer('):
            lNum, lName, lType = line[line.find('(')+1:line.find(')')].split(' ')
            lName = lName[1:-1].lower()
            lType = lType[1:-1].lower()
            if lName == 'outline' and lType == 'outline':
                if G.VerboseMode: print('Outline layer def starts at line %d, "%s"' % (lineNum+1,line))
                print('Using layer %s for outline information...' % lNum)
                break
        lineNum += 1
    minX = 1e10
    minY = 1e10
    maxX = 0
    maxY = 0
    foundLines = False
    lineNum += 1
    while True:
        line = pcbLines[lineNum].strip()
        if line.endswith(')'): break
        if line.lower().startswith('line'):
            x1, y1, x2, y2, thickness, clr, flags = line[line.find('[')+1:line.find(']')].split(' ')
            try:
                minX = min(minX, PcbCoordToMm(x1))
                minX = min(minX, PcbCoordToMm(x2))
                maxX = max(maxX, PcbCoordToMm(x1))
                maxX = max(maxX, PcbCoordToMm(x2))
                minY = min(minY, PcbCoordToMm(y1))
                minY = min(minY, PcbCoordToMm(y2))
                maxY = max(maxY, PcbCoordToMm(y1))
                maxY = max(maxY, PcbCoordToMm(y2))
            except:
                raise Exception("Parser could not handle PCB file line %d." % (lineNum + 1))
            foundLines = True
        elif line.lower().startswith('arc'):
            x, y, width, height, thickness, clearance, startAng, deltaAng, flags = line[line.find('[')+1:line.find(']')].split(' ')
            try:
                x = PcbCoordToMm(x)
                y = PcbCoordToMm(y)
                radius = PcbCoordToMm(width)
                startAng = float(startAng)
                endAng = startAng + float(deltaAng)
            except:
                raise Exception("Parser could not handle PCB file line %d." % (lineNum + 1))                
            mnX, mxX, mnY, mxY = ArcBoundingBox(radius, startAng, endAng, x, y)
            minX = min(minX, mnX)
            maxX = max(maxX, mxX)
            minY = min(minY, mnY)
            maxY = max(maxY, mxY)
            foundLines = True
        lineNum += 1
    if not foundLines: print("No bounding entities (lines/arcs) found in outline layer!")
    else:
        width = maxX-minX
        height = maxY-minY
        if printResult:
            print("Board width: %0.2fmm (%0.3fin)" % (width, width * 0.03937007874))
            print("Board height: %0.2fmm (%0.3fin)" % (height, height * 0.03937007874))
        return width, height, layoutWidth, layoutHeight

def ZipGerbers(pName):
    DirSet.Layout()
    gPath = "./%s" % G.GerbDir
    if not os.path.isdir(gPath): raise Exception("Cannot find Gerber folder to zip.")
    lst = os.listdir(gPath)
    gbrFileCount = 0
    for f in lst:
        if not f.startswith(pName): continue
        if f[-3:] in ['gbr', 'cnc']: gbrFileCount += 1
    if gbrFileCount < 3:
        if gbrFileCount > 1: plurl = 's'
        else: plurl = ''
        if gbrFileCount == 0: raise Exception("No Gerber files found in Gerber folder.")
        else: print("Warning, only %d Gerber file%s found.  Did you forget to generate them?" % (gbrFileCount, plurl))
    zipFileName = "%s_Gerber.zip" % pName
    print("Zipping Gerber folder as %s..." % zipFileName)
    if os.path.exists(zipFileName): os.remove(zipFileName)
    os.system("zip -q %s %s/*" % (zipFileName, G.GerbDir))


def DisplayHelpText():
    print("")
    print("Usage: geda.py switch1 switch2")
    print("")
    print("Available switches:")
    print("  v      Run in verbose mode (must be first arg)")
    print("  imode  Run in interactive mode")
    print("  exit   Exit interactive mode")
    print("  vers   Display script version")
    print("Schematic")
    print("  es     Edit schematic")
    print("  spdf   Generate schematic PDF")
    print("  bom    Generate bill of materials")
    print("  attr   Edit schematic in gattrib")
    print("  drc    Run design rule checker on schematic")
    print("  opc    Check off-page connectors")
    print("  cf     Check footprint attributes against element database")
    print("  os n   Open schematic page n file in Eclipse")
    print("  ob     Open BoM in Gnumeric")
    print("  eb     Edit BoM in Libre Office (opens both .tsv and .xls)")
    print("  hs     Open RevisionHist for schematic in Eclipse")
    print("  gsr    Get schematic revision number")
    print("  ssr    Set schematic revision number")
    print("  tblk   Set text in title block (file, page numbers)")
    print("  ano n  Annotate schematic with page-jump n (set n to 0 for no page-jump)")
    print("  fp r   Find parts on schematic with reference designator r")
    print("  fpa a  Find parts on schematic with attribute a")
    print("  ofp r  Open footprint file in PCB for schematic part with ref r")
    print("  scur p Display sum of currents for power rail p")
    print("  sa a v r Set attribute a to value v for all parts with ref in list r")
    print("  sv v p r Set vendor name to v, vendor part to p for all part in ref list r")
    print("  cs s r Change part base symbol for parts with ref in list r to s (omit .sym)")
    print("Layout")
    print("  el     Edit layout")
    print("  lpdf   Generate layout PDF")
    print("  xy     Generate layout XY file")
    print("  png    Generate layout PNG images")
    print("  gerb   Generate Gerber files")
    print("  notes  Merge Gerber notes layer into fab layer")
    print("  gv     Open Gerber files in gerbv")
    print("  ol     Open layout PCB file in Eclipse")
    print("  hl     Open RevisionHist for layout in Eclipse")
    print("  sts n s Set text scale to n (integer %) for scope s (selected or all)")
    print("  sstw w Set selected trace width to w (width with units e.g. 0.2mm or 8mil")
    print("  rdt    Remove duplicate traces (lines/arcs) in copper layers")
    print("  soat   Select odd-angled traces (not multiples of 45deg)")
    print("  mp p c [dryrun] Move parts p to coordinates c (mp R1,R2,C3 1.234,9.876)")
    print("  oxy    Open X-Y file in Eclipse")
    print("  dims   Get board dimensions (bounding rectangle)")
    print("  zg     Zip up Gerber folder")
    print("General")
    print("  sl     Export schematic to layout")
    print("  omp    Open MfgPackages.txt in Eclipse")

def ProcessSwitches(projName, schPages, args, interactiveMode):
    i = 1
    
    if len(args) <= 1:
        if not interactiveMode:
            DisplayHelpText()
            raise Exception("")
        
    while i < len(args):
        print("")
        if args[i] == 'h' or args[i] == 'help':
            DisplayHelpText()
            i += 1
        elif args[i] == 'v':
            if G.VerboseMode:
                G.VerboseMode = False
                print("Verbose mode disabled.")
            else:
                G.VerboseMode = True
                print("Verbose mode enabled.")
            i += 1
        elif args[i] == 'imode':
            interactiveMode = True
            print("Interactive mode enabled.")
            print("geda.py version %s" % __version__)
            i += 1
        elif args[i] == 'exit':
            interactiveMode = False
            i += 1
        elif args[i] == 'vers':
            print("geda.py version %s" % __version__)
            i += 1
        elif args[i] == 'es':
            EditSchem(schPages, projName)
            if interactiveMode: time.sleep(0.2)
            i += 1
        elif args[i] == 'spdf':
            GenSchPDF(schPages, projName)
            i += 1
        elif args[i] == 'bom':
            CreateBoM(schPages, projName)
            i += 1
        elif args[i] == 'attr':
            EditAttribs(schPages, projName)
            i += 1
        elif args[i] == 'drc':
            RunDRC(schPages, projName)
            i += 1
        elif args[i] == 'opc':
            CheckOffpageConnectors(schPages, projName)
            i += 1
        elif args[i] == 'cf':
            FindFootprints(schPages, projName)
            i += 1
        elif args[i] == 'os':
            if len(args) < i+2: raise Exception('"os" switch must be followed by a page number.')
            page = args[i+1]
            if not page.isdigit(): raise Exception('Expecting schematic page number, got "%s".' % page)
            page = int(page)
            if not page in range(1, schPages+1): raise Exception('Schematic has no page %d.' % page)
            DirSet.Schematic()
            print("Opening schematic page %d in Eclipse..." % page)
            if schPages == 1: os.system("ecl %s.sch" % projName)
            else: os.system("ecl %s_p%d.sch" % (projName, page))
            i += 2
        elif args[i] == 'ob':
            DirSet.Schematic()
            fn = "%s BOM.xls" % projName
            print('Opening file "%s" in Gnumeric...' % fn)
            os.system('gnumeric "%s" &' % fn)
            i += 1
        elif args[i] == 'eb':
            DirSet.Schematic()
            print('Opening "bom.tsv" in Libre Office...')
            os.system('open bom.tsv -a LibreOffice')
            fn = "%s BOM.xls" % projName
            print('Opening file "%s" in Libre Office...' % fn)
            os.system('open "%s" -a LibreOffice' % fn)
            i += 1
        elif args[i] == 'hs':
            DirSet.Schematic()
            print("Opening schematic revision history in Eclipse...")
            os.system("ecl RevisionHist.txt")
            i += 1
        elif args[i] == 'gsr':
            mismatch, revs = GetSchRevs(schPages, projName)
            if mismatch:
                print("Inconsistent revision numbers across schematic pages:")
                for pg in range(schPages):
                    print("  Page %d revision is %s" % (pg+1, revs[pg]))
            else: print("Schematic revision: %s" % revs[0])
            i += 1
        elif args[i] == 'ssr':
            if len(args) < i+2: raise Exception('"ssr" switch must be followed by a revision number.')
            newRev = args[i+1]
            print("Setting schematic revision to %s..." % newRev)
            for pg in range(schPages):
                SetSchPageRev(pg+1, schPages, projName, newRev)
            i += 2
        elif args[i] == 'tblk':
            print("Fixing schematic title block text...")
            for pg in range(schPages):
                FixTitleBlock(pg+1, schPages, projName)
            i += 1
        elif args[i] == 'ano':
            if len(args) < i+2: raise Exception('"ano" switch must be followed by a page-jump value.')
            pageJump = args[i+1]
            if not pageJump.isdigit(): raise Exception('Expecting  page-jump value, got "%s".' % pageJump)
            pageJump = int(pageJump)
            AnnotateSchematic(schPages, projName, pageJump)
            i += 2
        elif args[i] == 'fp':
            if len(args) < i+2: raise Exception('"fp" switch must be followed by a reference designator.')
            ref = args[i+1]
            ValidateRefDes([ref])
            FindSchematicPart(schPages,projName, ref)
            i += 2
        elif args[i] == 'fpa':
            if len(args) < i+2: raise Exception('"fpa" switch must be followed by an attribute value.')
            attr = args[i+1]
            if not attr.endswith(':1'): attr = attr.replace(':',' ')
            FindSchematicPartByAttr(schPages,projName, attr)
            i += 2
        elif args[i] == 'ofp':
            if len(args) < i+2: raise Exception('"ofp" switch must be followed by a reference designator.')
            ref = args[i+1]
            ValidateRefDes([ref])
            OpenFootprintByRefDes(schPages, projName, ref)
            i += 2
        elif args[i] == 'scur':
            if len(args) < i+2: raise Exception('"scur" switch must be followed by a net name.')
            net = args[i+1]
            SumCurrents(schPages, projName, net)
            i += 2
        elif args[i] == 'sa':
            if len(args) < i+4: raise Exception('"sa" switch must be followed by attr val ref-list.')
            attr = args[i+1].replace(':', ' ') #use colons for spaces because spaces mess up arg parsing and colons are illegal in attributes
            newVal = args[i+2].replace(':', ' ')
            refList = args[i+3]
            SetSchematicAttributes(schPages, projName, attr, newVal, refList)
            i += 4
        elif args[i] == 'sv':
            if len(args) < i+4: raise Exception('"sv" switch must be followed by vendor partnum ref-list.')
            vendor = args[i+1].replace(':', ' ') #use colons for spaces because spaces mess up arg parsing and colons are illegal in attributes
            partNum = args[i+2].replace(':', ' ')
            refList = args[i+3]
            SetSchematicVendorInfo(schPages, projName, vendor, partNum, refList)
            i += 4
        elif args[i] == 'ss':
            if len(args) < i+3: raise Exception('"ss" switch must be followed by symbol ref-list.')
            newSym = args[i+1]
            refList = args[i+2]
            SetSchematicSymbol(schPages, projName, newSym, refList)
            i += 3

        elif args[i] == 'el':
            EditLayout(projName)
            if interactiveMode: time.sleep(0.3)
            i += 1
        elif args[i] == 'lpdf':
            GenLayoutPDF(projName)
            i += 1
        elif args[i] == 'xy':
            GenXYFile(projName)
            i += 1
        elif args[i] == 'png':
            if len(args) > i+1 and args[i+1].isdigit():
                GenLayoutPNG(projName, int(args[i+1]))
                i += 1
            else:
                GenLayoutPNG(projName)
            i += 1
        elif args[i] == 'gerb':
            GenGerbers(projName)
            i += 1
        elif args[i] == 'notes':
            MergeNotes(projName)
            i += 1
        elif args[i] == 'gv':
            ViewGerber()
            i += 1
        elif args[i] == 'ol':
            DirSet.Layout()
            print("Opening PCB layout file in Eclipse...")
            os.system("ecl %s.pcb" % projName)
            i += 1
        elif args[i] == 'hl':
            DirSet.Layout()
            print("Opening layout revision history in Eclipse...")
            os.system("ecl RevisionHist.txt")
            i += 1
        elif args[i] == 'sts':
            if len(args) < i+3: raise Exception('"sts" switch must be followed by a text scale percentage (integer) and a scope ("selected" or "all").')
            tScale = args[i+1]
            scope = args[i+2]
            if not tScale.isdigit(): raise Exception('Text scale must be an integer.')
            if not scope in ['selected','all']: raise Exception('Scope must be "selected" or "all".')
            print("Setting text scale of %s elements to %s..." % (scope, tScale))
            numChanged = SetTextScale(projName, tScale, scope)
            print("Changed text scale of %d element%s." % (numChanged, AddS(numChanged)))
            i += 3
        elif args[i] == 'sstw':
            if len(args) < i+2: raise Exception('"sstw" switch must be followed by a trace width string (such as "5mil" or "0.18mm").')
            tWidth = args[i+1]
            try:
                PcbCoordToMm(tWidth)
            except:
                raise Exception('Trace width must be a valid PCB dimension.')
            print("Setting width of selected traces (lines) to %s..." % tWidth)
            numChanged = SetSelectedTraceWidth(projName, tWidth)
            print("Changed width of %d trace%s." % (numChanged, AddS(numChanged)))
            i += 2
        elif args[i] == 'rdt':
            RemoveDuplicateTraces(projName)
            i += 1
        elif args[i] == 'soat':
            SelectOddAngledTraces(projName)
            i += 1
        elif args[i] == 'mp':
            if len(args) < i+3: raise Exception('"mp" switch must be followed by a RefDes list and coordinates.')
            if len(args) > i+3 and args[i+3].lower() == 'dryrun': dryRun = True
            else: dryRun = False
            MovePartsOnLayout(projName, args[i+1], args[i+2], pgs=schPages, dryRun=dryRun)
            i += 3
            if dryRun: i += 1
        elif args[i] == 'oxy':
            DirSet.Layout()
            print("Opening X-Y file in Eclipse...")
            os.system("ecl %s-XY.txt" % projName)
            i += 1
        elif args[i] == 'dims':
            GetBoardDims(projName)
            i += 1
        elif args[i] == 'zg':
            ZipGerbers(projName)
            i += 1
        elif args[i] == 'sl':
            G2P(schPages, projName)
            i += 1
        elif args[i] == 'omp':
            DirSet.TopLevel()
            print("Opening manufacturing packages file in Eclipse...")
            os.system("ecl MfgPackages.txt")
            i += 1
        else:
            raise Exception('Unknown argument "%s" encountered.' % (args[i]))
    return interactiveMode
    
try:
    DirSet.FindPaths()
    DirSet.TopLevel()
    if not os.path.isfile("project"): raise Exception("Project config file not found.")
    with open('project','r') as projFile:
        projLines = projFile.readlines()
    projName = projLines[0].strip()
    schPages = int(projLines[1].strip())

    args = sys.argv
    interactiveMode = False
    while True:
        try:
            interactiveMode = ProcessSwitches(projName, schPages, args, interactiveMode)
        except Exception as E:
            if interactiveMode:
                print("Error:  %s\n" % E)
                if G.VerboseMode: traceback.print_tb(sys.exc_info()[-1], 50)
            else: raise
        if interactiveMode:
            cmd = "junk " + input('\n%s> ' % projName) #"junk" here replaces arg[0], which is the command that precedes the switches
            args = cmd.strip().split()
        else: break
    
    raise Exception("")
        
except Exception as E:
    if not E.__str__(): print("\nDone!\n")
    else:
        print("Error:  %s\n" % E)
        if G.VerboseMode: traceback.print_tb(sys.exc_info()[-1], 50)
