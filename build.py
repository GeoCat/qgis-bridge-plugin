# -*- coding: utf-8 -*-

import fnmatch
import os
import subprocess
import zipfile
import argparse
from pathlib import Path

OUTPUT_DIRNAME = 'build'


def package():
    ap = argparse.ArgumentParser(description='Package GeoCat Bridge plugin')
    ap.add_argument('--filename', help='ZIP file name', default='GeoCat_Bridge')
    ap.add_argument('--docs', help='Add to include docs in the ZIP', default=False, action='store_true')
    ns = ap.parse_args()

    if ns.docs:
        builddocs()
    file_name = f'{ns.filename}.zip'
    output_dir = Path(f'./{OUTPUT_DIRNAME}').resolve()
    os.makedirs(output_dir, exist_ok=True)
    package_file = output_dir / file_name
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        make_zip(f, include_docs=ns.docs)


def make_zip(zip_file, suffix="", include_docs=True):
    print("Creating ZIP for GeoCat Bridge plugin...")
    file_excludes = {'*.pyc', "*.git", "*.log"}
    dir_excludes = {"test", "tests", "_debug", "debug", "build", "__pycache__"}
    src_dir = "./geocatbridge%s" % suffix

    def filter_excludes(file_list):
        for fn in file_list:
            if not any([fnmatch.fnmatch(fn, e) for e in file_excludes]):
                yield fn

    for root, dirs, files in os.walk(src_dir):
        if any(p in dir_excludes for p in Path(root).parts):
            continue
        for f in filter_excludes(files):
            relpath = os.path.relpath(root, '.')
            dstpath = os.path.join(relpath, f)
            print(f'\t{dstpath}')
            zip_file.write(os.path.join(root, f), dstpath)

    if include_docs:
        docs_dir = "./docs%s/build/latest" % suffix
        for root, dirs, files in os.walk(docs_dir):
            for f in files:
                relpath = os.path.join("geocatbridge%s" % suffix, "docs", os.path.relpath(root, docs_dir))
                zip_file.write(os.path.join(root, f), os.path.join(relpath, f))
    print(f'Successfully created ZIP file {zip_file.filename}')


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
