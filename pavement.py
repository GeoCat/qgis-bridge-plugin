# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
import shutil
import zipfile
import json
from collections import defaultdict

# this pulls in the sphinx target
from paver.easy import *
from paver.doctools import html

options(
    plugin = Bunch(
        name = 'geocatbridge',
        ext_libs = path('geocatbridge/extlibs'),
        source_dir = path('geocatbridge'),
        package_dir = path('.'),
        tests = ['test', 'tests'],
        excludes = [
            '*.pyc',
            ".git"
        ]
    ),

    sphinx = Bunch(
        docroot = path('docs'),
        sourcedir = path('docs/source'),
        builddir = path('docs/build')
    )
)

@task
@cmdopts([
    ('clean', 'c', 'clean out dependencies first'),
])
def setup():
    clean = getattr(options, 'clean', False)
    ext_libs = options.plugin.ext_libs
    if clean:
        ext_libs.rmtree()
    ext_libs.makedirs()
    reqs = read_requirements()
    os.environ['PYTHONPATH']=ext_libs.abspath()
    for req in reqs:
        sh('pip3 install -U -t %(ext_libs)s %(dep)s' % {
            'ext_libs' : ext_libs.abspath(),
            'dep' : req
        })

@task
def install(options):
    '''install plugin to qgis'''
    plugin_name = options.plugin.name
    src = path(__file__).dirname() / plugin_name
    if os.name == 'nt':
        dst = path('~/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins').expanduser() / plugin_name
    elif sys.platform == 'darwin':
        dst = path('~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins').expanduser() / plugin_name
    else:
        dst = path('~/.local/share/QGIS/QGIS3/profiles/default/python/plugins').expanduser() / plugin_name
    src = src.abspath()
    dst = dst.abspath()
    if not hasattr(os, 'symlink'):
        dst.rmtree()
        src.copytree(dst)
    elif not dst.exists():
        src.symlink(dst)

def read_requirements():
    '''return a list of runtime and list of test requirements'''
    lines = open('requirements.txt').readlines()
    lines = [ l for l in [ l.strip() for l in lines] if l ]
    return [l for l in lines if l[0] != '#']

@task
@cmdopts([
    ('tests', 't', 'Package tests with plugin')
])
def package(options):
    '''create package for plugin'''
    builddocs(options)
    package_file = options.plugin.package_dir / ('%s.zip' % options.plugin.name)
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        if not hasattr(options.package, 'tests'):
            options.plugin.excludes.extend(options.plugin.tests)
        make_zip(f, options)


def make_zip(zipFile, options):
    excludes = set(options.plugin.excludes)

    src_dir = options.plugin.source_dir
    exclude = lambda p: any([fnmatch.fnmatch(p, e) for e in excludes])
    def filter_excludes(files):
        if not files: return []
        # to prevent descending into dirs, modify the list in place
        for i in xrange(len(files) - 1, -1, -1):
            f = files[i]
            if exclude(f):
                files.remove(f)
        return files

    for root, dirs, files in os.walk(src_dir):
        for f in filter_excludes(files):
            relpath = os.path.relpath(root, '.')
            zipFile.write(path(root) / f, path(relpath) / f)
        filter_excludes(dirs)

    for root, dirs, files in os.walk(options.sphinx.builddir):
        for f in files:
            relpath = os.path.join(options.plugin.name, "docs", os.path.relpath(root, options.sphinx.builddir))
            zipFile.write(path(root) / f, path(relpath) / f)

