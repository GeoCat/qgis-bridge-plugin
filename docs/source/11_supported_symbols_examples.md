# Supported Styles

The following map images have been generated using a custom ArcPy script
that uses the Bridge CLI to publish a number of MXD\'s. The script uses
ArcPy to generate an image for each layer in ArcMap and uses the WMS
GetMap request to generate an image for MapServer and GeoServer. The
script uses the Bridge managed workspace mode, so for every MXD
published Bridge will create a new workspace in GeoServer.

## Raster


### Continuous Raster

Symbology for continuous raster, one example of a classified symbology
and several stretched symbologies.

#### Layer \'Classified\'

Classified raster symbology.

![Layer \'Classified\' rendered in ArcGIS](./img_supported/continuous_raster_Classified_arcgis.png)

![Layer \'Classified\' rendered in MapServer](./img_supported/continuous_raster_Classified_mapserver.png)

![Layer \'Classified\' rendered in GeoServer](./img_supported/continuous_raster_Classified_geoserver.png)

#### Layer \'Stretched - histogram equalize\'

Histogram equalize stretched raster symbology.

![Layer \'Stretched - histogram equalize\' rendered in ArcGIS](./img_supported/continuous_raster_Stretched___histogram_equalize_arcgis.png)

![Layer \'Stretched - histogram equalize\' rendered in MapServer](./img_supported/continuous_raster_Stretched___histogram_equalize_mapserver.png)

![Layer \'Stretched - histogram equalize\' rendered in GeoServer](./img_supported/continuous_raster_Stretched___histogram_equalize_geoserver.png)

#### Layer \'Stretched - min max\'

Min-Max stretched raster symbology.

![Layer \'Stretched - min max\' rendered in ArcGIS](./img_supported/continuous_raster_Stretched___min_max_arcgis.png)

![Layer \'Stretched - min max\' rendered in MapServer](./img_supported/continuous_raster_Stretched___min_max_mapserver.png)

![Layer \'Stretched - min max\' rendered in GeoServer](./img_supported/continuous_raster_Stretched___min_max_geoserver.png)

#### Layer \'Stretched - standard deviation\'

Standard deviation stretched raster symbology.

![Layer \'Stretched - standard deviation\' rendered in ArcGIS](./img_supported/continuous_raster_Stretched___standard_deviation_arcgis.png)

![Layer \'Stretched - standard deviation\' rendered in MapServer](./img_supported/continuous_raster_Stretched___standard_deviation_mapserver.png)

![Layer \'Stretched - standard deviation\' rendered in GeoServer](./img_supported/continuous_raster_Stretched___standard_deviation_geoserver.png)

### Discrete Raster

Discrete raster symbologies.

#### Layer \'Internal color map\'

Symbology using internal color map of GeoTIFF file.

![Layer \'Internal color map\' rendered in ArcGIS](./img_supported/discrete_raster_Internal_color_map_arcgis.png)

![Layer \'Internal color map\' rendered in MapServer](./img_supported/discrete_raster_Internal_color_map_mapserver.png)

![Layer \'Internal color map\' rendered in GeoServer](./img_supported/discrete_raster_Internal_color_map_geoserver.png)

#### Layer \'Unique values - grouped values\'

Symbology using grouped unique values.

![Layer \'Unique values - grouped values\' rendered in ArcGIS](./img_supported/discrete_raster_Unique_values___grouped_values_arcgis.png)

![Layer \'Unique values - grouped values\' rendered in MapServer](./img_supported/discrete_raster_Unique_values___grouped_values_mapserver.png)

![Layer \'Unique values - grouped values\' rendered in GeoServer](./img_supported/discrete_raster_Unique_values___grouped_values_geoserver.png)

#### Layer \'Unique value - attribute table\'

Symbology using raster attribute table for classification. Also supports
grouping of values.

![Layer \'Unique value - attribute table\' rendered in ArcGIS](./img_supported/discrete_raster_Unique_value___attribute_table_arcgis.png)

![Layer \'Unique value - attribute table\' rendered in MapServer](./img_supported/discrete_raster_Unique_value___attribute_table_mapserver.png)

![Layer \'Unique value - attribute table\' rendered in GeoServer](./img_supported/discrete_raster_Unique_value___attribute_table_geoserver.png)

#### Layer \'Discrete color\'

Symbology using discrete color.

![Layer \'Discrete color\' rendered in ArcGIS](./img_supported/discrete_raster_Discrete_color_arcgis.png)

![Layer \'Discrete color\' rendered in MapServer](./img_supported/discrete_raster_Discrete_color_mapserver.png)

![Layer \'Discrete color\' rendered in GeoServer](./img_supported/discrete_raster_Discrete_color_geoserver.png)

### RGB Raster

Raster with red, green and blue band. Bridge exports the rasters with
the band sequence changed to the server. This way it is not required to
style the layers at the server.

RGB stretch is not supported by Bridge, because the support for this is
limited in GeoServer and MapServer.

The contrast can be enhanced in MapServer by applying the following to
the layer element:

``` python
PROCESSING "SCALE=AUTO"
```

The contrast can be enhanced in GeoServer by setting the following in the SLD:

``` python
<ChannelSelection>
  <RedChannel>
    <SourceChannelName>1</SourceChannelName>
     <ContrastEnhancement>
        <GammaValue>2</GammaValue>
     </ContrastEnhancement>
  </RedChannel>
  <GreenChannel>
    <SourceChannelName>2</SourceChannelName>
    <ContrastEnhancement>
        <GammaValue>2</GammaValue>
     </ContrastEnhancement>
  </GreenChannel>
  <BlueChannel>
    <SourceChannelName>3</SourceChannelName>
    <ContrastEnhancement>
        <GammaValue>2</GammaValue>
     </ContrastEnhancement>    
  </BlueChannel>
</ChannelSelection>
```

#### Layer \'Natural earth - bgr\'

False colour palette; red, blue, green:green, red, blue.

![Layer \'Natural earth - bgr\' rendered in ArcGIS](./img_supported/rgb_raster_Natural_earth___bgr_arcgis.png)

![Layer \'Natural earth - bgr\' rendered in MapServer](./img_supported/rgb_raster_Natural_earth___bgr_mapserver.png)

![Layer \'Natural earth - bgr\' rendered in GeoServer](./img_supported/rgb_raster_Natural_earth___bgr_geoserver.png)

#### Layer \'Natural earth - rgb\'

True color palette.

![Layer \'Natural earth - rgb\' rendered in ArcGIS](./img_supported/rgb_raster_Natural_earth___rgb_arcgis.png)

![Layer \'Natural earth - rgb\' rendered in MapServer](./img_supported/rgb_raster_Natural_earth___rgb_mapserver.png)

![Layer \'Natural earth - rgb\' rendered in GeoServer](./img_supported/rgb_raster_Natural_earth___rgb_geoserver.png)

Vector
------

### Character Symbol

Character symbol used for point in layer Cities marker line symbol with
character symbol used for Rivers and a marker fill symbol with character
symbol used for Countries.

#### Layer \'Cities\'

Point layer with a character marker symbol.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/character_symbol_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/character_symbol_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/character_symbol_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with a character marker line symbol.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/character_symbol_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/character_symbol_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/character_symbol_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with a character marker fill symbol.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/character_symbol_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/character_symbol_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/character_symbol_Countries_geoserver.png)

### Label Symbol

Label symbology.Layer Cities uses a multivariate classification for
symbols and labels. Layer Rivers uses a classification for the labels
and layer Countries are all labelled the same way, in upper case.

#### Layer \'Cities\'

Multivariate classification, on both SCALERANK and ADM0CAP attribute.
Labels are using the same classification.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/label_symbol_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/label_symbol_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/label_symbol_Cities_geoserver.png)

#### Layer \'Rivers\'

Single symbol with classifed labels, when specifying label classes it is
required for MapServer to create a class that is not labelled, otherwise
the features without labels are not showing up in MapServer.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/label_symbol_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/label_symbol_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/label_symbol_Rivers_geoserver.png)

#### Layer \'Countries\'

Features all labelled the same way, labels in uppercase.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/label_symbol_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/label_symbol_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/label_symbol_Countries_geoserver.png)

### Line Fill Symbol

Line fill symbol, also known as \"hatch fill\".

#### Layer \'Arbitrary angle line fill\'

Hatch fill symbol with lines under an angle of 10 degrees.

![Layer \'Arbitrary angle line fill\' rendered in ArcGIS](./img_supported/line_fill_symbol_Arbitrary_angle_line_fill_arcgis.png)

![Layer \'Arbitrary angle line fill\' rendered in MapServer](./img_supported/line_fill_symbol_Arbitrary_angle_line_fill_mapserver.png)

![Layer \'Arbitrary angle line fill\' rendered in GeoServer](./img_supported/line_fill_symbol_Arbitrary_angle_line_fill_geoserver.png)

#### Layer \'Single line fill\'

Hatch fill symbol with single line fill.

![Layer \'Single line fill\' rendered in ArcGIS](./img_supported/line_fill_symbol_Single_line_fill_arcgis.png)

![Layer \'Single line fill\' rendered in MapServer](./img_supported/line_fill_symbol_Single_line_fill_mapserver.png)

![Layer \'Single line fill\' rendered in GeoServer](./img_supported/line_fill_symbol_Single_line_fill_geoserver.png)

#### Layer \'Overlapping line fill\'

Hatch fill symbol with overlapping line fills.

![Layer \'Overlapping line fill\' rendered in ArcGIS](./img_supported/line_fill_symbol_Overlapping_line_fill_arcgis.png)

![Layer \'Overlapping line fill\' rendered in MapServer](./img_supported/line_fill_symbol_Overlapping_line_fill_mapserver.png)

![Layer \'Overlapping line fill\' rendered in GeoServer](./img_supported/line_fill_symbol_Overlapping_line_fill_geoserver.png)

### Line Symbols

Symbology with line symbols on polyline layers.

#### Layer \'Marker line\'

Symbology with marker line symbol.

![Layer \'Marker line\' rendered in ArcGIS](./img_supported/line_symbols_Marker_line_arcgis.png)

![Layer \'Marker line\' rendered in MapServer](./img_supported/line_symbols_Marker_line_mapserver.png)

![Layer \'Marker line\' rendered in GeoServer](./img_supported/line_symbols_Marker_line_geoserver.png)

#### Layer \'Cartographic line\'

Symbology with cartographic line symbol.

![Layer \'Cartographic line\' rendered in ArcGIS](./img_supported/line_symbols_Cartographic_line_arcgis.png)

![Layer \'Cartographic line\' rendered in MapServer](./img_supported/line_symbols_Cartographic_line_mapserver.png)

![Layer \'Cartographic line\' rendered in GeoServer](./img_supported/line_symbols_Cartographic_line_geoserver.png)

#### Layer \'Hash line\'

Symbology with hash line symbol.

![Layer \'Hash line\' rendered in ArcGIS](./img_supported/line_symbols_Hash_line_arcgis.png)

![Layer \'Hash line\' rendered in MapServer](./img_supported/line_symbols_Hash_line_mapserver.png)

![Layer \'Hash line\' rendered in GeoServer](./img_supported/line_symbols_Hash_line_geoserver.png)

### Picture Symbol

Symbology containing picture symbols.

#### Layer \'Cities\'

Point layer with picture marker symbol.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/picture_symbol_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/picture_symbol_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/picture_symbol_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with picture line symbol.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/picture_symbol_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/picture_symbol_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/picture_symbol_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with picture fill symbol.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/picture_symbol_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/picture_symbol_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/picture_symbol_Countries_geoserver.png)

### Quantities Graduated

Symbology with graduated colors, no normalization.

#### Layer \'Cities\'

Point layer with graduated color symbology.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/quantities_graduated_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/quantities_graduated_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/quantities_graduated_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with graduated color symbology.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/quantities_graduated_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/quantities_graduated_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/quantities_graduated_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with graduated color symbology.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/quantities_graduated_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/quantities_graduated_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/quantities_graduated_Countries_geoserver.png)

### Quantities Graduated Normalized

Symbology with graduated colors normalized.

#### Layer \'Cities\'

Point layer with graduated color symbology normalized.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/quantities_graduated_normalized_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/quantities_graduated_normalized_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/quantities_graduated_normalized_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with graduated color symbology normalized.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/quantities_graduated_normalized_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/quantities_graduated_normalized_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/quantities_graduated_normalized_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with graduated color symbology normalized.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/quantities_graduated_normalized_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/quantities_graduated_normalized_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/quantities_graduated_normalized_Countries_geoserver.png)

### Quantities Graduated Symbols

Symbology with graduated size symbols. Features are divided in classes,
each class has its own symbol size.

#### Layer \'Cities\'

Point layer with graduated size symbols normalized.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/quantities_graduated_symbols_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/quantities_graduated_symbols_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/quantities_graduated_symbols_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with graduated size symbol, not normalized.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/quantities_graduated_symbols_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/quantities_graduated_symbols_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/quantities_graduated_symbols_Rivers_geoserver.png)

### Rotation Symbol

Symbology with rotated symbols. ArcGIS knows two types of symbology
GeoGraphic and Arithmic.

Geographic rotates labels from north in a clockwise direction, while
Arithmetic rotates labels from east in a counterclockwise direction.

#### Layer \'Geographic rotation\'

Point layer with point symbols rotated geographically.

![Layer \'Geographic rotation\' rendered in ArcGIS](./img_supported/rotation_symbol_Geographic_rotation_arcgis.png)

![Layer \'Geographic rotation\' rendered in MapServer](./img_supported/rotation_symbol_Geographic_rotation_mapserver.png)

![Layer \'Geographic rotation\' rendered in GeoServer](./img_supported/rotation_symbol_Geographic_rotation_geoserver.png)

#### Layer \'Arithmic rotation\'

Point layer with point symbols rotated arithmically

![Layer \'Arithmic rotation\' rendered in ArcGIS](./img_supported/rotation_symbol_Arithmic_rotation_arcgis.png)

![Layer \'Arithmic rotation\' rendered in MapServer](./img_supported/rotation_symbol_Arithmic_rotation_mapserver.png)

![Layer \'Arithmic rotation\' rendered in GeoServer](./img_supported/rotation_symbol_Arithmic_rotation_geoserver.png)

### Simple Marker Symbol

Symbology with simple marker symbols. Simple marker symbols are a
fast-drawing set of basic glyph patterns with optional mask.

#### Layer \'Cities\'

Point layer with a simple marker symbol.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/simple_marker_symbol_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/simple_marker_symbol_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/simple_marker_symbol_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with a simple marker line symbol.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/simple_marker_symbol_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/simple_marker_symbol_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/simple_marker_symbol_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with a simple marker fill symbol.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/simple_marker_symbol_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/simple_marker_symbol_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/simple_marker_symbol_Countries_geoserver.png)

### Stacked Symbol

Symbology composed from different layers of symbols.

#### Layer \'Rivers\'

Stacked line symbol.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/stacked_symbol_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/stacked_symbol_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/stacked_symbol_Rivers_geoserver.png)

#### Layer \'Cities\'

Stacked point symbol.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/stacked_symbol_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/stacked_symbol_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/stacked_symbol_Cities_geoserver.png)

#### Layer \'Countries\'

Stacked fill symbol.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/stacked_symbol_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/stacked_symbol_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/stacked_symbol_Countries_geoserver.png)

### Unique Value

Symbology with a unique value classifiier.

#### Layer \'Cities\'

Point layer with a unique value classifiier.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/unique_value_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/unique_value_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/unique_value_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with a unique value classifiier.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/unique_value_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/unique_value_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/unique_value_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with a unique value classifiier.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/unique_value_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/unique_value_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/unique_value_Countries_geoserver.png)

### Unique Value Many Fields

Symbology with a unique multivalue classifiier.

#### Layer \'Cities\'

Point layer with a unique multivalue classifiier.

![Layer \'Cities\' rendered in ArcGIS](./img_supported/unique_value_many_fields_Cities_arcgis.png)

![Layer \'Cities\' rendered in MapServer](./img_supported/unique_value_many_fields_Cities_mapserver.png)

![Layer \'Cities\' rendered in GeoServer](./img_supported/unique_value_many_fields_Cities_geoserver.png)

#### Layer \'Rivers\'

Line layer with a unique multivalue classifiier.

![Layer \'Rivers\' rendered in ArcGIS](./img_supported/unique_value_many_fields_Rivers_arcgis.png)

![Layer \'Rivers\' rendered in MapServer](./img_supported/unique_value_many_fields_Rivers_mapserver.png)

![Layer \'Rivers\' rendered in GeoServer](./img_supported/unique_value_many_fields_Rivers_geoserver.png)

#### Layer \'Countries\'

Polygon layer with a unique multivalue classifiier.

![Layer \'Countries\' rendered in ArcGIS](./img_supported/unique_value_many_fields_Countries_arcgis.png)

![Layer \'Countries\' rendered in MapServer](./img_supported/unique_value_many_fields_Countries_mapserver.png)

![Layer \'Countries\' rendered in GeoServer](./img_supported/unique_value_many_fields_Countries_geoserver.png)
