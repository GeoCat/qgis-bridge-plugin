# -*- coding: utf-8 -*-

import os
import subprocess
import zipfile
import argparse
from pathlib import Path
from fnmatch import fnmatch

from geocatbridge.utils.meta import getVersion

OUTPUT_DIRNAME = 'build'


def package():
    ap = argparse.ArgumentParser(description='Package GeoCat Bridge plugin')
    ap.add_argument('--filename', help='ZIP file name', default=f'GeoCat_Bridge_v{getVersion()}')
    ns = ap.parse_args()

    file_name = f'{ns.filename}.zip'
    output_dir = Path(f'./{OUTPUT_DIRNAME}').resolve()
    os.makedirs(output_dir, exist_ok=True)
    package_file = output_dir / file_name
    with zipfile.ZipFile(package_file, "w", zipfile.ZIP_DEFLATED) as f:
        make_zip(f)


def make_zip(zip_file):
    print("Creating ZIP for GeoCat Bridge plugin...")
    file_excludes = {'*.pyc', "*.git*", "*.log"}
    dir_excludes = {"test", "tests", "_debug", "debug", "build", "__pycache__", ".github"}
    src_dir = f"./geocatbridge"
    gpltxt = Path('./LICENSE')
    readme = Path('./README.md')

    def filter_excludes(file_list):
        for fn in file_list:
            if not any([fnmatch(fn, e) for e in file_excludes]):
                yield fn

    if gpltxt.is_file():
        # Include license file from repo root in package if it exists
        dstpath = src_dir / gpltxt
        print(f'\t{dstpath}')
        zip_file.write(gpltxt.resolve(), dstpath)
    else:
        raise FileNotFoundError(f"Required LICENSE file is missing!")

    if readme.is_file():
        # Include README file from repo root in package if it exists
        dstpath = src_dir / readme
        print(f'\t{dstpath}')
        zip_file.write(readme.resolve(), dstpath)

    for root, dirs, files in os.walk(src_dir):
        if any(p in dir_excludes for p in Path(root).parts):
            continue
        for f in filter_excludes(files):
            relpath = os.path.relpath(root, '.')
            dstpath = os.path.join(relpath, f)
            print(f'\t{dstpath}')
            zip_file.write(os.path.join(root, f), dstpath)

    print(f'Successfully created ZIP file {zip_file.filename}')


def sh(commands):
    if isinstance(commands, str):
        commands = commands.split(" ")
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")


if __name__ == "__main__":
    package()
