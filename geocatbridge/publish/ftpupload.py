import ftplib
import os


# Code adopted from the ftp exporter included in the qgis2web plugin, by Nyall Dawson
def uploadFolder(folder, host, port, remote_folder, username, password):
    ftp = ftplib.FTP()
    try:
        ftp.connect(host, port)
    except ftplib.all_errors as e:
        raise Exception(f"Could not connect to FTP server at '{host}': {e}")

    try:
        ftp.login(username, password)
    except ftplib.all_errors as e:
        raise Exception(f"Login failed for user '{username}': {e}")

    def cwdAndCreate(p):
        """
        Recursively changes directory to an FTP target,
        creating new folders as required.
        """
        if not p:
            return
        try:
            ftp.cwd(p)
        except ftplib.all_errors:
            parent, base = os.path.split(p)
            cwdAndCreate(parent)
            if base:
                ftp.mkd(base)
                ftp.cwd(base)

    cwdAndCreate(remote_folder)

    def uploadPath(path):
        files = os.listdir(path)
        os.chdir(path)
        for f in files:
            current_path = os.path.join(path, f)
            if os.path.isfile(current_path):
                fh = open(f, 'rb')
                ftp.storbinary(f"STOR {f}", fh)
                fh.close()
            elif os.path.isdir(current_path):
                try:
                    ftp.mkd(f)
                except ftplib.all_errors:
                    pass
                ftp.cwd(f)
                if not uploadPath(current_path):
                    return False
        ftp.cwd('..')
        os.chdir('..')

    uploadPath(folder)
    ftp.close()
