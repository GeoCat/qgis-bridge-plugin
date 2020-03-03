# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
import shutil
import zipfile
import json
from collections import defaultdict
import subprocess
import argparse
from enterprise.branding import doBranding

def package(enterprise):
    builddocs()
    package_file = "./geocatbridge.zip"
    suffix = ""
    if enterprise:
        doBranding()
        suffix = "enterprise"
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        make_zip(f, suffix)

def make_zip(zipFile, suffix):
    print("Creating zip...")
    excludes = {"test", "tests", '*.pyc', ".git"}
    docs_dir = "./docs%s/build/latest" % suffix
    src_dir = "./geocatbridge%s" % suffix
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
            relpath = os.path.join("geocatbridge%s" % suffix, "docs", os.path.relpath(root, docs_dir))
            zipFile.write(os.path.join(root,  f), os.path.join(relpath, f))

def sh(commands):
    if isinstance(commands, str):
        commands = commands.split(" ")
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")

def builddocs():
    print("Building docs...")
    cwd = os.getcwd()        
    scriptPath = os.path.join(cwd, "docs")
    buildFolder = os.path.join(scriptPath, "build")
    os.chdir(scriptPath)
    sh("python builddocs.py --output %s --current --clean" % buildFolder)
    os.chdir(cwd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build documentation.')    
    parser.add_argument('--Enterprise', dest='clean', action='store_true', help='Build with Enterprise branding')
    args = parser.parse_args()
    package(args.enterprise)
    package(True)