from .server import MetadataCatalog

class RequestsTokenNetworkAccessManager()
    def __init__(self, username, password, login_url):
        self.client = requests.session()        
        self.login_url = login_url
        self.token = None
    
    def request(url, method, data=None, headers={}):
    	if self.token is None:
    		self.get_token()
        req_method = getattr(self.client, method.lower())
        headers["X-XSRF-TOKEN"] = self.token
        return req_method(url, headers=headers, data=data)

    def get_token(self):    	
    	#TODO: set token
    	pass

class GeoNetworkCatalog(MetadataCatalog):

	def metadata_exists(self, name):
		pass

	def get_metadata(self, name):
		pass

	def publish_metadata(self, metadata):
		headers = {"accept": "application/json"}
		url = self.service_url + "/api/0.1/records"
        with open(metadata, "rb") as f:
            data = f.read()
			self.request(url, "post", data, header)

	def delete_metadata(self, name):
		#TODO: bucket??
		url = self.service_url + "/api/0.1/records?uuids=%s&withBackup=true" % name
		self.request(url, "delete")









