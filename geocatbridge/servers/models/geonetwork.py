import webbrowser
from os import path
from urllib.parse import urlparse
from xml.etree import ElementTree as ETree

import requests
from geocatbridge.utils.layers import BridgeLayer
from qgis.core import (
    QgsProcessingParameterMapLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterAuthConfig
)

from geocatbridge.process.algorithm import BridgeAlgorithm
from geocatbridge.publish.metadata import saveMetadata
from geocatbridge.servers.bases import MetaCatalogServerBase
from geocatbridge.servers.models.gn_profile import GeoNetworkProfiles
from geocatbridge.servers.views.geonetwork import GeoNetworkWidget
from geocatbridge.utils.network import BridgeSession
from geocatbridge.utils.meta import semanticVersion
from geocatbridge.utils import feedback
from geocatbridge.utils.network import TESTCON_TIMEOUT


def parseMe(response: requests.Response) -> bool:
    """ Parses the response from a 'me' request to a GeoNetwork API.
    Returns True if the response was authenticated. """
    try:
        xml = ETree.fromstring(response.text)
        authenticated = xml.find('me').get('authenticated').lower()
    except (TypeError, AttributeError, ETree.ParseError):
        feedback.logError(f'Received invalid response from {response.url}: {response.text}')
        return False
    return authenticated == 'true'


class GeonetworkApiError(Exception):
    """ Error raised when the API returns a HTTP 200, but the response object contains errors. """
    pass


class GeonetworkAuthError(Exception):
    """ Error raised when the sign in process for GeoNetwork failed. """
    pass


class GeonetworkServer(MetaCatalogServerBase):
    profile: GeoNetworkProfiles = GeoNetworkProfiles.DEFAULT
    node: str = "srv"

    def __init__(self, name, authid="", url="", **options):
        """
        Creates a new GeoNetwork model instance.

        :param name:            Descriptive server name (given by the user)
        :param authid:          QGIS Authentication ID (optional)
        :param url:             GeoNetwork base URL
        :param profile:         GeoNetwork metadata profile type (optional)
        :param node:            GeoNetwork node name (default = srv)
        """

        super().__init__(name, authid, url, **options)
        self._session = GeonetworkSession(self.meUrl)

    @classmethod
    def getWidgetClass(cls) -> type:
        return GeoNetworkWidget

    @classmethod
    def getLabel(cls) -> str:
        return 'GeoNetwork'

    def publishLayerMetadata(self, layer: BridgeLayer,
                             wms_url: str = None, wfs_url: str = None, linked_name: str = None):
        mef_filename = saveMetadata(layer, None, self.apiUrl, wms_url, wfs_url, linked_name)
        result = self.publishMetadata(mef_filename)
        self.processApiResult(result)

    def testConnection(self, errors: set):
        msg = f'Could not connect to {self.serverName}'

        # First get GeoNetwork version
        version = self.getVersion() or ''
        if version:
            major, minor = semanticVersion(version)
            if not (major == 3 and minor >= 4):
                if major == 4:
                    errors.add(f'{msg}: {self.getLabel()} version 4 instances are not supported yet')
                else:
                    errors.add(f'{msg}: {self.getLabel()} instances prior to version 3.4 are not supported')
                return False
        else:
            errors.add(f'{msg}: please check URL')
            return False

        # Do an authenticated "me" request
        try:
            result = self.sessionRequest(self.meUrl, timeout=TESTCON_TIMEOUT)
        except GeonetworkAuthError as err:
            self.logError(err)
            result = None
            auth = None
        else:
            auth = parseMe(result)
        if not auth or (result and result.status_code == 401):
            errors.add(f'{msg}: please check credentials')
        return auth

    @property
    def apiUrl(self):
        """ Returns the GeoNetwork REST API base URL. """
        return f"{self.baseUrl}/{self.node}/api"

    @property
    def meUrl(self):
        """ Returns the GeoNetwork 'ME' API endpoint URL. """
        return f"{self.apiUrl}/info?type=me"

    @property
    def signinUrl(self):
        return f"{self.baseUrl}/signin"

    def metadataExists(self, uuid):
        """ Returns True if a metadata record with the given ID exists on GeoNetwork. """
        try:
            self.getMetadata(uuid)
            return True
        except requests.RequestException:
            return False

    def getMetadata(self, uuid):
        """ Retrieves a record by the given ID. """
        url = self.metadataUrl(uuid)
        return self.sessionRequest(url)

    def publishMetadata(self, metadata):
        """ (Over)writes new metadata. """
        url = self.apiUrl + "/records"
        headers = {'Accept': 'application/json'}

        with open(metadata, "rb") as f:
            files = {
                'uuidProcessing': (None, 'OVERWRITE', 'text/plain'),
                'file': (path.basename(metadata), f, 'application/octet-stream')
            }
            result = self.sessionRequest(url, "post", files=files, headers=headers)
        return result

    def deleteMetadata(self, uuid):
        """ Deletes a record by the given ID. """
        url = self.metadataUrl(uuid)
        result = self.sessionRequest(url, "delete")
        self.processApiResult(result)
        return result

    def processApiResult(self, result: requests.Response):
        """ Checks if the GeoNetwork API returned any errors in the response object.
        If it did, a GeonetworkApiError is raised. Otherwise, it only logs the info messages. """
        exceptions = []
        try:
            body = result.json() or {}
        except Exception as err:
            if result.content:
                self.logWarning(f"Failed to parse valid JSON from response '{result.text or ''}': {err}")
            body = {}
        errors = body.get('errors', [])
        infos = body.get('infos', [])
        if len(errors) == len(infos) > 0:
            for i, info in enumerate(infos):
                info_msg = info.get('message', '')
                error_msg = errors[i].get('message')
                if info_msg and error_msg:
                    self.logError(info_msg)
                    exceptions.append(f"{info_msg.replace('Check error for details', '').rstrip('. ')}:"
                                      f"\n\t{error_msg}")
        if exceptions:
            concat_msg = '\r\n'.join(exceptions)
            raise GeonetworkApiError(concat_msg)

    def getVersion(self) -> str:
        """ Retrieve the GeoNetwork version info from the REST API.
        Note that this GET request does not use (nor require) a session.

        :returns:   The current GeoNetwork version string or an empty string if not found.
        """
        url = f"{self.apiUrl}/site/info/build"
        headers = {"Accept": "application/json"}
        try:
            result = self.request(url, headers=headers, timeout=TESTCON_TIMEOUT)
            return result.json().get('version')
        except Exception as err:
            self.logError(f"Failed to retrieve {self.getLabel()} version for '{self.serverName}': {err}")
            return ''

    def metadataUrl(self, uuid):
        """ Returns the metadata REST API url for the given record ID. """
        return f"{self.apiUrl}/records/{uuid}"

    def openMetadata(self, uuid):
        """ Open a browser window and show the metadata for the given record ID. """
        webbrowser.open_new_tab(self.metadataUrl(uuid))

    def sessionRequest(self, url, method='get', **kwargs):
        """ Wrapper for GeoNetwork tokenized session requests. """
        kwargs['session'] = self._session
        if self._session.signIn(*self.getCredentials()):
            return self.request(url, method, **kwargs)
        else:
            raise GeonetworkAuthError(f'{self.getLabel()} user failed to authenticate')

    @classmethod
    def getAlgorithmInstance(cls):
        return GeonetworkAlgorithm()


class GeonetworkAlgorithm(BridgeAlgorithm):
    URL = 'URL'
    AUTHID = 'AUTHID'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterMapLayer(self.INPUT,
                                                         self.tr('Layer')))
        self.addParameter(QgsProcessingParameterString(self.URL,
                                                       self.tr('Server URL'), ''))
        self.addParameter(QgsProcessingParameterAuthConfig(self.AUTHID,
                                                           self.tr('Auth credentials')))

    def name(self):
        return 'publishtogeonetwork'

    def displayName(self):
        return self.tr('Metadata to GeoNetwork')

    def shortDescription(self):
        return self.tr('Publishes metadata to a GeoNetwork server instance')

    def processAlgorithm(self, parameters, context, feedback):
        url = self.parameterAsString(parameters, self.URL, context)
        authid = self.parameterAsString(parameters, self.AUTHID, context)
        layer = BridgeLayer(self.parameterAsLayer(parameters, self.INPUT, context))

        feedback.pushInfo(f'Publishing {layer.name()} metadata to GeoNetwork...')
        try:
            server = GeonetworkServer(GeonetworkServer.__name__, authid, url)
            server.publishLayerMetadata(layer)
        except Exception as err:
            feedback.reportError(err, True)

        return {self.OUTPUT: True}


class GeonetworkSession(BridgeSession):
    COOKIE_TOKEN = 'XSRF-TOKEN'
    HEADER_TOKEN = 'X-XSRF-TOKEN'

    def __init__(self, token_url):
        """
        Initializes a new GeoNetwork HTTP Session with cookie storage and token handling.

        :param token_url:   The URL from which to obtain a XSRF token cookie ("me" endpoint).
        """
        super().__init__()
        self._signin_url, self._token_url = self.getUrls(token_url)

    @staticmethod
    def getUrls(token_url):
        """ Parses the token URL and returns a tuple of (sign in URL, validated token URL). """
        parsed_url = urlparse(token_url)
        inst_name = next(p for p in parsed_url.path.split('/') if p)
        signin_url = f"{parsed_url.scheme}://{parsed_url.netloc}/{inst_name}/signin"
        return signin_url, parsed_url.geturl()

    @property
    def signedIn(self) -> bool:
        """ Returns True if the session is authenticated (i.e. the user has been signed in). """
        headers = {'Accept': 'application/xml'}
        feedback.logInfo(f'GET {self._token_url}')
        result = self.get(self._token_url, headers=headers)
        if result.status_code < 400:
            return parseMe(result)
        # This should not happen (even unauthenticated responses should return a 200), but we have to handle it
        feedback.logError(f'Failed to query {self._token_url}: server returned {result.status_code}')
        return False

    def signIn(self, user: str, pwd: str, refresh_token: bool = False) -> bool:
        """
        Checks if the current session is authenticated. If not, a token is retrieved (if not available yet)
        and its value is set in the session X-XSRF-TOKEN header. Finally, the user will be signed in to GeoNetwork.

        :param user:            The basic authentication user name.
        :param pwd:             The basic authentication password.
        :param refresh_token:   If True (default = False), the token will be refreshed.
        :returns:               True if sign in was successful.
        """
        if GeonetworkSession.HEADER_TOKEN in self.headers and self.signedIn and not refresh_token:
            # We are still signed in: no need to do it again
            return True

        if not (user and pwd):
            return False

        auth = {
            'username': user,
            'password': pwd
        }

        if GeonetworkSession.HEADER_TOKEN not in self.headers or refresh_token:
            # Obtain cookie token if there is none or we want to refresh it
            token = self.getToken()
            if token:
                # Update session headers with an X-XSRF-TOKEN
                self.headers[GeonetworkSession.HEADER_TOKEN] = token

        auth['_csrf'] = self.headers[GeonetworkSession.HEADER_TOKEN]

        headers = {'Accept': 'application/html'}

        feedback.logInfo(f'POST {self._signin_url}')
        # Note: it is **extremely** important to NOT allow redirects here!
        # Disallowing redirects will sign us in successfully and return a 302 (Found).
        # A redirect however will result in a 403 (Access Denied), even with valid credentials.
        result = self.post(self._signin_url, data=auth, headers=headers, allow_redirects=False)

        status = result.status_code
        if status >= 400:
            prefix = f"Failed to sign in to {self._signin_url}"
            if status == 403:
                if not refresh_token:
                    # Retry 1 more time with a refreshed token
                    feedback.logWarning(f"{prefix}: retrying with new token")
                    return self.signIn(user, pwd, True)
                feedback.logError(f"{prefix}: access denied to user '{user}' ({status})")
            elif status == 401:
                feedback.logError(f"{prefix}: user '{user}' not authorized (bad credentials)")
            else:
                feedback.logError(f"{prefix}: server returned {status} (please check server logs)")
            return False

        return True

    def getToken(self):
        """ Requests a session token using POST and reads its value from the cookie. """
        headers = {'Content-Type': 'application/xml'}
        feedback.logInfo(f'POST {self._token_url}')
        # Note: it is expected that this returns a 403
        self.post(self._token_url, headers=headers)
        token = self.cookies.get(GeonetworkSession.COOKIE_TOKEN)
        if not token:
            feedback.logError(f'Did not receive a {GeonetworkSession.COOKIE_TOKEN} cookie!')
        return token
