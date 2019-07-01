
from qgis.core import *
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom

def saveLayerStyleAsSld(layer, filename):
    xml = processLayer(layer)    
    #dom = minidom.parseString()
    with open(filename, "w") as f:
        f.write(ElementTree.tostring(xml, encoding='utf8', method='xml').decode())

def processLayer(layer):
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
        raise
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
        props = sl.properties()
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
        
        if symbolizer is not None:
            symbolizers.append(symbolizer)

    return symbolizers

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

def _lineSymbolizer(sl, opacity):
    color = getHexColor(symbolProperty(sl, "line_color", QgsSymbolLayer.PropertyStrokeColor))
    width = symbolProperty(sl, "line_width", QgsSymbolLayer.PropertyStrokeColor)
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
    
def _svgMarkerSymbolizer(sl, opacity):
    root, graphic = _basePointSimbolizer(sl, opacity)
    svg = _svgGraphic(sl, opacity)
    graphic.append(svg)
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

def _markGraphic(sl, opacity):
    props = sl.properties()
    color = getHexColor(symbolProperty(sl, "color"))
    outlineColor = getHexColor(symbolProperty(sl, "outline_color"))
    outlineWidth = symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth)
    outlineWidth = 1 if str(outlineWidth) == 0.0 else outlineWidth
    outlineStyle = symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    shape = props["name"]
    mark = Element("Mark")
    _addSubElement(mark, "WellKnownName", shape)    
    fill = SubElement(mark, "Fill")
    _addCssParameter(fill, "fill", color)
    _addCssParameter(fill, "fill-opacity", opacity)
    stroke = SubElement(mark, "Stroke")
    _addCssParameter(stroke, "stroke", outlineColor)
    _addCssParameter(stroke, "stroke-width", outlineWidth)
    _addCssParameter(stroke, "stroke-opacity", opacity)

    return mark

def _svgGraphic(sl):
    path = sl.path()
    externalGraphic = Element("ExternalGraphic")  
    attrib = {
        "xlink:type": "simple",
        "xlink:href": sl.path()
    } 
    SubElement(externalGraphic, "OnlineResource", attrib=attrib)
    _addSubElement(externalGraphic, "Format", "image/svg+xml") 
    return externalGraphic   

def _baseFillSymbolizer(sl, opacity):
    root = Element("PolygonSymbolizer")        

    return root

def _pointPatternFillSymbolizer(sl, opacity):    
    root = _baseFillSymbolizer(sl, opacity)
    subsymbol = sl.subSymbol().symbolLayer(0)
    size = symbolProperty(subsymbol, "size", QgsSymbolLayer.PropertySize)    
    print(type(subsymbol))
    if isinstance(subsymbol, QgsSimpleMarkerSymbolLayer):
        marker = _markGraphic(subsymbol, opacity)
    elif isinstance(sl, QgsSvgMarkerSymbolLayer):
        marker = _svgGraphic(subsymbol, opacity)
    else:
        marker = None # TODO

    fill = _addSubElement(root, "fill")
    graphicFill = _addSubElement(fill, "GraphicFill")
    graphic = _addSubElement(graphicFill, "Graphic")    
    if marker is not None:
        graphic.append(marker)
    _addSubElement(graphicFill, "Size", size)
    return root

def _simpleFillSymbolizer(sl, opacity):
    props = sl.properties()
    if props["style"] == "no":
        fillAlpha = 0                
    else:
        fillAlpha = opacity
    color =  getHexColor(symbolProperty(sl, "color", QgsSymbolLayer.PropertyFillColor))        
    root = _baseFillSymbolizer(sl, opacity)
    fill = SubElement(root, "Fill")
    _addCssParameter(fill, "fill", color)
    _addCssParameter(fill, "fill-opacity", fillAlpha)

    outlineColor =  getHexColor(symbolProperty(sl, "outline_color", QgsSymbolLayer.PropertyStrokeColor))
    outlineStyle = symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    if outlineStyle != "no": 
        outlineWidth = symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth)
    else:
        outlineWidth = 0
    borderWidthUnits = props["outline_width_unit"]
    stroke = SubElement(root, "Stroke")
    _addCssParameter(stroke, "stroke", outlineColor)
    _addCssParameter(stroke, "stroke-width", outlineWidth)
    _addCssParameter(stroke, "stroke-opacity", opacity)
    #_addCssParameter(stroke, "stroke-linejoin", join)
    #_addCssParameter(stroke, "stroke-linecap", cap)
    if outlineStyle not in ["solid", "no"]:
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

def walkExpression(node):
    if node.nodeType() == QgsExpressionNode.ntBinaryOperator:
        exp = handleBinary(node)
    elif node.nodeType() == QgsExpressionNode.ntUnaryOperator:
        exp = handleUnary(node)
    #elif node.nodeType() == QgsExpressionNode.ntInOperator:
        #filt = handle_in(node)
    #elif node.nodeType() == QgsExpression.ntFunction:
    #    filt = handle_function(node)
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
