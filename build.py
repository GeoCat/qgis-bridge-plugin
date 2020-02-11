# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
import shutil
import zipfile
import json
from collections import defaultdict
import subprocess

def package():
    builddocs()
    package_file = "./geocatbridge.zip"
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        make_zip(f)

def make_zip(zipFile):
    excludes = {"test", "tests", '*.pyc', ".git"}
    src_dir = "./geocatbridge"
    docs_dir = "./docs/build/latest"
    exclude = lambda p: any([fnmatch.fnmatch(p, e) for e in excludes])
    def filter_excludes(files):
        if not files: return []
        # to prevent descending into dirs, modify the list in place
        for i in range(len(files) - 1, -1, -1):
            f = files[i]
            if exclude(f):
                files.remove(f)
        return files

    for root, dirs, files in os.walk(src_dir):
        for f in filter_excludes(files):
            relpath = os.path.relpath(root, '.')
            zipFile.write(os.path.join(root,  f), os.path.join(relpath, f))
        filter_excludes(dirs)

    for root, dirs, files in os.walk(docs_dir):
        for f in files:
            relpath = os.path.join("geocatbridge", "docs", os.path.relpath(root, docs_dir))
            zipFile.write(os.path.join(root,  f), os.path.join(relpath, f))

def sh(commands):
    if isinstance(commands, str):
        commands = commands.split(" ")
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")

def builddocs():
    cwd = os.getcwd()        
    scriptPath = os.path.join(cwd, "docs")
    buildFolder = os.path.join(scriptPath, "build")
    os.chdir(scriptPath)
    sh("python builddocs.py --output %s --version dev --clean" % buildFolder)
    os.chdir(cwd)

if __name__ == "__main__":
    package()