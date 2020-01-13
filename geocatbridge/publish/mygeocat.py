import requests

from geocatbridge.publish.geocatlive import GeocatLiveServer
from geocatbridge.utils.gui import execute
from geocatbridge.publish.servers import *

class MyGeoCatClient():

    BASE_URL = "https://live-services.geocat.net/geocat-live/api/1.0/order"

    def __init__(self):
        self.logout()

    def login(self, user, password):
        try:
            self.user = user
            self.password = password
            self.server = GeocatLiveServer("GeoCat Live - " + self.user, self.user, "", "")
            url = "%s/%s" % (self.BASE_URL, self.user)
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
        self.password = None
        self.server = None

    def isLoggedIn(self):
        return self.user is not None and self.password is not None

    def addLiveServer(self):
        for server in allServers().values():
            if isinstance(server, GeocatLiveServer):
                if server.userid == self.user:
                    return        
        addServer(self.server)

client = MyGeoCatClient()