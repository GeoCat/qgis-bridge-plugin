import sys

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

    md_text = f"[please include a description of what you were doing here]\n\n" \
              f"### {main_error}\n" \
              f"```\n" \
              f"{stacktrace}\n" \
              f"```\n\n" \
              f"**{bridge_label}** {bridge_version}\n" \
              f"**{version_label}** {sys.version}\n" \
              f"**{qgis_label}** {qgis_version}\n\n" \
              f"#### {pypath_label}\n" \
              f"{md_pypaths}"

    dlg = ErrorDialog(md_text)
    dlg.exec()
