import sys
import platform

from geocatbridge.utils import meta, feedback
from geocatbridge.ui.errordialog import ErrorDialog


def handleError(errors):
    stacktrace = ''.join(errors[1:]).rstrip()
    trace_label = errors[0].strip()
    bridge_label = feedback.translate(f'{meta.getShortAppName()} version')
    bridge_version = feedback.translate(f'{meta.getLongAppNameWithMinVersion()}')
    py_label = feedback.translate('Python version')
    py_version = platform.python_version()
    py_revision = platform.python_revision()
    qgis_label = feedback.translate('QGIS version')
    os_label = feedback.translate('OS version')
    os_version = platform.platform().replace('-', ' ')
    pypath_label = feedback.translate('Python path')
    md_pypaths = '\n'.join('- {}'.format(path) for path in sys.path)
    if py_revision:
        py_version += f' (rev {py_revision})'

    md_text = f"### {trace_label}\n" \
              f"```  \n  \n" \
              f"{stacktrace}\n" \
              f"```\n" \
              f"**{bridge_label}:** {bridge_version}  \n" \
              f"**{qgis_label}:** {meta.getCurrentQgisVersion()}  \n" \
              f"**{os_label}:** {os_version}  \n" \
              f"**{py_label}:** {py_version}  \n" \
              f"### {pypath_label}:\n" \
              f"{md_pypaths}  \n"

    dlg = ErrorDialog(md_text)
    dlg.exec()
