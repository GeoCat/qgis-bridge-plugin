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
        url = self.api_url() + "/records"
        with open(metadata, "rb") as f:
            data = f.read()
            self.http_request(url, data, "post", headers)

    def delete_metadata(self, uuid):
        #TODO: bucket??
        url = self.api_url() + "/records?uuids=%s&withBackup=true" % uuid
        self.http_request(url, method="delete")

    def me(self):
        url = self.api_url() + "/me"
        ret =  self.http_request(url, headers = {"Accept": "application/json"})
        return ret









