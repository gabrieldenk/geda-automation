#!/usr/local/bin/python3
##!/usr/bin/python

#For details on schem file format, see http://wiki.geda-project.org/geda:file_format_spec

from enum import IntEnum
import math

class MyEnum(IntEnum):
    def __str__(self):
        return str(int(self))
    @classmethod
    def New(cls, val):
        if type(val)==str: val = int(val)
        return cls(val)

class eCapStyle(MyEnum):
    NONE = 0
    SQUARE = 1
    ROUND = 2

class eDashStyle(MyEnum):
    SOLID = 0
    DOTTED = 1
    DASHED = 2
    CENTER = 3
    PHANTOM = 4
    
class eFillType(MyEnum):
    HOLLOW = 0
    FILL = 1
    MESH = 2
    HATCH = 3
    VOID = 4

class ePinType(MyEnum):
    NORMAL = 0
    BUS = 1

class eShowNameVal(MyEnum):
    Both = 0
    Value = 1
    Name = 2
    
class eColor(MyEnum):
    BACKGROUND_COLOR = 0
    PIN = 1
    NET_ENDPOINT = 2
    GRAPHIC = 3
    NET = 4
    ATTRIBUTE = 5
    LOGIC_BUBBLE = 6
    DOTS_GRID = 7
    DETACHED_ATTRIBUTE = 8
    TEXT = 9
    BUS = 10
    SELECT = 11
    BOUNDINGBOX = 12
    ZOOM_BOX = 13
    STROKE = 14
    LOCK = 15
    OUTPUT_BACKGROUND = 16
    FREESTYLE1 = 17
    FREESTYLE2 = 18
    FREESTYLE3 = 19
    FREESTYLE4 = 20
    JUNCTION = 21
    MESH_GRID_MAJOR = 22
    MESH_GRID_MINOR = 23
    
class eAlignment(MyEnum):
    LowerLeft = 0
    CenterLeft = 1
    UpperLeft = 2
    LowerCenter = 3
    CenterCenter = 4
    UpperCenter = 5
    LowerRight = 6
    CenterRight = 7
    UpperRight = 8

def SubList(inpList, indicies):
    result = []
    for idx in indicies:
        result.append(inpList[idx])
    return result

class Item(object):
    'BaseItem'
    Code = '-'
    FieldTypes = [str]
    
    _Code = 0 #position of code argument in all item lines
    
    @classmethod    
    def IsItem(cls, hdrLine):
        return hdrLine.startswith(cls.Code + ' ')
        
    def __init__(self):
        self.Fields = []
    
    def FromFileSnippet(self, lines, idx):
        fields = lines[idx].strip().split(' ')
        if len(fields) != len(self.FieldTypes):
            raise Exception("Error: Wrong number of arguments for %s on line %d." % (self.Code,idx))
        if fields[0] != self.Code: raise Exception("Error: %s class invoked to parse non-%s item." % (self.__doc__,self.__doc__))
        try:
            for i in range(len(fields)):
                self.Fields.append(self.FieldTypes[i](fields[i]))
        except Exception as E:
            print(i)
            print(fields)
            print(self.FieldTypes)
            print(E)
            raise Exception("Error: Bad number conversion at line %d (%s)." % (idx,self.__doc__))
        idx += 1
        return idx
    
    def ToString(self):
        return "-BaseItem-"
    
    def ToFileSnippet(self):
        return ["%s\n" % " ".join(str(x) for x in self.Fields)]
    

class GschVersion(Item):
    'GschVersion'
    Code = 'v'
    FieldTypes = [str, int, int]
        
    Version = 1
    Fileformat_version = 2

    def ToString(self):
        return "Version: %s %s" % (self.Fields[self.Version], self.Fields[self.Fileformat_version])

    @property
    def X(self): return 0
    @X.setter
    def X(self, val): pass

    @property
    def Y(self): return 0
    @Y.setter
    def Y(self, val): pass


class LineBase(Item):
    'LineBase'
    Code = '-'

    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        if self.Fields[self._Dashstyle] in [eDashStyle.SOLID, eDashStyle.DOTTED] and self.Fields[self._Dashlength] != -1:
            raise Exception("Error: Dash length specified for solid or dotted line type at line %d." % idx)
        if self.Fields[self._Dashstyle] == eDashStyle.SOLID and self.Fields[self._Dashspace] != -1:
            raise Exception("Error: Dash space specified for solid line type at line %d." % idx)
        return idx

class OneCoordItems(object):
    _X = 1
    _Y = 2

    @property
    def X(self): return self.Fields[self._X]
    @X.setter
    def X(self, val): self.Fields[self._X] = val

    @property
    def Y(self): return self.Fields[self._Y]
    @Y.setter
    def Y(self, val): self.Fields[self._Y] = val

class TwoCoordItems(object):    
    _X1 = 1
    _Y1 = 2
    _X2 = 3
    _Y2 = 4

    @property
    def X1(self): return self.Fields[self._X1]
    @X1.setter
    def X1(self, val): self.Fields[self._X1] = val

    @property
    def Y1(self): return self.Fields[self._Y1]
    @Y1.setter
    def Y1(self, val): self.Fields[self._Y1] = val

    @property
    def X2(self): return self.Fields[self._X2]
    @X2.setter
    def X2(self, val): self.Fields[self._X2] = val

    @property
    def Y2(self): return self.Fields[self._Y2]
    @Y2.setter
    def Y2(self, val): self.Fields[self._Y21] = val

    @property
    def X(self): return (self.Fields[self._X1] + self.Fields[self._X2]) // 2
    @X.setter
    def X(self, val):
        diff = val - self.X
        self.Fields[self._X1] += diff
        self.Fields[self._X2] += diff

    @property
    def Y(self): return (self.Fields[self._Y1] + self.Fields[self._Y2]) // 2
    @Y.setter
    def Y(self, val):
        diff = val - self.Y
        self.Fields[self._Y1] += diff
        self.Fields[self._Y2] += diff

class Line(LineBase, TwoCoordItems):
    'Line'
    Code = 'L'
    #type x1 y1 x2 y2 color width capstyle dashstyle dashlength dashspace
    FieldTypes = [str]+[int]*4+[eColor.New, int, eCapStyle.New, eDashStyle.New, int, int]
    
    _Color = 5
    _LWidth = 6
    _Capstyle = 7
    _Dashstyle = 8
    _Dashlength = 9
    _Dashspace = 10
    
    def ToString(self):
        x1, y1, x2, y2, color, style = SubList(self.Fields, [self._X1, self._Y1, self._X2, self._Y2, self._Color, self._Dashstyle])
        return "Line: (%d,%d) to (%d,%d) color=%s, style=%s" % (x1,y1,x2,y2,color.name,style.name)

    
class Box(LineBase, OneCoordItems):
    'Box'
    Code = 'B'
    #type x y width height color width capstyle dashstyle dashlength dashspace filltype fillwidth angle1 pitch1 angle2 pitch2
    FieldTypes = [str]+[int]*4+[eColor.New,int,eCapStyle.New,eDashStyle.New,int,int,eFillType.New]+[int]*5
    
    _X = 1
    _Y = 2
    _Width = 3
    _Height = 4
    _LWidth = 5
    _Color = 6
    _Capstyle = 7
    _Dashstyle = 8
    _Dashlength = 9
    _Dashspace = 10
    _FillType = 11
    _FillWidth = 12
    _Angle1 = 13
    _Pitch1 = 14
    _Angle2 = 15
    _Pitch2 = 16

    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        simpleFill = self.Fields[self._FillType] in [eFillType.FILL, eFillType.HOLLOW, eFillType.VOID]
        paramsUsed = self.Fields[self._Angle1] != -1 or self.Fields[self._Angle2] != -1 or self.Fields[self._Pitch1] != -1 or self.Fields[self._Pitch2] != -1
        if simpleFill and paramsUsed:
            raise Exception("Error: Fill parameters given for un-hatched shape at line %d." % idx)
        return idx
    
    def ToString(self):
        x, y, w, h, color, fill = SubList(self.Fields, [self._X1, self._Y1, self._Width, self._Height, self._Color, self._FillType])
        return "Box: at (%d,%d), %dx%d, color=%s, fill=%s" % (x,y,w,h,color.name,fill.name)
    
    @property
    def Width(self):
        return self.Fields[self._Width]
    @Width.setter
    def Width(self, newWidth):
        self.Fields[self._Width] = newWidth

    @property
    def Height(self):
        return self.Fields[self._Height]
    @Height.setter
    def Height(self, newHeight):
        self.Fields[self._Height] = newHeight
        
    def IsCoordWithinFigure(self, x, y):
        return x >= self.X and x <= self.X+self.Width and y >= self.Y and y <= self.Y+self.Height
    
    @property
    def FillType(self): return self.Fields[self._FillType]
    
class Circle(LineBase, OneCoordItems):
    'Circle'
    Code = 'V'
    #type x y radius color width capstyle dashstyle dashlength dashspace filltype fillwidth angle1 pitch1 angle2 pitch2
    FieldTypes = [str,int,int,int,eColor.New,int,eCapStyle.New,eDashStyle.New,int,int,eFillType.New]+[int]*5

    _Radius = 3
    _Color = 4
    _LWidth = 5
    _Capstyle = 6
    _Dashstyle = 7
    _Dashlength = 8
    _Dashspace = 9
    _FillType = 10
    _FillWidth = 11
    _Angle1 = 12
    _Pitch1 = 13
    _Angle2 = 14
    _Pitch2 = 15
    
    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        simpleFill = self.Fields[self._FillType] in [eFillType.FILL, eFillType.HOLLOW, eFillType.VOID]
        paramsUsed = self.Fields[self._Angle1] != -1 or self.Fields[self._Angle2] != -1 or self.Fields[self._Pitch1] != -1 or self.Fields[self._Pitch2] != -1
        if simpleFill and paramsUsed:
            raise Exception("Error: Fill parameters given for un-hatched shape at line %d." % idx)
        return idx
    
    def ToString(self):
        x, y, rad, color, fill = SubList(self.Fields, [self.X, self.Y, self.Radius, self.Color, self.FillType])
        return "Circle: at (%d,%d), r=%d, color=%s, fill=%s" % (x,y,rad,color.name,fill.name)
    
    @property
    def Radius(self): return self.Fields[self._Radius]
    @Radius.setter
    def Radius(self, newRadius): self.Fields[self._Radius] = newRadius

    def IsCoordWithinFigure(self, x, y):
        return math.sqrt((x-self.X)**2 + (y-self.Y)**2) < self.Radius
    
class Arc(LineBase, OneCoordItems):
    'Arc'
    Code = 'A'
    #type x y radius startangle sweepangle color width capstyle dashstyle dashlength dashspace
    FieldTypes = [str]+[int]*5+[eColor.New,int,eCapStyle.New,eDashStyle.New,int,int]
    
    _Radius = 3
    _StartAngle = 4
    _SweepAngle = 5
    _Color = 6
    _LWidth = 7
    _Capstyle = 8
    _Dashstyle = 9
    _Dashlength = 10
    _Dashspace = 11
    
    def ToString(self):
        x, y, rad, strt, sweep, color = SubList(self.Fields, [self._X, self._Y, self._Radius, self._StartAngle, self._SweepAngle, self._Color])
        return "Arc: at (%d,%d), r=%d, start at %ddeg and sweeping %ddeg, color=%s" % (x,y,rad,strt,sweep,color.name)

class Text(Item, OneCoordItems):
    'Text'
    Code = 'T'
    #type x y color size visibility show_name_value angle alignment num_lines
    FieldTypes = [str,int,int,eColor.New,int,int,eShowNameVal.New,int,eAlignment.New,int]
    
    _Color = 3
    _Size = 4
    _Visible = 5
    _ShowNameVal = 6
    _Angle = 7
    _Alignment = 8
    _NumLines = 9
        
    def __init__(self):
        super().__init__()
        self.IsVisible = False
        self.__Strings = []
        self.__IsAttrib = False
        self.__AttrName = ""
        self.__AttrValue = ""
        
    def FromParams(self, x=0, y=0, color=eColor.TEXT, visible=False, show=eShowNameVal.Name,
                   isAttrib=False, alignment=eAlignment.LowerLeft, attrName="", attrVal="",
                   lines=[], size=10, angle=0):
        if isAttrib:
            if len(lines) > 0: raise Exception("Error: Text item can be an attribute or normal text, not both.")
            if not attrName: raise Exception("Error: Attribute must be named")
        if not angle in [0, 90, 180, 270]: raise Exception("Error: Text item angle '%d' is invalid." % angle)
        self.Fields = list(range(len(self.FieldTypes)))
        self.Fields[self._Code] = self.Code
        self.Fields[self._X] = x
        self.Fields[self._Y] = y
        self.Fields[self._Color] = color
        self.Fields[self._Size] = size
        self.IsVisible = visible
        self.Fields[self._Visible] = int(visible)
        self.Fields[self._ShowNameVal] = show
        self.Fields[self._Angle] = angle
        self.Fields[self._Alignment] = alignment
        if isAttrib:
            self.Fields[self._NumLines] = 1
            self.__Strings = [""]
            self.__IsAttrib = True
            self.Name = attrName
            self.Value = attrVal
        else:
            self.__Strings = lines
            self.__IsAttrib = False
        return self
        
    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        if not self.Fields[self._Angle] in [0, 90, 180, 270]: raise Exception("Error: Invalid text angle at line %d." % idx-1)
        if not self.Fields[self._Visible] in [0,1]:
            raise Exception("Error: Invalid visibility boolean at line %d." % (idx-1))
        self.IsVisible = self.Fields[self._Visible] == 1
        for i in range(self.Fields[self._NumLines]):
            self.__Strings.append(lines[idx].strip())
            idx += 1
        equPos = self.__Strings[0].find('=')
        self.__IsAttrib = self.Fields[self._NumLines] == 1 and equPos != -1
        if self.__IsAttrib:
            self.__AttrName = self.__Strings[0][:equPos]
            self.__AttrValue = self.__Strings[0][equPos+1:]
        return idx
            
    def ToString(self):
        if self.IsVisible: viz = ""
        else: viz = "invisible"
        if self.Fields[self._NumLines] > 1: elipses = "..."
        else: elipses = ""
        st = 'Text: (%d, %d) %s "%s%s"' % (self.Fields[self._X], self.Fields[self._Y], viz, self.__Strings[0], elipses)
        return st
    
    def ToFileSnippet(self):
        result = super().ToFileSnippet()
        for s in self.__Strings:
            result.append("%s\n" % s)
        return result

    @property
    def Name(self):
        if self.__IsAttrib:
            return self.__AttrName
        else:
            return ""
    @Name.setter
    def Name(self, newName):
        if self.__IsAttrib:
            self.__AttrName = newName
            self.__Strings[0] = "%s=%s" % (self.__AttrName, self.__AttrValue)
        else:
            pass
        
    @property
    def Value(self):
        if self.__IsAttrib:
            return self.__AttrValue
        else:
            return self.__Strings
    @Value.setter
    def Value(self, newVal):
        if self.__IsAttrib:
            self.__AttrValue = newVal
            self.__Strings[0] = "%s=%s" % (self.__AttrName, self.__AttrValue)
        else:
            if type(newVal) == list:
                self.__Strings = newVal
            else:
                self.__Strings = [newVal]
                
    @property
    def IsAttrib(self):
        return self.__IsAttrib
    
    @property
    def Strings(self):
        return self.__Strings
    @Strings.setter
    def Strings(self, arg):
        if not self.__IsAttrib:
            if arg[0].find('=') != -1: raise Exception("Error: Cannot change text to attribute.")
            self.__Strings = arg
                

class Component(Item, OneCoordItems):
    'Component'
    Code = 'C'
    #type x y selectable angle mirror basename
    FieldTypes = [str,int,int,int,int,int,str]
    
    _Selectable = 3
    _Angle = 4
    _Mirrored = 5
    _Basename = 6
 
    def __init__(self):
        super().__init__()
        self.Embedded = False
        self.Attribs = []
        self.EmbeddedLines = []
        #self.EmbeddedSymbol = Schematic()
    
    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        embText = 'EMBEDDED'
        bname = self.Fields[self._Basename]
        if bname.startswith(embText):
            self.Embedded = True
            self.Fields[self._Basename] = bname[len(embText):]
        else:
            self.Embedded = False
            self.Fields[self._Basename] = bname
        #handle embedding (just skip over it for now)
        if self.Embedded:
            if lines[idx][0] != '[': raise Exception("Error: Missing component embedding at line %d." % idx)
            idx += 1
            while lines[idx][0] != ']':
                self.EmbeddedLines.append(lines[idx])
                idx += 1
            idx += 1
        #parse attribs
        if idx < len(lines) and lines[idx].startswith('{'):
            idx += 1
            while Text.IsItem(lines[idx]):
                attrib = Text()
                idx = attrib.FromFileSnippet(lines, idx)
                if not attrib.IsAttrib: raise Exception("Error: Encountered non-attribute text in component section at line %d." % idx)
                self.Attribs.append(attrib)
            if not lines[idx].startswith('}'): raise Exception("Error: Unexpected item found in component section at line %d." % idx)
            idx += 1
        return idx
    
    def ToString(self):
        if self.Embedded: emb = " (embedded)"
        else: emb = ""
        l = len(self.Attribs) 
        if l == 0: atrb = "no attributes"
        elif l == 1: atrb = "1 attribute" 
        else: atrb = "%d attributes" % l
        st = 'Component: (%d, %d) "%s"%s - %s' % (self.Fields[self._X], self.Fields[self._Y], self.Fields[self._Basename], emb, atrb)
        return st
    
    def GetAttrib(self, atrName):
        for t in self.Attribs:
            if t.IsAttrib:
                if t.Name == atrName:
                    return t.Value
        return ""
    
    def GetAttribs(self):
        result = {}
        for t in self.Attribs:
            if t.IsAttrib:
                result[t.Name] = t.Value
        return result
    
    def SetAttrib(self, atrName, atrVal, createIfMissing=False):
        for t in self.Attribs:
            if t.IsAttrib:
                if t.Name == atrName:
                    t.Value = atrVal
                    return
        if createIfMissing:
            attrib = Text()
            attrib.FromParams(x=self.Fields[self._X], y=self.Fields[self._Y], color=eColor.ATTRIBUTE, isAttrib=True,
                              attrName=atrName, attrVal=atrVal)
            self.Attribs.append(attrib)
    
    def ToFileSnippet(self):
        fields = self.Fields.copy()
        embText = 'EMBEDDED'
        if self.Embedded: fields[self._Basename] = embText + fields[self._Basename]
        result = ["%s\n" % " ".join(str(x) for x in fields)]
        if self.Embedded:
            result.append('[\n')
            result.extend(self.EmbeddedLines)
            result.append(']\n')
        if len(self.Attribs) > 0:
            result.append('{\n')
            for attr in self.Attribs:
                result.extend(attr.ToFileSnippet())
            result.append('}\n')
        return result

    @property
    def Basename(self):
        return self.Fields[self._Basename]
    @Basename.setter
    def Basename(self, newSymName):
        if newSymName.split('.')[-1] != 'sym': print("Warning, setting a base symbol name without standard .sym extension.")
        self.Fields[self._Basename] = newSymName
        
    @property
    def RefDes(self):
        return self.GetAttrib('refdes')
    @RefDes.setter
    def RefDes(self, newRef):
        self.SetAttrib('refdes', newRef, createIfMissing=False)

class Net(Item, TwoCoordItems):
    'Net'
    Code = 'N'
    #type x1 y1 x2 y2 color
    FieldTypes = [str] + [int]*4 + [eColor.New]
    
    _Color = 5

    def __init__(self):
        super().__init__()
        self.Attribs = []
        
    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        #parse attribs
        if idx < len(lines) and lines[idx].startswith('{'):
            idx += 1
            while Text.IsItem(lines[idx]):
                attrib = Text()
                idx = attrib.FromFileSnippet(lines, idx)
                if not attrib.IsAttrib: raise Exception("Error: Encountered non-attribute text in net section at line %d." % idx)
                self.Attribs.append(attrib)
            if not lines[idx].startswith('}'): raise Exception("Error: Unexpected item found in net section at line %d." % idx)
            idx += 1
        return idx

    def ToString(self):
        netName = self.GetAttrib('netname')
        if netName: net = " net=%s" % netName
        else: net = ""
        return "%s: from (%d,%d) to (%d,%d)%s" % (self.__doc__,self.Fields[self._X1], self.Fields[self._Y1], self.Fields[self._X2], self.Fields[self._Y2], net)
    
    def GetAttrib(self, atrName):
        for t in self.Attribs:
            if t.IsAttrib:
                if t.Name == atrName:
                    return t.Value
        return ""

    def GetAttribs(self):
        result = {}
        for t in self.Attribs:
            if t.IsAttrib:
                result[t.Name] = t.Value
        return result
    
    def ToFileSnippet(self):
        result = super().ToFileSnippet()
        if len(self.Attribs) > 0:
            result.append("{\n")
            for attr in self.Attribs:
                result.extend(attr.ToFileSnippet())
            result.append("}\n")
        return result

class Bus(Net):
    'Bus'
    Code = 'U'
    #type x1 y1 x2 y2 color ripperdir
    FieldTypes = Net.FieldTypes + [int]
    
    _RipperDir = 6
            
    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        if not self.Fields[self._RipperDir] in [-1,0,1]: raise Exception('Error: Invalid "ripperdir" on line %d.' % idx)
        return idx
    
class Pin(Net):
    'Pin'
    Code = 'P'
    #type x1 y1 x2 y2 color pintype whichend
    FieldTypes = Net.FieldTypes + [ePinType.New, int]
    
    _PinType = 6
    _WhichEnd = 7
            
    def FromFileSnippet(self, lines, idx):
        idx = super().FromFileSnippet(lines, idx)
        if not self.Fields[self._WhichEnd] in [0,1]: raise Exception('Error: Invalid "whichend" on line %d.' % idx)
        return idx

    def ToString(self):
        pNum = self.GetAttrib('pinnumber')
        if not pNum: pNum = 'none'
        pType = self.GetAttrib('pintype')
        if not pType: pType = '??'
        return "Pin: from (%d,%d) to (%d,%d), num=%s, type=%s" % (self.Fields[self._X1], self.Fields[self._Y1], self.Fields[self._X2], self.Fields[self._Y2], pNum, pType)

class Symbol(object): #descend from Schematic?
    def __init__(self, fName):
        try:
            self.__symFile = open(fName, 'r')
        except:
            raise Exception("Error opening symbol file.")
        self.__pinList = []
        self.allPinsNumeric = True
        self.__numPins = 0
        self.__numNumericPins = 0
        self.__problemCount = 0
        
class Schematic(object):
    def __init__(self):
        self.Items = []
    
    def FromLines(self, lines, idx=0):
        if lines[idx].strip() == '[':
            if idx == 0: raise Exception("Error: Unexpected start of embedded component at line 0.")
            embedded = True
            idx += 1
        else: embedded = False
        itemTypes = [GschVersion, Line, Box, Circle, Arc, Text, Component, Net, Bus, Pin]
        while idx < len(lines):
            if embedded and lines[idx].strip() == ']': return idx + 1
            parsed = False
            for itemType in itemTypes:
                if itemType.IsItem(lines[idx]):
                    item = itemType()
                    idx = item.FromFileSnippet(lines, idx)
                    self.Items.append(item)
                    parsed = True
                    #print("parsed %s" % type(item))
                    break
            if not parsed: raise Exception("Error: Unrecognized input data at line %d." % idx)
            
    def ToLines(self):
        result = []
        for item in self.Items:
            result.extend(item.ToFileSnippet())
        return result
    
    def FromFile(self, fName):
        with open(fName, 'r') as schFile:
            self.FromLines(schFile.readlines())
            
    def ToFile(self, fName):
        with open(fName, 'w') as schFile:
            for line in self.ToLines():
                schFile.write(line)

    def Print(self):
        for item in self.Items:
            print(item.ToString())
            
    def GetComponentsByAttrib(self, attrName, attrVal):
        if not attrName or not attrVal: raise Exception("Error: Schematic.GetComponentsByAttrib called with empty string param.")
        result = []
        if attrName == '*' and attrVal == '*':
            for item in self.Items:
                if type(item) != Component: continue
                result.append(item)
        elif attrName == '*':
            for item in self.Items:
                if type(item) != Component: continue
                attrDict = item.GetAttribs()
                if attrVal in attrDict.values(): result.append(item)
        elif attrVal == '*':
            for item in self.Items:
                if type(item) != Component: continue
                attrDict = item.GetAttribs()
                if attrName in attrDict: result.append(item)
        else:
            for item in self.Items:
                if type(item) != Component: continue
                if item.GetAttrib(attrName) == attrVal: result.append(item)
        return result
            

#sch = Schematic()
#sch.FromFile("/Users/gabrield/Project/CodeJet/Hardware/ControllerBoard/Schematic/Controller_p1.sch")
#sch.Print()