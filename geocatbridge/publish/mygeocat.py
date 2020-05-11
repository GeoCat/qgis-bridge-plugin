import requests

from geocatbridge.publish.geocatlive import GeocatLiveServer
from geocatbridge.utils.gui import execute
from geocatbridge.publish.servers import *


class MyGeoCatClient:
    def __init__(self):
        self.logout()

    def login(self, user):
        try:
            self.user = user
            self.server = GeocatLiveServer(
                "GeoCat Live - " + self.user, self.user, "", ""
            )
            url = "%s/%s" % (GeocatLiveServer.BASE_URL, self.user)
            response = execute(lambda: requests.get(url))
            responsejson = response.json()
            for serv in responsejson["services"]:
                if serv["application"] == "geoserver":
                    self.geoserverUrl = serv["url"] + "/rest"
                    self.geoserverStatus = serv["status"]
                if serv["application"] == "geonetwork":
                    self.geonetworkUrl = serv["url"]
                    self.geonetworkStatus = serv["status"]
        except:
            self.logout()
            raise Exception("Could not log in to GeoCat Live")

    def logout(self):
        self.geoserverUrl = ""
        self.geoserverStatus = ""
        self.geonetworkUrl = ""
        self.geonetworkStatus = ""
        self.user = None
        self.server = None

    def isLoggedIn(self):
        return self.user is not None

    def addLiveServer(self):
        for server in allServers().values():
            if isinstance(server, GeocatLiveServer):
                if server.userid == self.user:
                    return
        addServer(self.server)


client = MyGeoCatClient()
