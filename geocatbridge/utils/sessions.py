from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth


class TokenizedSession(requests.Session):

    def __init__(self, token_url, token_param="XSRF-TOKEN"):
        """
        Initializes a new tokenized requests Session.

        :param token_url:       The URL from which to obtain a token.
        :param token_param:     The name of the token parameter to read from the session cookie.
        """
        super().__init__()
        self._token = None
        self._token_param = token_param
        self._token_url = urlparse(token_url).geturl()

    def setTokenHeader(self, user, pwd, header_name="X-XSRF-TOKEN"):
        """
        Gets a token (if not available yet) and sets its value in the session header.

        :param user:            The basic authentication user name.
        :param pwd:             The basic authentication password.
        :param header_name:     The name of the token header to set (if not "X-XSRF-TOKEN").
        """
        self.auth = HTTPBasicAuth(user, pwd)
        if self._token is None:
            self._token = self.getToken()
        self.headers.update({header_name: self._token})

    def getToken(self):
        """ Requests a session token using POST and reads its value from the cookie. """
        self.post(self._token_url)
        return self.cookies.get(self._token_param)
