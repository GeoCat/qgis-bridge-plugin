# -*- coding: utf-8 -*-

import os
import zipfile
import argparse
from pathlib import Path
from fnmatch import fnmatch

from shared import get_rootdir
from geocatbridge.utils.meta import getVersion

OUTPUT_DIRNAME = 'build'


def package():
    ap = argparse.ArgumentParser(description='Package GeoCat Bridge plugin')
    ap.add_argument('--filename', help='ZIP file name', default=f'GeoCat_Bridge_v{getVersion()}')
    ns = ap.parse_args()

    file_name = f'{ns.filename}.zip'
    output_dir = get_rootdir() / OUTPUT_DIRNAME
    os.makedirs(output_dir, exist_ok=True)
    package_file = output_dir / file_name
    with zipfile.ZipFile(package_file, 'w', zipfile.ZIP_DEFLATED) as f:
        make_zip(f)


def make_zip(zip_file):
    print('Creating ZIP for GeoCat Bridge plugin...')
    file_excludes = {'*.pyc', '*.git*', '*.log', '*.bkp'}
    dir_excludes = {'test', 'tests', '_debug', '__pycache__'}  # folder names inside ./geocatbridge
    root_dir = get_rootdir()
    src_dir = root_dir / 'geocatbridge'
    gpltxt = root_dir / 'LICENSE'

    def filter_excludes(file_list):
        for fn in file_list:
            if not any([fnmatch(fn, e) for e in file_excludes]):
                yield fn

    if gpltxt.is_file():
        # Include license file from repo root in package if it exists
        dstpath = Path(src_dir.name) / gpltxt.name
        print(f'\t{dstpath}')
        zip_file.write(gpltxt.resolve(), dstpath)
    else:
        raise FileNotFoundError(f'❌ Required LICENSE file is missing!')

    for root, dirs, files in os.walk(src_dir):
        if any(p in dir_excludes for p in Path(root).parts):
            continue
        for f in filter_excludes(files):
            relpath = os.path.relpath(root, '.')
            dstpath = os.path.join(relpath, f)
            print(f'\t{dstpath}')
            zip_file.write(os.path.join(root, f), dstpath)

    print(f'✅ Successfully created ZIP file {zip_file.filename}')


if __name__ == '__main__':
    package()
