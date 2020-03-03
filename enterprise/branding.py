import os
import shutil
import fnmatch

root = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(root, "geocatbridge")
DST_DIR = os.path.join(root, "geocatbridgeenterprise")
DOCS_SRC_DIR = os.path.join(root, "docs")
DOCS_DST_DIR = os.path.join(root, "docsenterprise")

class ReplaceAction():

    def __init__(self, old, new):
        self.old = old
        self.new = new

    def change(self, text):
        text = text.replace(self.old, self.new)
        return text

    def run(self):
        for fpath in self.files():
            with open(fpath) as f:
                text = f.read()
            text = self.change(text)
            with open(fpath, "w") as f:
                f.write(text)

    def files(self):
        files = []
        for folder in [DST_DIR, DOCS_DST_DIR]:
            for root, dirnames, filenames in os.walk(folder):
                for ext in ["*.txt", "*.rst" , "*.py", "*.ui"]:
                    for filename in fnmatch.filter(filenames, ext):
                        files.append(os.path.join(root, filename))
        return files

brandingActions = [
                    ReplaceAction(" Bridge ", " Bridge Enterprise "),
                    ReplaceAction("GeoCat Bridge", "GeoCat Bridge Enterprise"),
                    ReplaceAction("geocatbridge.", "geocatbridgeenterprise."),
                ]

def doBranding():
    if os.path.exists(DST_DIR):
        shutil.rmtree(DST_DIR)
    shutil.copytree(SRC_DIR, DST_DIR)

    if os.path.exists(DOCS_DST_DIR):
        shutil.rmtree(DOCS_DST_DIR)
    shutil.copytree(DOCS_SRC_DIR, DOCS_DST_DIR)

    for action in brandingActions:
        action.run()
