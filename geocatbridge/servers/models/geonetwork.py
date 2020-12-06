import webbrowser
import requests

from geocatbridge.utils.sessions import TokenizedSession
from geocatbridge.publish.metadata import saveMetadata
from geocatbridge.servers.bases import MetaCatalogServerBase
from geocatbridge.servers.views.geonetwork import GeoNetworkWidget
from geocatbridge.utils.enum_ import LabeledIntEnum


class GeoNetworkProfiles(LabeledIntEnum):
    """ Container class for GeoNetwork profile constants. """
    DEFAULT = 'Default'
    INSPIRE = 'INSPIRE'
    DUTCH = 'Dutch Geography'


class GeonetworkServer(MetaCatalogServerBase):

    def __init__(self, name, auth_id="", url="", profile=GeoNetworkProfiles.DEFAULT, node="srv"):
        """
        Creates a new GeoNetwork model instance.

        :param name:    Descriptive server name (given by the user)
        :param auth_id: QGIS Authentication ID (optional)
        :param url:     GeoNetwork base URL
        :param profile: GeoNetwork metadata profile type (optional)
        :param node:    GeoNetwork node name (default = srv)
        """

        super().__init__(name, auth_id, url)
        try:
            self.profile = GeoNetworkProfiles[profile]
        except IndexError:
            raise ValueError(f"'{profile}' is not a valid GeoNetwork profile")
        self.node = node
        self._session = TokenizedSession(f"{self.baseUrl}/eng/catalog.signin")

    def getSettings(self) -> dict:
        return {
            'name':  self.serverName,
            'authid': self.authId,
            'url': self.baseUrl,
            'profile': self.profile,
            'node': self.node
        }

    @classmethod
    def getWidgetClass(cls) -> type:
        return GeoNetworkWidget

    @classmethod
    def getServerTypeLabel(cls) -> str:
        return 'GeoNetwork'

    def publishLayerMetadata(self, layer, wms, wfs, layer_name):
        mef_filename = saveMetadata(layer, None, self.apiUrl, wms, wfs, layer_name)
        self.publishMetadata(mef_filename)

    def testConnection(self):
        try:
            self.me()
        except Exception as e:
            self.logWarning(e)
            return False
        return True

    @property
    def apiUrl(self):
        return f"{self.baseUrl}/{self.node}/api"

    @property
    def xmlServicesUrl(self):
        return f"{self.baseUrl}/{self.node}/eng"

    def metadataExists(self, uuid):
        try:
            self.getMetadata(uuid)
            return True
        except requests.HTTPError:
            return False

    def getMetadata(self, uuid):
        url = self.metadataUrl(uuid)
        return self.request(url, session=self._session)

    def publishMetadata(self, metadata):
        """ Writes new metadata (does not update existing metadata). """
        url = self.apiUrl + "/records"
        headers = {"Accept": "application/json"}

        with open(metadata, "rb") as f:
            files = {'file': f}
            r = self.request(url, "post", files=files, headers=headers, session=self._session)
            r.raise_for_status()

    def deleteMetadata(self, uuid):
        url = self.metadataUrl(uuid)
        self.request(url, "delete", session=self._session)

    def me(self):
        url = f"{self.apiUrl}/info?type=me"
        return self.request(url, session=self._session)

    def metadataUrl(self, uuid):
        return f"{self.apiUrl}/records/{uuid}"

    def openMetadata(self, uuid):
        webbrowser.open_new_tab(self.metadataUrl(uuid))
