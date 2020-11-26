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

    html_text = f'''<h3>{main_error}</h3>
                <pre>{stacktrace}</pre><br>
                <b>{version_label}</b> {sys.version}<br>
                <b>{qgis_label}</b> {Qgis().version()} ({Qgis().releaseName()} {Qgis.QGIS_DEV_VERSION})<br>
                <h4>{pypath_label}</h4>
                <ul>{"".join(f"<li>{path}</li>" for path in sys.path)}</ul>'''

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
