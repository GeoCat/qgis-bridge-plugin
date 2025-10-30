FORMS = views/publishreportdialog.ui \
        views/publishwidget.ui \
        views/connectionswidget.ui \
        views/errordialog.ui

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
          views/errordialog.py \
          views/publishwidget.py \
          views/progressdialog.py \
          views/publishreportdialog.py \
          views/connectionswidget.py \
          utils/l10n.py

TRANSLATIONS = i18n/bridge_de.ts \
               i18n/bridge_es.ts \
               i18n/bridge_nl.ts
