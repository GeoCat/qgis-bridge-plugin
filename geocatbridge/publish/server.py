from qgiscommons2.network.networkaccessmanager import NetworkAccessManager

class Server():

    def __init__(self, name, service_url, authid):
        self.authid = authid
        self.name = name
        self.service_url = service_url.strip("/")
        self.nam = NetworkAccessManager(self.authid)

    def http_request(self, url, data=None, method='get', headers = {}):
        resp, content = self.nam.request(url, method, data, headers)
        return resp

class GeodataServer(Server):
	pass

class MetadataServer(Server):
	pass