import os
import shutil
import subprocess
import argparse

'''
This script generates documentation based on the content of the current
repo, for the current master HEAD (if run with '--version dev' argument or
without arguments), all available tags (if run with the '--version all' argument), 
or the latest available tag (if the '--version stable' argument is used)

The script file should be located in the documentation folder (with sphinx files
under ./source folder)

You can specify the output folder in which docs are to be produced, by using the 
'--output [path]' argument. If not used, the documentation will be created under the 
./build folder. 
'''

NAME = "bridge4"
DOC_BRANCH_PREFIX = "docs-"

def sh(commands):
    if isinstance(commands, str):
        commands = commands.split(" ")
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")

def clean(folder):
    print("Cleaning output folder")
    shutil.rmtree(folder, ignore_errors=True)

def builddocs(current, folder):
    refs = getrefs()
    if current:
        buildref(None, folder, "latest")
    else:
        for ref in refs:
            buildref(ref, folder)

def getrefs():
    refs = []
    branches = sh("git branch -r").splitlines()
    for line in branches:
        fullname = line.strip().split(" ")[0]
        name = fullname.split("/")[-1]
        if name.startswith(DOC_BRANCH_PREFIX):          
            refs.append(fullname)
    return refs

def buildref(ref, folder, versionname=None):
    versionname = versionname or ref.split("/")[-1].split(DOC_BRANCH_PREFIX)[-1]
    print("Building project '%s' at version '%s'..." % (NAME, versionname))
    if ref is not None:
        sh("git checkout {}".format(ref))
    sourcedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source")
    builddir = os.path.join(folder, versionname)
    if os.path.exists(builddir):
        shutil.rmtree(builddir)
    os.makedirs(builddir)
    sh("sphinx-build -a {} {}".format(sourcedir, builddir))

def main():
    parser = argparse.ArgumentParser(description='Build documentation.')
    parser.add_argument('--output', help='Output folder to save documentation')
    parser.add_argument('--clean', dest='clean', action='store_false', help='Clean output folder')
    parser.add_argument('--current', dest='current', action='store_false', help='Build only current branch')

    args = parser.parse_args()

    folder = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")

    if args.clean:
        clean(folder)

    builddocs(args.current, folder)

if __name__ == "__main__":
    main()
