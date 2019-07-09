import json
from qgis.core import *

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
    symbolizers = createSymbolizers(rule.symbol().clone())
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
            symbolizer = _markerSymbolizer(sl, opacity)            
        elif isinstance(sl, QgsSimpleLineSymbolLayer):
            color = getHexColor(symbolProperty(sl, "line_color", QgsSymbolLayer.PropertyStrokeColor))
            width = symbolProperty(sl, "line_width", QgsSymbolLayer.PropertyStrokeColor)
            lineWidthUnits = props["line_width_unit"]
            lineStyle = symbolProperty(sl, "line_style", QgsSymbolLayer.PropertyStrokeStyle)
            cap = symbolProperty(sl, "capstyle", QgsSymbolLayer.PropertyCapStyle)
            cap = "butt" if cap == "flat" else cap
            join = symbolProperty(sl, "joinstyle", QgsSymbolLayer.PropertyJoinStyle)
            offset = sl.offset()
            symbolizer = {"kind": "Line",
                    "color": color,
                    "opacity": opacity,
                    "width": shape,
                    "dasharray": lineStyle, #TODO check this
                    "perpendicularOffset": offset,
                    "cap": cap,
                    "join": join
                    }
            if lineStyle != "solid":
                symbolizer["dasharray"] = [5, 2]
        elif isinstance(sl, QgsSimpleFillSymbolLayer):
            symbolizer = _fillSymbolizer(sl, opacity)
        elif isinstance(sl, QgsSVGFillSymbolLayer):
            path = os.path.basename(sl.svgPath())
            size = symbolProperty(sl, "width", QgsSymbolLayer.PropertyWidth)
            color = sl.svgFillColor().name()
            x, y = sl.offset().x(), sl.offset().y()
            svg = {"kind": "Icon",
                    "color": color,
                    "opacity": opacity,
                    "image": path,
                    "size": size,
                    }
            symbolizer = _fillSymbolizer(sl, opacity)
            symbolizer["graphicFill"] = svg
        elif isinstance(sl, QgsPointPatternFillSymbolLayer):
            subSymbolizer = _markerSymbolizer(sl.subSymbol().symbolLayer(0), opacity)
            symbolizer = _fillSymbolizer(sl, opacity)
            symbolizer["graphicFill"] = subSymbolizer
        elif isinstance(sl, QgsSvgMarkerSymbolLayer):
            symbolizer = _svgMarkerSymbolizer(sl, opacity)
        
        if symbolizer is not None:
            symbolizers.append(symbolizer)

    return symbolizers

def _markerSymbolizer(sl, opacity):
    props = sl.properties()
    size = symbolProperty(sl, "size", QgsSymbolLayer.PropertySize)
    units = props["size_unit"] #TODO: Use this
    color = getHexColor(symbolProperty(sl, "color"))
    outlineColor = getHexColor(symbolProperty(sl, "outline_color"))
    outlineWidth = float(symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth))
    outlineWidth = 1 if str(outlineWidth) == 0.0 else outlineWidth
    outlineStyle = symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    shape = props["name"]
    rotation = symbolProperty(sl, "angle", QgsSymbolLayer.PropertyAngle)
    x, y = sl.offset().x(), sl.offset().y()
    return {"kind": "Mark",
            "color": color,
            "opacity": opacity,
            "wellKnownName": shape,
            "radius": size,
            "strokeColor": outlineColor,
            "strokeWidth": outlineWidth,
            "offset": [x, y],
            "rotate": rotation
            } 

def _svgMarkerSymbolizer(sl, opacity):
    props = sl.properties()
    size = symbolProperty(sl, "size", QgsSymbolLayer.PropertySize)
    color = getHexColor(symbolProperty(sl, "color"))
    rotation = symbolProperty(sl, "angle", QgsSymbolLayer.PropertyAngle)
    x, y = sl.offset().x(), sl.offset().y()
    return {"kind": "Icon",
            "color": color,
            "opacity": opacity,
            "image": sl.path(),
            "size": size,
            "offset": [x, y],
            "rotate": rotation
            } 

def _fillSymbolizer(sl, opacity):
    if props["style"] == "no":
        fillAlpha = 0                
    else:
        fillAlpha = alpha            
    color =  getHexColor(symbolProperty(sl, "color", QgsSymbolLayer.PropertyFillColor))
    outlineColor =  getHexColor(symbolProperty(sl, "outline_color", QgsSymbolLayer.PropertyStrokeColor))
    outlineStyle = symbolProperty(sl, "outline_style", QgsSymbolLayer.PropertyStrokeStyle)
    outlineWidth = symbolProperty(sl, "outline_width", QgsSymbolLayer.PropertyStrokeWidth)
    borderWidthUnits = props["outline_width_unit"]
    x, y = sl.offset().x(), sl.offset().y()
    symbolizer = {"kind": "Fill",
                  "opacity": fillAlpha,
                  "outlineColor": outlineColor,
                  "color": color,
                  "outlineWidth": outlineWidth}
    if outlineStyle not in ["solid", "no"]:
        symbolizer["outlineDasharray"] = [5, 2]
    if x or y:
        symbolizer["translate"] = [x,y]
    return symbolizer

#######################33

binary_ops = [
    "||", "&&",
    "==", "!=", "<=", ">=", "<", ">", "~",
    "LIKE", "NOT LIKE", "ILIKE", "NOT ILIKE", "===", "!==",
    "+", "-", "*", "/", "//", "%", "^",
    "+"
]

unary_ops = ["!", "-"]

def walkExpression(node):
    try:
        if node.nodeType() == QgsExpressionNode.ntBinaryOperator:
            filt = handle_binary(node)
        elif node.nodeType() == QgsExpressionNode.ntUnaryOperator:
            filt = handle_unary(node)
        #elif node.nodeType() == QgsExpressionNode.ntInOperator:
            #filt = handle_in(node)
        #elif node.nodeType() == QgsExpression.ntFunction:
        #    filt = handle_function(node)
        elif node.nodeType() == QgsExpressionNode.ntLiteral:
            filt = handle_literal(node)
        elif node.nodeType() == QgsExpressionNode.ntColumnRef:
            filt = handle_columnRef(node)
        #elif node.nodeType() == QgsExpression.ntCondition:
        #    filt = handle_condition(nod)
        return filt
    except:
        return []

def handle_binary(node):
    op = node.op()
    retOp = binary_ops[op]
    left = node.opLeft()
    right = node.opRight()
    retLeft = walkExpression(left)
    retRight = walkExpression(right)
    return [retOp, retLeft, retRight]

def handle_unary(node):
    op = node.op()
    operand = node.operand()
    retOp = unary_ops[op]
    retOperand = walkExpression(operand)
    return [retOp, retOperand]


def handle_literal(node):
    val = node.value()
    quote = ""
    if isinstance(val, basestring):
        quote = "'"
        val = val.replace("\n", "\\n")
    elif val is None:
        val = "null"

    return "%s%s%s" % (quote, unicode(val), quote)

def handle_columnRef(node):
    return node.name()