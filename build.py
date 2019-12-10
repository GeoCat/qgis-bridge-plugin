# -*- coding: utf-8 -*-

import os
import sys
import fnmatch
import shutil
import zipfile
import json
from collections import defaultdict

def package():
    builddocs()
    package_file = "./geocatbridge.zip"
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        make_zip(f)

def make_zip(zipFile):
    excludes = {"test", "tests", '*.pyc', ".git"}
    src_dir = "./geocatbridge"
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


if __name__ == "__main__":
    package()