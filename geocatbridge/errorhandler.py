import sys
from qgis.core import Qgis
from qgis.PyQt.QtCore import QCoreApplication
from geocatbridge.ui.errordialog import ErrorDialog

_errors = []

def handleError(errorList):

    txt = u'''<h3>{main_error}</h3>
<pre>
{error}
</pre>
<br>
<b>{version_label}</b> {num}
<br>
<b>{qgis_label}</b> {qversion} {qgisrelease}, {devversion}
<br>
<h4>{pypath_label}</h4>
<ul>
{pypath}
</ul>'''

    error = ''
    for s in errorList:
        error += s.decode('utf-8', 'replace') if hasattr(s, 'decode') else s
    error = error.replace('\n', '<br>')

    main_error = errorList[-1].decode('utf-8', 'replace') if hasattr(errorList[-1], 'decode') else errorList[-1]

    version_label = QCoreApplication.translate('Python', 'Python version:')
    qgis_label = QCoreApplication.translate('Python', 'QGIS version:')
    pypath_label = QCoreApplication.translate('Python', 'Python Path:')
    txt = txt.format(main_error=main_error,
                     error=error,
                     version_label=version_label,
                     num=sys.version,
                     qgis_label=qgis_label,
                     qversion=Qgis.QGIS_VERSION,
                     qgisrelease=Qgis.QGIS_RELEASE_NAME,
                     devversion=Qgis.QGIS_DEV_VERSION,
                     pypath_label=pypath_label,
                     pypath=u"".join(u"<li>{}</li>".format(path) for path in sys.path))

    txt = txt.replace('  ', '&nbsp; ')  # preserve whitespaces for nicer output
    _errors.append(error)
    dlg = ErrorDialog(txt)
    dlg.exec()
    
