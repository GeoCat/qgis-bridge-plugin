# -*- coding: utf-8 -*-

import fnmatch
import os
import subprocess
import zipfile


def package():
    builddocs()
    package_file = "./geocatbridge.zip"
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        make_zip(f)


def make_zip(zip_file, suffix=""):
    print("Creating zip...")
    excludes = {"test", "tests", '*.pyc', ".git"}
    docs_dir = "./docs%s/build/latest" % suffix
    src_dir = "./geocatbridge%s" % suffix

    def filter_excludes(file_list):
        for fn in file_list:
            if not any([fnmatch.fnmatch(fn, e) for e in excludes]):
                yield fn

    for root, dirs, files in os.walk(src_dir):
        for f in filter_excludes(files):
            relpath = os.path.relpath(root, '.')
            zip_file.write(os.path.join(root, f), os.path.join(relpath, f))
        filter_excludes(dirs)

    for root, dirs, files in os.walk(docs_dir):
        for f in files:
            relpath = os.path.join("geocatbridge%s" % suffix, "docs", os.path.relpath(root, docs_dir))
            zip_file.write(os.path.join(root, f), os.path.join(relpath, f))


def sh(commands):
    if isinstance(commands, str):
        commands = commands.split(" ")
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")


def builddocs():
    print("Building docs...")
    cwd = os.getcwd()
    script_path = os.path.join(cwd, "docs")
    build_folder = os.path.join(script_path, "build")
    os.chdir(script_path)
    sh("python builddocs.py --output %s --current --clean" % build_folder)
    os.chdir(cwd)


if __name__ == "__main__":
    package()
