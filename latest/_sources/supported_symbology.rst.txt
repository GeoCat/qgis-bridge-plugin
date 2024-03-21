.. _Symbology:

Supported Symbology
###################

|short_name| uses the Python `bridgestyle library <https://github.com/GeoCat/bridge-style>`_ to export QGIS symbology into other formats such as SLD (used when uploading to GeoServer), MapServer files, or Mapbox GL.

Below you can find a list of supported elements that should be correctly converted from QGIS to SLD, along with additional information about the limitations of the conversion between these two formats.


Common settings
===============

This section describes general elements that are common to most types of layers and symbologies.

Drawing order (symbol levels)
-----------------------------

You can use `symbol levels <https://docs.qgis.org/3.4/en/docs/user_manual/working_with_vector/vector_properties.html#id95>`_ in QGIS to define the order in which to render the symbol layers, which should be correctly converted to z-levels in SLD.

Size units
----------

Size values can be used in millimeters, pixels, points, or real world meters. In this last case, expressions cannot be used, only fixed values.

However, please note that it's safer to use pixels instead of millimeters (which are the default unit in QGIS), since pixel is the assumed unit for formats like SLD, so no conversion is needed.

.. _SupportedExpressions:

Expressions
-----------

`Expressions <https://docs.qgis.org/3.4/en/docs/pyqgis_developer_cookbook/expressions.html>`_ are supported wherever QGIS allows to use data-defined values. They must be created using QGIS expression language (Python custom functions are not supported). Not all available functions in QGIS can be used, since there's no equivalent for all of them in GeoServer. The following QGIS functions can be used::

		radians, degrees, floor, ceil, area, buffer, centroid, 
		if, bounds, distance, convex_hull, end_point, start_point, 
		x, y, concat, substr, lower, upper, replace, exterior_ring, 
		intersects, overlaps, touches, within, relates, crosses, 
		disjoint, geom_from_wkt, perimeter, union, acos, asin, atan,
		atan2, sin, cos, tan, ln, title, translate, min, max,
		to_int, to_real, to_string

| Some function parameters accept expressions, but this is not always supported by |short_name| when converting to SLD.
| This applies to the following parameter types:

- Colors
- Parameters selected from drop down lists
- Offset values
- Size measures in units different than pixels or mm (i.e. if you are using map units relative to the current map scale)

Blending modes
--------------

Blending modes are supported at the layer level.


Vector Layers
=============

The supported elements for styling vector layers are described below.

Supported renderers
-------------------

The following renderers are supported for vector layers:

`Single symbol <https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/vector_properties.html#single-symbol-renderer>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: img/singlesymbolrenderer.png

`Categorized <https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/vector_properties.html#categorized-renderer>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: img/categorizedrenderer.png

`Graduated <https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/vector_properties.html#graduated-renderer>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: img/graduatedrenderer.png

`Heatmap <https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/vector_properties.html#heatmap-renderer>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following limitations apply:

- Radius must be expressed in pixels
- Expressions are not supported for the ``weight`` parameter


`Rule-based <https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/vector_properties.html#rule-based-renderer>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: img/rulebasedrenderer.png

Nested rules are supported. The ``ELSE`` rule is also supported, but it might behave incorrectly in the SLD version if the layer has labeling.
QGIS considers labeling to be a separate part of the symbology, while SLD considers it as just another symbolizer.

To find out more about the supported expressions that can be used in rule filters, see the :ref:`SupportedExpressions` section.


Supported point symbology
-------------------------

The following symbol layer types are supported for rendering points:

Simple marker
^^^^^^^^^^^^^

.. figure:: img/simplemarker.png

Below is a list of the parameters that are supported:

* Size
* Fill Color
* Stroke Color
* Stroke style
* Stroke width
* Join style
* Rotation
* Offset

SVG marker
^^^^^^^^^^

.. figure:: img/svgmarker.png

Below is a list of the parameters that are supported:

* Size
* Fill Color
* Stroke Color
* Stroke width
* Rotation
* Offset
* SVG image

Raster image marker
^^^^^^^^^^^^^^^^^^^

.. figure:: img/rastermarker.png

Below is a list of the parameters that are supported:

* Size
* Rotation
* File

Font marker
^^^^^^^^^^^

.. figure:: img/fontmarker.png

Below is a list of the parameters that are supported:

* Size
* Fill Color
* Font

Geometry generator
^^^^^^^^^^^^^^^^^^


Supported line symbology
------------------------

The following symbol layer types are supported for rendering lines:

Simple line
^^^^^^^^^^^

.. figure:: img/simpleline.png

Below is a list of the parameters that are supported:

* Color
* Stroke width
* Stroke style
* Join style
* Cap style
* Offset

Marker line
^^^^^^^^^^^

.. figure:: img/markerline.png

Below is a list of the parameters that are supported:

- Marker placement: only ``with interval`` mode is supported
- Offset along line

As marker, you can use simple markers, SVG markers and raster image markers, with the restrictions mentioned in the corresponding section about supported symbology for point symbols.

Geometry generator
^^^^^^^^^^^^^^^^^^


Supported polygon symbology
---------------------------

The following symbol layer types are supported for rendering polygons:

Simple fill
^^^^^^^^^^^

.. figure:: img/simplefill.png

Below is a list of the parameters that are supported:

* Size
* Fill Color
* Fill style: only ``solid, no brush, horizontal, vertical, cross``
* Stroke Color
* Stroke style
* Stroke width
* Join style
* Rotation

Point pattern fill
^^^^^^^^^^^^^^^^^^

.. figure:: img/pointpatternfill.png

Below is a list of the parameters that are supported:

* Horizontal distance
* Vertical distance

As marker, you can use simple markers, SVG markers and raster image markers, with the restrictions mentioned in the corresponding section about supported symbology for point symbols.

Line pattern fill
^^^^^^^^^^^^^^^^^

.. figure:: img/linepatternfill.png

Below is a list of the parameters that are supported:

* Rotation: Angle will be rounded to a multiple of 45 degrees
* Spacing

Outline: Simple line
^^^^^^^^^^^^^^^^^^^^

See the section on supported symbology for simple lines

Outline: Marker line
^^^^^^^^^^^^^^^^^^^^

.. figure:: img/fillmarkeroutline.png

See the section on supported symbology for marker lines

Geometry generator
^^^^^^^^^^^^^^^^^^


Labeling
==========

The following labeling modes are supported for vector layer labels.

- No labels
- `Single labels <https://docs.qgis.org/3.4/en/docs/user_manual/working_with_vector/vector_properties.html#id98>`_
- `Rule-based labeling <https://docs.qgis.org/3.4/en/docs/user_manual/working_with_vector/vector_properties.html#id111>`_

Text options
------------

The following options from the :guilabel:`Text` group of parameters are supported:

- Size
- Font family
- Rotation

	
Buffer options
--------------

.. figure:: img/labelhalo.png

The following options from the :guilabel:`Buffer` group of parameters are supported:

- Size
- Color
- Opacity

	
Background options
------------------

.. figure:: img/labelbackground.png

The following options from the :guilabel:`Background` group of parameters are supported:

- Size X
- Size Y
- Size type
- Shape type
- Stroke color
- Fill color

	
Placement options
-----------------

The only supported :guilabel:`Placement` option is :guilabel:`Offset from centroid`, using the following parameters

- Quadrant
- Offset
- Rotation


Raster Layers
=============

The supported elements for styling raster layers are detailed in this section.

Supported renderers
-------------------

- Single band gray
- Single band color
- Single band pseudo color
- Multi-band color
- Paletted
