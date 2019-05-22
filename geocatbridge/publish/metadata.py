from qgis.PyQt.QtXml import QDomDocument

def createMetadataXml(layer, metadata):
    doc = QDomDocument()
    layer.exportNamedMetadata(doc)
    return doc.toString()
    #TODO: convert to ISO

def createMetadataXmlFile(layer, metadata):
    filename = tempFilenameInTempFolder("metadata.xml")
    xml = createMetadataXml(layer, metadata)
    with open(filename, "w") as f:
        f.write(xml)
    return filename

def createMetadataMefFile(layer, metadata):
    xml = createMetadataXml(layer, metadata)
    filename = tempFilenameInTempFolder(layer.name() + ".mef")
    z = zipfile.ZipFile(filename, "w")    
    z.writestr("metadata.xml", xml)
    z.close()
    return filename
