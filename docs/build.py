import os
import shutil
import subprocess

'''
This script generates the documentation based on the content of this repo,
for all available tags and also for the most recent version.

It adds the built documents to the corresponding folder in the central 
GeoCat documentation repository, adding a new commit to it.

For instance, if there are two tags named 'v1.0' and 'v2.0', 
this script will generate the following tree structure.

|--docs
   |--bridge
      |--v1.0
         |--index.html         
         .
         .
         .
      |--v2.0
         |--index.html         
         .
         .
         .
      |--latest
         |--index.html         
         .
         .
         .

The 'latest' folder is always added and contains the most recent version of the
documentation for a given product (taken from the current master HEAD)
'''

NAME = "bridge"
DOCS_REPO = "https://github.com/volaya/geocat-documentation.git"

def sh(command):
    out = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE)
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
        sh("git checkout master")
        sh("git pull")            
    else:
        sh("git clone {} {}".format(DOCS_REPO, repopath))
    os.chdir(cwd)

def builddocs():          
    refs = getrefs()
    for refname, ref in refs.items():
        buildref(refname, ref)

def getrefs():
    refs = {"latest": "master"}
    try:
        tags = sh("git show-ref --tags").splitlines()
        for line in tags:
            ref, tag = line.split(" ")
            refs[tag.replace("refs/tags/", "")] = ref
    except:
        pass # in case no tags exist yet    
    return refs

def buildref(refname, ref):    
    sh("git checkout -f {}".format(ref))
    sourcedir = os.path.join(os.getcwd(), "source")
    builddir = os.path.join(central_docs_path(), NAME, refname)
    if os.path.exists(builddir):
        shutil.rmtree(builddir)
    os.makedirs(builddir)
    sh("pip install --user sphinx")
    sh("pip install --user recommonmark")
    sh("pip install --user sphinx-markdown-tables")
    sh("sphinx-build -a ./source {}".format(builddir))

def deploy():
    sh('git add .')
    sh('git commit -am update')
    sh("git push")

if __name__ == "__main__":
      fetch_central_repo()
      builddocs()
      deploy()
      sh("git checkout master")
