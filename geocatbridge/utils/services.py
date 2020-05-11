from qgis.PyQt.QtCore import QSettings


def addServicesForGeodataServer(name, url, authcfg):
    s = QSettings()

    s.setValue("qgis/WMS/{0}/password".format(name), "")
    s.setValue("qgis/WMS/{0}/username".format(name), "")
    s.setValue("qgis/WMS/{0}/authcfg".format(name), authcfg)
    s.setValue("qgis/connections-wms/{0}/dpiMode".format(name), 7)
    s.setValue("qgis/connections-wms/{0}/ignoreAxisOrientation".format(name), False)
    s.setValue("qgis/connections-wms/{0}/ignoreGetFeatureInfoURI".format(name), False)
    s.setValue("qgis/connections-wms/{0}/ignoreGetMapURI".format(name), False)
    s.setValue("qgis/connections-wms/{0}/invertAxisOrientation".format(name), False)
    s.setValue("qgis/connections-wms/{0}/referer".format(name), "")
    s.setValue("qgis/connections-wms/{0}/smoothPixmapTransform".format(name), False)
    s.setValue("qgis/connections-wms/{0}/url".format(name), url + "/wms")

    s.setValue("qgis/WFS/{0}/username".format(name), "")
    s.setValue("qgis/WFS/{0}/password".format(name), "")
    s.setValue("qgis/connections-wfs/{0}/referer".format(name), "")
    s.setValue("qgis/connections-wfs/{0}/url".format(name), url + "/wfs")
    s.setValue("qgis/WFS/{0}/authcfg".format(name), authcfg)
