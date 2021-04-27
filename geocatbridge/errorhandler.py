import sys

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import Qgis

from geocatbridge.ui.errordialog import ErrorDialog


def handleError(errors):

    stacktrace = ''.join(errors).strip()
    main_error = errors[-1]
    version_label = QCoreApplication.translate('Python', 'Python version:')
    qgis_label = QCoreApplication.translate('Python', 'QGIS version:')
    pypath_label = QCoreApplication.translate('Python', 'Python path:')
    md_pypaths = '\n'.join('- {}'.format(path) for path in sys.path)

    html_text = f'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
                <html><head></head>
                <body style="font-family:'Segoe UI'; font-size:9.75pt; font-weight:400; margin: 10px">
                <h3>{main_error}</h3>
                <pre>{stacktrace}</pre>
                <p><b>{version_label}</b> {sys.version}<br>
                <b>{qgis_label}</b> {Qgis().version()} ({Qgis().releaseName()} {Qgis.QGIS_DEV_VERSION})</p>
                <h4>{pypath_label}</h4>
                <ul>{"".join(f"<li>{path}</li>" for path in sys.path)}</ul>
                </body></html>'''

    md_text = f"[please insert description of what you were doing here]\n\n" \
              f"### {main_error}\n" \
              f"```\n" \
              f"{stacktrace}\n" \
              f"```\n\n" \
              f"**{version_label}** {sys.version}\n" \
              f"**{qgis_label}** {Qgis().version()} ({Qgis().releaseName()} {Qgis.QGIS_DEV_VERSION})\n\n" \
              f"#### {pypath_label}\n" \
              f"{md_pypaths}"

    dlg = ErrorDialog(html_text, md_text)
    dlg.exec()
