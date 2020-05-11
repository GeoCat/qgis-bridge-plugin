import ftplib

# Code adapted from the ftp exporter included in the qgis2web plugin, by Nyall Dawson
def uploadFolder(folder, host, port, remoteFolder, username, password):
    ftp = ftplib.FTP()
    try:
        ftp.connect(host, port)
    except Exception:
        raise Exception("Could not connect to ftp server.")

    # feedback.showFeedback('Connected!')
    # feedback.showFeedback('Logging in as {}...'.format(self.username))

    try:
        ftp.login(username, password)
    except Exception:
        raise Exception("Login failed for user {}".format(username))

    # feedback.showFeedback('Logged in to {}'.format(self.host))

    def cwdAndCreate(p):
        """
            recursively changes directory to an ftp target,
            creating new folders as required.
            """
        if not p:
            return
        try:
            ftp.cwd(p)
        except Exception:
            parent, base = os.path.split(p)
            cwdAndCreate(parent)
            if base:
                ftp.mkd(base)
                ftp.cwd(base)

    cwdAndCreate(remoteFolder)

    def uploadPath(path):
        files = os.listdir(path)
        os.chdir(path)
        for f in files:
            currentPath = os.path.join(path, f)
            if os.path.isfile(currentPath):
                # feedback.showFeedback('Uploading {}'.format(f))
                fh = open(f, "rb")
                ftp.storbinary("STOR %s" % f, fh)
                fh.close()
            elif os.path.isdir(currentPath):
                # feedback.showFeedback('Creating folder {}'.format(f))
                try:
                    ftp.mkd(f)
                except Exception:
                    pass
                ftp.cwd(f)
                if not uploadPath(currentPath):
                    return False
        ftp.cwd("..")
        os.chdir("..")

    uploadPath(folder)

    # feedback.setCompleted('Upload complete!')
    ftp.close()
