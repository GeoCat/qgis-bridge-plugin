import argparse
import os
import shutil
import subprocess

"""
This script generates documentation based on the content of the current
repo, for the current master HEAD (if run with '--version dev' argument or
without arguments), all available tags (if run with the '--version all' argument), 
or the latest available tag (if the '--version stable' argument is used)

The script file should be located in the documentation folder (with sphinx files
under ./source folder)

You can specify the output folder in which docs are to be produced, by using the 
'--output [path]' argument. If not used, the documentation will be created under the 
./build folder. 
"""

NAME = "bridge4"
DOC_BRANCH_PREFIX = "docs-"


def sh(commands):
    if isinstance(commands, str):
        commands = commands.split()
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")


def clean(folder):
    print("Cleaning output folder")
    shutil.rmtree(folder, ignore_errors=True)


def builddocs(addmaster, folder):
    refs = getrefs()
    if addmaster:
        buildref("master", folder, "latest")
    for ref in refs:
        buildref(ref, folder)


def getrefs():
    refs = []
    branches = sh("git branch").splitlines()
    for line in branches:
        name = line.split(" ")[-1]
        if name.startswith(DOC_BRANCH_PREFIX):
            foldername = name.split(DOC_BRANCH_PREFIX)[-1]
            refs.append(foldername)
    return refs


def buildref(ref, folder, versionname=None):
    print(f"Building project '{NAME}' at version '{versionname or ref}'...")
    if ref is not None:
        sh(f"git checkout {ref}")
    sourcedir = os.path.join(os.getcwd(), "source")
    builddir = os.path.join(folder, versionname or ref)
    if os.path.exists(builddir):
        shutil.rmtree(builddir)
    os.makedirs(builddir)
    sh(f"sphinx-build -a {sourcedir} {builddir}")


def main():
    parser = argparse.ArgumentParser(description='Build documentation.')
    parser.add_argument('--output', help='Output folder to save documentation')
    parser.add_argument('--clean', dest='clean', action='store_true', help='Clean output folder')
    parser.add_argument('--addmaster', dest='addmaster', action='store_true', help='Build also master branch')
    parser.set_defaults(clean=False)

    args = parser.parse_args()

    folder = args.output or os.path.join(os.getcwd(), "build")

    if args.clean:
        clean(folder)

    builddocs(args.addmaster, folder)
    sh("git checkout master")


if __name__ == "__main__":
    main()
