import sys

from qgis.core import Qgis

from geocatbridge.utils import meta, feedback
from geocatbridge.ui.errordialog import ErrorDialog


def handleError(errors):
    stacktrace = ''.join(errors).strip()
    main_error = errors[-1]
    bridge_label = feedback.translate(f'{meta.getShortAppName()} version')
    bridge_version = feedback.translate(f'{meta.getLongAppNameWithMinVersion()}')
    version_label = feedback.translate('Python version')
    qgis_label = feedback.translate('QGIS version')
    qgis_version = meta.getCurrentQgisVersion()
    pypath_label = feedback.translate('Python path')
    md_pypaths = '\n'.join('- {}'.format(path) for path in sys.path)

    html_text = f'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
                <html><head></head>
                <body style="font-family:'Segoe UI'; font-size:9.75pt; font-weight:400; margin: 10px">
                <h3>{main_error}</h3>
                <pre>{stacktrace}</pre>
                <p><b>{bridge_label}:</b> {bridge_version}<br>
                <b>{version_label}:</b> {sys.version}<br>
                <b>{qgis_label}:</b> {qgis_version}</p>
                <h4>{pypath_label}:</h4>
                <ul>{"".join(f"<li>{path}</li>" for path in sys.path)}</ul>
                </body></html>'''

    md_text = f"[please include description of what you were doing here]\n\n" \
              f"### {main_error}\n" \
              f"```\n" \
              f"{stacktrace}\n" \
              f"```\n\n" \
              f"**{bridge_label}** {bridge_version}\n" \
              f"**{version_label}** {sys.version}\n" \
              f"**{qgis_label}** {qgis_version}\n\n" \
              f"#### {pypath_label}\n" \
              f"{md_pypaths}"

    dlg = ErrorDialog(html_text, md_text)
    dlg.exec()
