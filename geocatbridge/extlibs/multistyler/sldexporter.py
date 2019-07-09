import os
from qgis.core import *
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom
from geocatbridgecommons import log
import zipfile
from qgiscommons2.files import tempFilenameInTempFolder

_usedIcons = []

def saveLayerStyleAsZip(layer):    
    filename = tempFilenameInTempFolder(layer.name() + ".zip")
    z = zipfile.ZipFile(filename, "w")
    xml = processLayer(layer)
    sld = ElementTree.tostring(xml, encoding='utf8', method='xml').decode()
    for icon in _usedIcons:
        z.write(icon, os.path.basename(icon))
    z.writestr(layer.name() + ".sld", sld)
    z.close()
    log.logInfo("Style for layer %s exported as zip file to %s" % (layer.name(), filename))
    return filename

def saveLayerStyleAsSld(layer, filename):
    xml = processLayer(layer)    
    #dom = minidom.parseString()
    with open(filename, "w") as f:
        f.write(ElementTree.tostring(xml, encoding='utf8', method='xml').decode())
    print(_usedIcons)

def processLayer(layer):
    global _usedIcons
    _usedIcons = []
    attribs = {
        "version": "1.0.0",
        "xsi:schemaLocation": "http://www.opengis.net/sld StyledLayerDescriptor.xsd",
        "xmlns": "http://www.opengis.net/sld",
        "xmlns:ogc": "http://www.opengis.net/ogc",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
        }
    root = Element("StyledLayerDescriptor", attrib=attribs) 
    namedLayer = SubElement(root, "NamedLayer")
    layerName = SubElement(namedLayer, "Name")
    layerName.text = layer.name()
    userStyle = SubElement(namedLayer, "UserStyle")
    userStyleTitle = SubElement(userStyle, "Title")
    userStyleTitle.text = layer.name()
    if layer.type() == layer.VectorLayer:
        rules = []
        renderer = layer.renderer()
        if not isinstance(renderer, QgsRuleBasedRenderer):
            renderer = QgsRuleBasedRenderer.convertFromRenderer(renderer)
        if renderer is None:
            pass #show error          
        featureTypeStyle = SubElement(userStyle, "FeatureTypeStyle")
        for rule in renderer.rootRule().children():
            featureTypeStyle.append(processRule(rule))
    
    return root

def processRule(rule):    
    ruleElement = Element("Rule")
    ruleName = SubElement(ruleElement, "Name")
    ruleName.text = rule.label()
    symbolizers = createSymbolizers(rule.symbol().clone())
    ruleElement.extend(symbolizers)
    filt = processExpression(rule.filterExpression())    
    if filt is not None:
        filterElement = Element("ogc:Filter")
        filterElement.append(filt)
        ruleElement.append(filterElement)            
    if rule.dependsOnScale():
        maxScale = SubElement(ruleElement, "MaxScaleDenominator")
        maxScale.text = rule.maximumScale()
        minScale = SubElement(ruleElement, "MinScaleDenominator")
        maxScale.text = rule.minimumScale()
        
    return ruleElement

def processExpression(expstr):
    try:
        if expstr:
            exp = QgsExpression(expstr)
            return walkExpression(exp.rootNode())
        else:
            return None
    except:
        return None

def symbolProperty(symbolLayer, name, propertyConstant=-1):
    ddProps = symbolLayer.dataDefinedProperties()
    if propertyConstant in ddProps.propertyKeys():
        return processExpression(ddProps.property(propertyConstant).asExpression()) or ""
    else:
        return symbolLayer.properties()[name]

def getHexColor(color):
    try:
        r,g,b,a = str(color).split(",")
        return '#%02x%02x%02x' % (int(r), int(g), int(b))
    except:
        return color
        
def createSymbolizers(symbol):
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

    return symbolizer

def _addCssParameter(parent, name, value):
    sub = SubElement(parent, "CssParameter", name=name)
    if isinstance(value, Element):
        sub.append(value)
    else:
        sub.text = str(value)
    return sub

def _addSubElement(parent, tag, value=None):
    sub = SubElement(parent, tag)
    if value is not None:
        if isinstance(value, Element):
            sub.append(value)
        else:
            sub.text = str(value)
    return sub

def _fontMarkerSymbolizer(sl, opacity):
    color = getHexColor(symbolProperty(sl, "color", QgsSymbolLayer.PropertyFillColor))
    fontFamily = symbolProperty(sl, "font")
    character = symbolProperty(sl, "chr", QgsSymbolLayer.PropertyCharacter)
    size = symbolProperty(sl, "size", QgsSymbolLayer.PropertySize)

    root = Element("TextSymbolizer")
    _addSubElement(root, "Label", character)
    fontElem = _addSubElement(root, "Font")    
    _addCssParameter(fontElem, "font-family", fontFamily)
    _addCssParameter(fontElem, "font-size", size)
    fillElem = _addSubElement(root, "Fill")
    _addCssParameter(fontElem, "fill", color)
    return root

def _lineSymbolizer(sl, opacity):
    props = sl.properties()
    color = getHexColor(symbolProperty(sl, "line_color", QgsSymbolLayer.PropertyStrokeColor))
    width = symbolProperty(sl, "line_width", QgsSymbolLayer.PropertyStrokeWidth)
    lineWidthUnits = props["line_width_unit"]
    lineStyle = symbolProperty(sl, "line_style", QgsSymbolLayer.PropertyStrokeStyle)
    cap = symbolProperty(sl, "capstyle", QgsSymbolLayer.PropertyCapStyle)
    cap = "butt" if cap == "flat" else cap
    join = symbolProperty(sl, "joinstyle", QgsSymbolLayer.PropertyJoinStyle)
    offset = sl.offset()

    root = Element("LineSymbolizer")
    stroke = SubElement(root, "Stroke")
    _addCssParameter(stroke, "stroke", color)
    _addCssParameter(stroke, "stroke-width", width)
    _addCssParameter(stroke, "stroke-opacity", opacity)
    _addCssParameter(stroke, "stroke-linejoin", join)
    _addCssParameter(stroke, "stroke-linecap", cap)
    if lineStyle != "solid":        
        _addCssParameter(stroke, "stroke-dasharray", "5 2")
    if offset:
        _addSubElement(root, "PerpendicularOffset", offset)
    return root
    
def _geomGeneratorSymbolizer(sl, opacity):
    subSymbol = sl.subSymbol()
    symbolizers = createSymbolizers(subSymbol)
    geomExp = sl.geometryExpression()
    geomElement = Element("Geometry")
    geomElement.append(processExpression(geomExp))
    for symbolizer in symbolizers:
        symbolizer.append(geomElement)
    return symbolizers

def _svgMarkerSymbolizer(sl, opacity):
    root, graphic = _basePointSimbolizer(sl, opacity)
    svg = _svgGraphic(sl, opacity)
    graphic.append(svg)
    return root

def _rasterImageMarkerSymbolizer(sl, opacity):
    root, graphic = _basePointSimbolizer(sl, opacity)
    img = _rasterImageGraphic(sl, opacity)
    graphic.append(img)
    return root    

def _simpleMarkerSymbolizer(sl, opacity):
    root, graphic = _basePointSimbolizer(sl, opacity)
    mark = _markGraphic(sl, opacity)
    graphic.append(mark)
    return root

def _basePointSimbolizer(sl, opacity):
    props = sl.properties()
    size = symbolProperty(sl, "size", QgsSymbolLayer.PropertySize)
    units = props["size_unit"] #TODO: Use this
    rotation = symbolProperty(sl, "angle", QgsSymbolLayer.PropertyAngle)
    x, y = sl.offset().x(), sl.offset().y()
    
    root = Element("PointSymbolizer")
    graphic = SubElement(root, "Graphic")
    _addSubElement(graphic, "Size", size)
    _addSubElement(graphic, "Rotation", rotation)
    _addSubElement(graphic, "Opacity", opacity)
    if x or y:
        geom = SubElement(root, "Geometry")
        func = SubElement(geom, "ogc:Function", name="offset")
        _addSubElement(func, "ogc:PropertyName", geom)
        _addSubElement(func, "ogc:Literal", x)
        _addSubElement(func, "ogc:Literal", y)
    return root, graphic

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

def _markGraphic(sl, opacity):
    props = sl.properties()
    color = getHexColor(symbolProperty(sl, "color"))
    outlineColor = getHexColor(symbolProperty(sl, "outline_color"))
    outlineWidth = symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth)
    outlineWidth = 1 if str(outlineWidth) == 0.0 else outlineWidth
    outlineStyle = symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    shape = props["name"]
    mark = Element("Mark")
    _addSubElement(mark, "WellKnownName", wknReplacements.get(shape, shape))    
    fill = SubElement(mark, "Fill")
    _addCssParameter(fill, "fill", color)
    stroke = SubElement(mark, "Stroke")
    _addCssParameter(stroke, "stroke", outlineColor)
    _addCssParameter(stroke, "stroke-width", outlineWidth)

    return mark

def _markFillPattern(shape, color):
    mark = Element("Mark")
    _addSubElement(mark, "WellKnownName", wknReplacements.get(shape, shape))    
    stroke = SubElement(mark, "Stroke")
    _addCssParameter(stroke, "stroke", color)
    return mark

def _svgGraphic(sl, opacity):
    global _usedIcons
    _usedIcons.append(sl.path())
    path = os.path.basename(sl.path())
    externalGraphic = Element("ExternalGraphic")  
    attrib = {
        "xlink:type": "simple",
        "xlink:href": path
    } 
    SubElement(externalGraphic, "OnlineResource", attrib=attrib)
    _addSubElement(externalGraphic, "Format", "image/svg+xml") 
    return externalGraphic   

def _rasterImageGraphic(sl, opacity):
    global _usedIcons
    _usedIcons.append(sl.path())
    path = os.path.basename(sl.path())
    externalGraphic = Element("ExternalGraphic")  
    attrib = {
        "xlink:type": "simple",
        "xlink:href": path
    } 
    SubElement(externalGraphic, "OnlineResource", attrib=attrib)
    _addSubElement(externalGraphic, "Format", "image/%s" % os.path.splitext(path)[1][1:]) 
    return externalGraphic 

def _baseFillSymbolizer(sl, opacity):
    root = Element("PolygonSymbolizer")  

    return root

def _pointPatternFillSymbolizer(sl, opacity):    
    root = _baseFillSymbolizer(sl, opacity)
    subsymbol = sl.subSymbol().symbolLayer(0)
    size = symbolProperty(subsymbol, "size", QgsSymbolLayer.PropertySize)    
    if isinstance(subsymbol, QgsSimpleMarkerSymbolLayer):
        marker = _markGraphic(subsymbol, opacity)
    elif isinstance(subsymbol, QgsSvgMarkerSymbolLayer):
        marker = _svgGraphic(subsymbol, opacity)
    elif isinstance(subsymbol, QgsRasterMarkerSymbolLayer):
        marker = _rasterImageGraphic(subsymbol, opacity)        
    else:
        marker = None # TODO
        log.logWarning("Unsupported symbol in point pattern fill: " + type(subsymbol))

    fill = _addSubElement(root, "fill")
    graphicFill = _addSubElement(fill, "GraphicFill")
    graphic = _addSubElement(graphicFill, "Graphic")    
    if marker is not None:
        graphic.append(marker)
    _addSubElement(graphicFill, "Size", size)
    _addSubElement(graphicFill, "Opacity", opacity)
    return root

patternNamesReplacement = {"horizontal": "horline",
                            "vertical": "vertline",
                            "cross": "x"} #TODO

def _simpleFillSymbolizer(sl, opacity):
    props = sl.properties()
    style = props["style"]
    if style != "no":
        color =  getHexColor(symbolProperty(sl, "color", QgsSymbolLayer.PropertyFillColor))        
        root = _baseFillSymbolizer(sl, opacity)
        fill = SubElement(root, "Fill")
        if style == "solid":
            _addCssParameter(fill, "fill", color)
            _addCssParameter(fill, "fill-opacity", 1)
        else:
            graphicFill = _addSubElement(fill, "GraphicFill")
            graphic = _addSubElement(graphicFill, "Graphic") 
            style = patternNamesReplacement.get(style, style)
            marker = _markFillPattern(style, color)
            graphic.append(marker)
            _addSubElement(graphicFill, "Size", 10)
            _addSubElement(graphicFill, "Opacity", opacity)

    outlineColor =  getHexColor(symbolProperty(sl, "outline_color", QgsSymbolLayer.PropertyStrokeColor))
    outlineStyle = symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    if outlineStyle != "no": 
        outlineWidth = symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth)
        borderWidthUnits = props["outline_width_unit"]
        stroke = SubElement(root, "Stroke")
        _addCssParameter(stroke, "stroke", outlineColor)
        _addCssParameter(stroke, "stroke-width", outlineWidth)
        _addCssParameter(stroke, "stroke-opacity", opacity)
        #_addCssParameter(stroke, "stroke-linejoin", join)
        #_addCssParameter(stroke, "stroke-linecap", cap)
        if outlineStyle != "solid":
            _addCssParameter(stroke, "stroke-dasharray", "5 2")
    
    x, y = sl.offset().x(), sl.offset().y()    
    if x or y:
        geom = SubElement(root, "Geometry")
        func = SubElement(geom, "ogc:Function", name="offset")
        _addSubElement(func, "ogc:PropertyName", geom)
        _addSubElement(func, "ogc:Literal", x)
        _addSubElement(func, "ogc:Literal", y)

    return root

#######################

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
             "replace": "strReplace"} #TODO

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
        exp = handleColumnName(node)
    #elif node.nodeType() == QgsExpression.ntCondition:
    #    filt = handle_condition(nod)
    return exp

def handleBinary(node):
    op = node.op()
    retOp = binaryOps[op]
    left = node.opLeft()
    right = node.opRight()
    retLeft = walkExpression(left)
    retRight = walkExpression(right)
    element = Element(retOp)
    element.append(retLeft)
    element.append(retRight)
    return element

def handleUnary(node):
    op = node.op()
    operand = node.operand()
    retOp = unaryOps[op]
    retOperand = walkExpression(operand)
    element = Element(retOp)
    element.append(retOperand)
    return element

def handleLiteral(node):
    elem = Element("Literal")
    elem.text = str(node.value())
    return elem

def handleColumnName(node):
    elem = Element("PropertyName")
    elem.text = node.name()
    return elem

def handleFunction(node):
    fnIndex = node.fnIndex()
    func = QgsExpression.Functions()[fnIndex].name()
    if func == "$geometry":
        elem = Element("PropertyName")
        elem.text = "geom"        
    elif func in functions:        
        gsFunction = functions[func]
        elem = Element("Function", name=gsFunction)
        args = node.args()
        if args is not None:
            args = args.list()
            for arg in args:
                elem.append(walkExpression(arg))           
    else:
        elem = Element("Literal")
        elem.text = "1"
        log.logWarning("Expression function '%s' not supported" % func)
    return elem
