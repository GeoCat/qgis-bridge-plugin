import os
from qgis.core import *
import json
#from geocatbridgecommons import log
import zipfile
from qgiscommons2.files import tempFilenameInTempFolder

_usedIcons = []


def layerAsGeostyler(layer):
    global _usedIcons
    _usedIcons = []
    geostyler = processLayer(layer)
    return geostyler, _usedIcons 

def saveLayerStyleAsGeostyler(layer, filename):
    s = json.dumps(processLayer(layer), indent=4, sort_keys=True)
    with open(filename, "w") as f:
        f.write(s)

def processLayer(layer):
    if layer.type() == layer.VectorLayer:
        rules = []
        renderer = layer.renderer()
        if not isinstance(renderer, QgsRuleBasedRenderer):
            renderer = QgsRuleBasedRenderer.convertFromRenderer(renderer)
        if renderer is None:
            pass #show error
        for rule in renderer.rootRule().children():
            rules.append(processRule(rule))
        return  {"name": layer.name(), "rules": rules}

def processRule(rule):
    symbolizers = _createSymbolizers(rule.symbol().clone())
    name = rule.label()
    ruledef = {"name": name,
            "symbolizers": symbolizers}
    if not(rule.isElse()):
        filt = processExpression(rule.filterExpression())
        if filt is not None:
            ruledef["filter"] = filt
    if rule.dependsOnScale():
        scale = processRuleScale(rule)
        ruledef["scaleDenominator"] = scale
    return ruledef

def processRuleScale(rule):
    return {"min": rule.minimumScale(),
            "max": rule.maximumScale()}

def processExpression(expstr):
    try:
        if expstr:
            exp = QgsExpression(expstr)
            return walkExpression(exp.rootNode())
        else:
            return None
    except:
        return None

def _cast(v):
    if isinstance(v, basestring):
        try:
            return float(v)
        except:
            return v
    else:
        return v

MM2PIXEL = 3.7795275591

def _handleUnits(value, units):
    if str(value) in ["0", "0.0"]:
        return 1 #hairline width
    if units == "MM":        
        return ["Mul", MM2PIXEL, value]        
    elif units == "RenderMetersInMapUnits":
        if isinstance(value, list):
            print ("Cannot render in map units when using a data-defined size value: '%s'" % str(value))
            return value
        else:
            return str(value) + "m"
    elif units == "Pixel":
        return value
    else:
        print("Unsupported units: '%s'" % units)
        return value


def _symbolProperty(symbolLayer, name, propertyConstant=-1, units=None):
    ddProps = symbolLayer.dataDefinedProperties()
    if propertyConstant in ddProps.propertyKeys():
        v = processExpression(ddProps.property(propertyConstant).asExpression()) or ""        
    else:
        v = symbolLayer.properties()[name]

    if units is not None:
        v = _handleUnits(v, units)
    return _cast(v)

def _toHexColor(color):
    try:
        r,g,b,a = str(color).split(",")
        return '#%02x%02x%02x' % (int(r), int(g), int(b))
    except:
        return color
        
def _createSymbolizers(symbol):
    opacity = symbol.opacity()
    symbolizers = []    
    for sl in symbol.symbolLayers():
        symbolizer = _createSymbolizer(sl, opacity)        
        if symbolizer is not None:
            if isinstance(symbolizer, list):
                symbolizers.extend(symbolizer)
            else:
                symbolizers.append(symbolizer)

    return symbolizers

def _createSymbolizer(sl, opacity):
    symbolizer = None
    if isinstance(sl, QgsSimpleMarkerSymbolLayer):
        symbolizer = _simpleMarkerSymbolizer(sl, opacity)            
    elif isinstance(sl, QgsSimpleLineSymbolLayer):
        symbolizer = _lineSymbolizer(sl, opacity)
    elif isinstance(sl, QgsMarkerLineSymbolLayer):
        symbolizer = _markerLineSymbolizer(sl, opacity)   
    elif isinstance(sl, QgsSimpleFillSymbolLayer):
        symbolizer = _simpleFillSymbolizer(sl, opacity)
    elif isinstance(sl, QgsPointPatternFillSymbolLayer):
        symbolizer = _pointPatternFillSymbolizer(sl, opacity)
    elif isinstance(sl, QgsSvgMarkerSymbolLayer):
        symbolizer = _svgMarkerSymbolizer(sl, opacity)
    elif isinstance(sl, QgsRasterMarkerSymbolLayer):
        symbolizer = _rasterImageMarkerSymbolizer(sl, opacity)      
    elif isinstance(sl, QgsGeometryGeneratorSymbolLayer):
        symbolizer = _geomGeneratorSymbolizer(sl, opacity)
    elif isinstance(sl, QgsFontMarkerSymbolLayer):
        symbolizer = _fontMarkerSymbolizer(sl, opacity)

    if symbolizer is None:
        print("Symbol layer type not supported: '%s'" % type(sl))
    return symbolizer


def _fontMarkerSymbolizer(sl, opacity):
    color = _toHexColor(sl.properties()["color"])
    fontFamily = _symbolProperty(sl, "font")
    character = _symbolProperty(sl, "chr", QgsSymbolLayer.PropertyCharacter)
    size = _symbolProperty(sl, "size", QgsSymbolLayer.PropertySize)

    symbolizer = {"kind": "Text",
                    "size": size,
                    "label": character,
                    "font": fontFamily,
                    "color": color}    
    return symbolizer

def _lineSymbolizer(sl, opacity):
    props = sl.properties()
    color = _toHexColor(props["line_color"])
    lineWidthUnits = props["line_width_unit"]
    width = _symbolProperty(sl, "line_width", QgsSymbolLayer.PropertyStrokeWidth, lineWidthUnits)    
    lineStyle = _symbolProperty(sl, "line_style", QgsSymbolLayer.PropertyStrokeStyle)
    cap = _symbolProperty(sl, "capstyle", QgsSymbolLayer.PropertyCapStyle)
    cap = "butt" if cap == "flat" else cap
    join = _symbolProperty(sl, "joinstyle", QgsSymbolLayer.PropertyJoinStyle)
    offset = sl.offset()

    symbolizer = {"kind": "Line",
                    "color": color,
                    "opacity": opacity,
                    "width": width,
                    "perpendicularOffset": offset,
                    "cap": cap,
                    "join": join
                    }
    if lineStyle != "solid":
        symbolizer["dasharray"] = "5 2"
    return symbolizer

def _markerLineSymbolizer(sl, opacity):
    symbolizer = {"kind": "Line",                
                    "opacity": opacity}
    subSymbolizers = []
    for subsl in sl.subSymbol().symbolLayers():       
        subSymbolizer = _createSymbolizer(subsl, 1)
        if subSymbolizers is not None:
            subSymbolizers.append(subSymbolizer)
    if subSymbolizers:
        interval = _symbolProperty(sl, "interval", QgsSymbolLayer.PropertyInterval)
        symbolizer["graphicStroke"] = subSymbolizers
        symbolizer["graphicStrokeInterval"] = interval        

    return symbolizer    

def _geomGeneratorSymbolizer(sl, opacity):
    subSymbol = sl.subSymbol()
    symbolizers = _createSymbolizers(subSymbol)
    geomExp = sl.geometryExpression()    
    geom = processExpression(geomExp)
    for symbolizer in symbolizers:
        symbolizer["Geometry"] = geom
    return symbolizers

def _svgMarkerSymbolizer(sl, opacity):
    marker = _basePointSimbolizer(sl, opacity)
    color = _toHexColor(sl.properties()["color"])
    marker["color"] = color
    svg = _markGraphic(sl)    
    marker.update(svg)
    return marker

def _rasterImageMarkerSymbolizer(sl, opacity):
    marker = _basePointSimbolizer(sl, opacity)
    img = _iconGraphic(sl)
    marker.update(img)
    return marker  

def _simpleMarkerSymbolizer(sl, opacity):
    marker = _basePointSimbolizer(sl, opacity)
    mark = _markGraphic(sl)
    marker.update(mark)    
    return marker

def _basePointSimbolizer(sl, opacity):
    props = sl.properties()        
    rotation = _symbolProperty(sl, "angle", QgsSymbolLayer.PropertyAngle)
    x, y = sl.offset().x(), sl.offset().y()
    
    symbolizer =  {
        "opacity": opacity,
        "rotate": rotation
        } 

    if x or y:
        symbolizer["geometry"] = processExpression("translate(%s,%s)" % (str(x), str(y)))

    return symbolizer

wknReplacements = {"regular_star":"star",
               "cross2": "x",
               "equilateral_triangle": "triangle",
               "rectangle": "square",
               "filled_arrowhead": "ttf://Webdings#0x34",
               "line": "shape://vertline",
               "arrow": "ttf://Wingdings#0xE9",
               "diamond": "ttf://Wingdings#0x75",
                "horline":"shape://horline",
               "vertline":"shape://vertline",
               "cross":"shape://plus",
               "slash":"shape://slash",
               "backslash":"shape://backslash",
               "x": "shape://times"}

def _markGraphic(sl):
    props = sl.properties()
    units = props["size_unit"] 
    size = _symbolProperty(sl, "size", QgsSymbolLayer.PropertySize, units)
    color = _toHexColor(props["color"])
    outlineColor = _toHexColor(props["outline_color"])
    units = props["outline_width_unit"] 
    outlineWidth = _symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth, units)    
    try:
        path = sl.path()
        name = "file://" + os.path.basename(path)
        outlineStyle = "solid"
    except:
        name = props["name"]
        name = wknReplacements.get(name, name)
        outlineStyle = _symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
        if outlineStyle == "no":
            outlineWidth = 0

    mark = {"kind": "Mark",
            "color": color,
            "wellKnownName": name,
            "size": size,
            "strokeColor": outlineColor,
            "strokeWidth": outlineWidth            
            } 
    if outlineStyle not in ["solid", "no"]:
        mark["strokeDasharray"] = "5 2"

    return mark

FIXED_PATTERN_SIZE = 10

def _markFillPattern(shape, color):    
    shape = wknReplacements.get(shape, shape)
    return {"kind": "Mark",
            "color": color,
            "wellKnownName": shape,
            "size": FIXED_PATTERN_SIZE,
            "strokeColor": color,
            "strokeWidth": 1
            } 

def _iconGraphic(sl, color=None):    
    global _usedIcons
    _usedIcons.append(sl.path())
    path = os.path.basename(sl.path())
    units = props["size_unit"] 
    size = _symbolProperty(sl, "size", QgsSymbolLayer.PropertySize, units)
    return {"kind": "Icon",
            "color": color,
            "image": path,
            "size": size,
            }  

def _baseFillSymbolizer(sl, opacity):
    return {"kind": "Fill",
            "opacity": opacity}

def _pointPatternFillSymbolizer(sl, opacity):    
    symbolizer = _baseFillSymbolizer(sl, opacity)
    subSymbolizers = []
    for subsl in sl.subSymbol().symbolLayers():       
        subSymbolizer = _createSymbolizer(subsl, 1)
        if subSymbolizers is not None:
            subSymbolizers.append(subSymbolizer)
    if subSymbolizers:
        distancex = _symbolProperty(sl, "distance_x", QgsSymbolLayer.PropertyDistanceX)
        distancey = _symbolProperty(sl, "distance_y", QgsSymbolLayer.PropertyDistanceY)
        symbolizer["graphicFill"] = subSymbolizers
        distancex = ["Div", distancex, 2] if isinstance(distancex, list) else distancex / 2.0
        distancey = ["Div", distancex, 2] if isinstance(distancey, list) else distancey / 2.0
        symbolizer["graphicFillMarginX"] = distancex
        symbolizer["graphicFillMarginY"] = distancey

    return symbolizer

patternNamesReplacement = {"horizontal": "horline",
                            "vertical": "vertline",
                            "cross": "x"} #TODO

def _simpleFillSymbolizer(sl, opacity):
    props = sl.properties()
    style = props["style"]
    
    symbolizer = _baseFillSymbolizer(sl, opacity)

    if style != "no":
        color =  _toHexColor(props["color"])               
        if style == "solid":
            symbolizer["color"] = color            
        else:
            style = patternNamesReplacement.get(style, style)
            marker = _markFillPattern(style, color)
            symbolizer["graphicFill"] = [marker]
            symbolizer["graphicFillDistanceX"] = FIXED_PATTERN_SIZE / 2.0
            symbolizer["graphicFillDistanceY"] = FIXED_PATTERN_SIZE / 2.0

    outlineColor =  _toHexColor(props["outline_color"])
    outlineStyle = _symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    if outlineStyle != "no":
        units = props["outline_width_unit"] 
        outlineWidth = _symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth, units)
        borderWidthUnits = props["outline_width_unit"]
        symbolizer.update({"outlineColor": outlineColor,
                            "outlineWidth": outlineWidth})
    if outlineStyle not in ["solid", "no"]:
        symbolizer["outlineDasharray"] ="5 2"

    x, y = sl.offset().x(), sl.offset().y()    
    if x or y:
        symbolizer["geometry"] = processExpression("translate(%s,%s)" % (str(x), str(y)))

    return symbolizer

#######################Expressions#################

binaryOps = [
     "Or",
    "And",
     "PropertyIsEqualTo",
     "PropertyIsNotEqualTo",
     "PropertyIsLessThanOrEqualTo",
     "PropertyIsGreaterThanEqualTo",
     "PropertyIsLessThan",
     "PropertyIsGreater",
     None, None, None, None, None, None, None,
     "Add",
      "Sub",
      "Mul",
      "Div",
      None, None, None, None]

unaryOps = ["Not", None]

functions = {"radians": "toRadians",
             "degrees": "toDegrees",
             "floor": "floor",
             "area": "area",
             "buffer": "buffer",
             "centroid": "centroid",
             "if": "if_then_else",
             "bounds": "envelope",
             "distance": "distance",
             "convex_hull": "convexHull",
             "end_point": "endPoint",
             "start_point": "startPoint",
             "x": "getX",
             "x": "getY",
             "concat": "Concatenate",
             "substr": "strSubstr",
             "lower": "strToLower",
             "upper": "strToUpper",
             "replace": "strReplace",
             "exterior_ring": "exteriorRing"} #TODO

def walkExpression(node):
    if node.nodeType() == QgsExpressionNode.ntBinaryOperator:
        exp = handleBinary(node)
    elif node.nodeType() == QgsExpressionNode.ntUnaryOperator:
        exp = handleUnary(node)
    #elif node.nodeType() == QgsExpressionNode.ntInOperator:
        #filt = handle_in(node)
    elif node.nodeType() == QgsExpressionNode.ntFunction:
        exp = handleFunction(node)
    elif node.nodeType() == QgsExpressionNode.ntLiteral:
        exp = handleLiteral(node)
    elif node.nodeType() == QgsExpressionNode.ntColumnRef:
        exp = handleColumnRef(node)
    #elif node.nodeType() == QgsExpression.ntCondition:
    #    filt = handle_condition(nod)
    return exp

def handleBinary(node):
    op = node.op()
    retOp = binary_ops[op]
    left = node.opLeft()
    right = node.opRight()
    retLeft = walkExpression(left)
    retRight = walkExpression(right)
    return [retOp, retLeft, retRight]

def handleUnary(node):
    op = node.op()
    operand = node.operand()
    retOp = unary_ops[op]
    retOperand = walkExpression(operand)
    return [retOp, retOperand]

def handleLiteral(node):
    val = node.value()
    quote = ""
    if isinstance(val, basestring):
        quote = "'"
        val = val.replace("\n", "\\n")
    elif val is None:
        val = "null"
    return val

def handleColumnRef(node):
    return ["PropertyName", node.name()]

def handleFunction(node):
    fnIndex = node.fnIndex()
    func = QgsExpression.Functions()[fnIndex].name()
    if func == "$geometry":
        return ["PropertyName", "geom"]
    elif func in functions:        
        elems = [functions[func]]
        args = node.args()
        if args is not None:
            args = args.list()
            for arg in args:
                elems.append(walkExpression(arg))
        return elems
    else:
        print("Unsupported function in expression: '%s'" % func)    
        return "1"    

