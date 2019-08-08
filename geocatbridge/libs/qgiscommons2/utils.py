import os
import inspect
import qgiscommons2
from pyplugin_installer.installer_data import plugins

def _callerName():
    stack = inspect.stack()
    parentframe = stack[2][0]
    name = []
    module = inspect.getmodule(parentframe)
    name.append(module.__name__)
    if 'self' in parentframe.f_locals:
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':
        name.append( codename )
    del parentframe
    return  ".".join(name)


def _callerPath():
    stack = inspect.stack()
    parentframe = stack[2][0]
    name = []
    module = inspect.getmodule(parentframe)
    return module.__file__

def pluginDetails(namespace):
    plugins.rebuild()
    plugin = plugins.all()[namespace]
    html = '<style>body, table {padding:0px; margin:0px; font-family:verdana; font-size: 1.1em;}</style>'
    html += '<body>'
    html += '<table cellspacing="4" width="100%"><tr><td>'
    html += '<h1>{}</h1>'.format(plugin['name'])
    html += '<h3>{}</h3>'.format(plugin['description'])

    if plugin['about'] != '':
        html += plugin['about'].replace('\n', '<br/>')

    html += '<br/><br/>'

    if plugin['category'] != '':
        html += '{}: {} <br/>'.format(tr('Category'), plugin['category'])

    if plugin['tags'] != '':
        html += '{}: {} <br/>'.format(tr('Tags'), plugin['tags'])

    if plugin['homepage'] != '' or plugin['tracker'] != '' or plugin['code_repository'] != '':
        html += tr('More info:')

        if plugin['homepage'] != '':
            html += '<a href="{}">{}</a> &nbsp;'.format(plugin['homepage'], tr('homepage') )

        if plugin['tracker'] != '':
            html += '<a href="{}">{}</a> &nbsp;'.format(plugin['tracker'], tr('bug_tracker') )

        if plugin['code_repository'] != '':
            html += '<a href="{}">{}</a> &nbsp;'.format(plugin['code_repository'], tr('code_repository') )

        html += '<br/>'

    html += '<br/>'

    if plugin['author_email'] != '':
        html += '{}: <a href="mailto:{}">{}</a>'.format(tr('Author'), plugin['author_email'], plugin['author_name'])
        html += '<br/><br/>'
    elif plugin['author_name'] != '':
        html += '{}: {}'.format(tr('Author'), plugin['author_name'])
        html += '<br/><br/>'

    if plugin['version_installed'] != '':
        ver = plugin['version_installed']
        if ver == '-1':
            ver = '?'

        html += tr('Installed version: {} (in {})<br/>'.format(ver, plugin['library']))

    if plugin['version_available'] != '':
        html += tr('Available version: {} (in {})<br/>'.format(plugin['version_available'], plugin['zip_repository']))

    if plugin['changelog'] != '':
        html += '<br/>'
        changelog = tr('Changelog:<br/>{} <br/>'.format(plugin['changelog']))
        html += changelog.replace('\n', '<br/>')

    html += '<br/><br/>'    
    html += '{}: {} ({} {})<br/>'.format(tr('Version of qgiscommons library'), qgiscommons2.__version__, 
        tr("Located at"), os.path.dirname(qgiscommons2.__file__))

    html += '</td></tr></table>'
    html += '</body>'

    return html


def tr(s):
    return s
