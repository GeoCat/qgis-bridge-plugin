
# Renderers and Symbols Supported

Bridge supports several layer renderers and symbol types. In this
paragraph an overview of supported renderers and possible limitations
during conversion to Styled Layer Descriptor (SLD) files are listed. The
conversion is optimized for GeoServer supporting some of the SLD
extensions that are provided, like dynamic symbolizers and chart
renderers.

Although using GeoServer SLD extensions helps to create a high quality
SLD, they will not always give the exact same result as the 
Desktop symbology. The GeoServer SLD extensions are continuously
improved, but there are the following limitations:

Fonts used in symbols of the layers configured in Desktop
should be available on the GeoServer map server. This is not always
the case. The SLD engine maps a set of proprietary font symbols to
Webdings and Wingdings font symbols. These fonts should then be
available on the server running GeoServer.

## Feature layers


### Feature layer renderers


| Renderer                      | Supported                                 |
| ----------------------------- | ----------------------------------------- |
| *Features*                    |                                           |
| Single Symbol                 | x                        |
| *Categories*                  |                                           |
| Unique values                 | x                        |
| Unique values, many fields    | x                        |
| Match to symbols in a style   | :x: [^1]                                  |
| *Quantities*                  |                                           |
| Graduated colors              | x                        |
| Graduated symbols             | x                        |
| Proportional symbols          | x                        |
| Dot density                   | x [^2]                   |
| *Charts*[^3]                  |                                           |
| Pie                           | x                        |
| Bar/Column                    | x                        |
| Stacked                       | x                        |
| *Multiple attributes*         |                                           |
| Quantity by category          | x                        |

### Point symbols

| Symbol type              | Supported                                 |
| ------------------------ | ----------------------------------------- |
| Character marker symbol  | x [^4]                   |
| Simple Marker symbol     | x [^5]                   |
| Picture Marker Symbol    | x [^6]                   |
| Arrow Marker Symbol      | x [^7]                   |

### Line symbols

| Symbol type              | Supported                                 |
| ------------------------ | ----------------------------------------- |
| Cartographic line symbol | x                        |
| Hash line symbol         | x                        |
| Marker line symbol       | x                        |
| Picture line symbol      | x [^8]                   |
| Simple line symbol       | x                        |

### Polygon symbols

| Symbol type              | Supported                                 |
| ------------------------ | ----------------------------------------- |
| Line fill symbol         | x                        |
| Marker fill symbol       | x                        |
| Picture fill symbol      | x [^9]                   |
| Simple fill symbol       | x                        |

### Labeling

| Symbol type              | Supported                                 |
| ------------------------ | ----------------------------------------- |
| Halo                     | x                        |
| Multiple fields labeling | x [^10]                  |
| Rotation                 | x                        |

Raster layers
-------------

### Raster layer renderers

| Symbol type              | Supported                                 |
| ------------------------ | ----------------------------------------- |
| Unique values            | x                        |
| Classified               | x                        |
| Stretched                | x                        |
| Color map                | x                        |
| Discrete color           | x                        |

[^1]: Default Single Symbol renderer is used

[^2]: The symbols are processed, but only the background color is used
    to create the fill.

[^3]: Only for GeoServer SLD. The Chart API in GeoServer must be
    installed.

[^4]: The font (True Type Font) should be available to GeoServer

[^5]: Supported SLD markers: Circle, Square, Cross and X. The Diamond is
    mapped to circle

[^6]: Supported from GeoServer version 2.8 and higher, supported for
    MapServer 6.0.0 and higher

[^7]: These are mapped to an arrow symbol

[^8]: Supported from GeoServer version 2.8 and higher, supported for
    MapServer 6.0.0 and higher

[^9]: Supported from GeoServer version 2.8 and higher, supported for
    MapServer 6.0.0 and higher

[^10]: Only string concatanation expressions supported like:
    `[CITY_NAME] + "(" + [STATE_NAME] + "")"` No programming expressions
    supported.
