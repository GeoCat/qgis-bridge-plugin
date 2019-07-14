import requests

class RequestsNetworkAccessManager():

    def __init__(self, username, password):
        self.client = requests.session()
        self.username = username
        self.password = password
    
    def request(url, method, data=None, headers={}):
        req_method = getattr(self.client, method.lower())
        return req_method(url, headers=headers, data=data, auth=(self.username, self.password))

class Catalog():

    def __init__(self, service_url, network_access_manager):
        self.service_url = service_url.strip("/")
        self.nam = network_access_manager

    def http_request(self, url, data=None, method='get', headers = {}):
        resp = self.nam.request(url, method, data, headers)
        return resp

class GeodataCatalog(Catalog):
	pass

class MetadataCatalog(Catalog):
	pass