FORMS = ui/publishreportdialog.ui \
        ui/publishwidget.ui \
        ui/serverconnectionswidget.ui \
        ui/errordialog.ui

SOURCES = plugin.py \
          process/algorithm.py \
          process/provider.py \
          publish/exporter.py \
          publish/metadata.py \
          publish/tasks.py \
          servers/manager.py \
          servers/views/geonetwork.py \
          servers/views/geoserver.py \
          servers/views/mapserver.py \
          servers/views/postgis.py \
          ui/errordialog.py \
          ui/publishwidget.py \
          ui/progressdialog.py \
          ui/publishreportdialog.py \
          ui/serverconnectionswidget.py \
          utils/l10n.py

TRANSLATIONS = i18n/bridge_de.ts \
               i18n/bridge_es.ts \
               i18n/bridge_nl.ts
