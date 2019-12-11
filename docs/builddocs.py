import os
import shutil
import subprocess
import argparse

'''
This script generates documentation based on the content of the current
repo, for the most recent tag (if run without arguments), all available tags 
(if run with the '--version all' argument), or the current master HEAD (if the 
'--version dev' argument is used)

The script file should be located in the documentation folder (with sphinx files
under ./source folder)
 
If the '--deploy' argument is used, it adds the built documents to the corresponding 
folder in the central GeoCat documentation site.

When the '--deploy' argument is not used, the documentation is added under the 
./build folder.

The '-all' argument is not compatible with the '--deploy' argument.
'''

NAME = "bridge"
DOCS_REPO = "https://github.com/volaya/geocat-documentation.git"

def sh(commands):
    if isinstance(commands, str):
        commands = commands.split(" ")
    out = subprocess.Popen(commands, stdout=subprocess.PIPE)
    stdout, stderr = out.communicate()
    return stdout.decode("utf-8")

def central_docs_path():
    cwd = os.getcwd()
    tmpDir = os.path.join(cwd, 'tmp')
    if not os.path.exists(tmpDir):
        os.mkdir(tmpDir)
    repopath = os.path.join(tmpDir, "geocat-documentation")
    return repopath

def fetch_central_repo():
    cwd = os.getcwd()    
    print ("\nFetching central documentation...")
    repopath = central_docs_path()
    if os.path.exists(repopath):
        os.chdir(repopath)            
        #sh("git checkout master")
        sh("git pull")            
    else:
        sh("git clone {} {}".format(DOCS_REPO, repopath))
    os.chdir(cwd)

def builddocs(version, deploy):
    if deploy:
        fetch_central_repo()
    if version == "dev":
        buildref("latest", "master", deploy)
    else:
        refs = getrefs()
        if refs:
            if version == "stable":
                refs = refs[:1]
            for refname, ref in refs:
                buildref(refname, ref, deploy)

def getrefs():
    refs = []
    try:
        tags = sh("git show-ref --tags").splitlines()
        for line in tags:
            ref, tag = line.split(" ")
            refs.append((tag.replace("refs/tags/", ""), ref))
    except:
        pass # in case no tags exist yet
    return refs

def buildref(refname, ref, deploy):
    print("Building project '%s' at version '%s'..." % (NAME, refname)) 
    sh("git checkout -f {}".format(ref))
    sourcedir = os.path.join(os.getcwd(), "source")
    if deploy:
        builddir = os.path.join(central_docs_path(), NAME, refname)
    else:
        builddir = os.path.join(os.getcwd(), "build")
    if os.path.exists(builddir):
        shutil.rmtree(builddir)
    os.makedirs(builddir)
    sh("pip3 install --user sphinx")
    sh("pip3 install --user recommonmark")
    sh("pip3 install --user sphinx-markdown-tables")
    sh("sphinx-build -a {} {}".format(sourcedir, builddir))
    if deploy:
        deploydocs(refname)

def deploydocs(refname):
    cwd = os.getcwd()
    os.chdir(central_docs_path())
    sh('git add .')
    sh(['git', 'commit', '-am' '"added/updated docs for %s(%s)"' % (NAME, refname)])
    sh("git push")
    os.chdir(cwd)

def main():
    parser = argparse.ArgumentParser(description='Build and deploy documentation.')
    parser.add_argument('--version',
                        help='Version to build',
                        choices=["all", "stable", "dev"],
                        default="stable")
    parser.add_argument('--deploy',
                        help='Deploy built docs to server',
                        action="store_true")

    args = parser.parse_args()

    if args.version == "all" and not args.deploy:
        print("'--version all' argument can only be used with '--deploy' argument")
        return
    builddocs(args.version, args.deploy)
    sh("git checkout master")

if __name__ == "__main__":
    main()
