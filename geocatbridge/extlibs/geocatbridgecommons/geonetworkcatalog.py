from .catalog import MetadataCatalog     

class GeoNetworkCatalog(MetadataCatalog):

    def login_url(self):
        return self.service_url + "/signin"

    def api_url(self):
        return self.service_url + "/srv/api/0.1"

    def metadata_exists(self, uuid):
        try:
            self.get_metadata(uuid)
            return True
        except:
            return False

    def get_metadata(self, uuid):
        url = self.api_url() + "/records/" + uuid
        return self.http_request(url)

    def publish_metadata(self, metadata):
        headers = {"accept": "application/json"}
        url = self.api_url() + "/records?uuidProcessing=OVERWRITE"        
        with open(metadata,'rb') as f:
            files = {'file': (metadata, f, 'application/zip', {'Expires': '0'})}        
            r = self.nam.session.post(url, files=files, headers = headers)
        r.raise_for_status()
        js = r.json()
        if "errors" in r and r['errors']:
            raise Exception(r['errors'])       

    def delete_metadata(self, uuid):
        #TODO: bucket??
        url = self.api_url() + "/records?uuids=%s" % uuid
        self.http_request(url, method="delete")

    def me(self):
        url = self.api_url() + "/me"
        ret =  self.http_request(url, headers = {"Accept": "application/json"})
        return ret









