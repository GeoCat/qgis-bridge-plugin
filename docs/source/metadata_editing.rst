.. _MetadataEditing:

Metadata Editing
================

Bridge provides a basic editor for metadata properties to create
ISO19139 metadata records. The purpose of this editor is to easily
complete a minimal subset of required metadata elements.

-   Title
-   Abstract
-   ISO topic category
-   Keywords
-   Metadata contact
-   Data contact
-   Access constraints (used for data license)
-   Use constraints (also known as Fees)
-   Metadata language

When publishing metadata to GeoNetwork, Bridge will
convert the metadata to ISO19139 format.

You can edit the metadata fields directly or click on the buttons beside each parameter to open the QGIS metadata editor.

Preview metadata
----------------

To show a preview of the metadata of the selected layer, click on the |previewmetadata| button

.. |previewmetadata| image:: ./img/preview_metadata_button.png

You will see the metadata in a new dialog

.. image:: ./img/metadata_preview.png


Metadata validation
-------------------

Bridge can use QGIS built-in validation tools and display the result of metadata validation. Click on the |validatemetadata| button to validate your metadata.

.. |validatemetadata| image:: ./img/validation.png 

After validation a dialog with validation results is displayed.

.. image:: ./img/schematron_metadata.png
