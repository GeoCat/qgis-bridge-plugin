# -*- coding: utf-8 -*-

"""
***************************************************************************
    oauth2.py
    ---------------------
    Date                 : March 2017
    Copyright            : (C) 2017 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************

Utility functions to handle OAuth2 authentication configuration

"""

__author__ = 'Alessandro Pasotti'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

import json
from qgis.core import (QgsApplication,
                       QgsAuthManager,
                       QgsAuthMethodConfig)


AUTHCFG_ID = "conect1"  # Standard name for connect OAuth2 configuration
AUTHCFG_NAME = "Boundless OAuth2 API"


def auth_manager():
    return QgsApplication.authManager()


def oauth2_supported():
    """Check wether current QGIS installation has all requirements to
    consume BCS services, current checks
    - OAuth2 auth plugin is available
    """
    return 'OAuth2' in auth_manager().authMethodsKeys()

def get_oauth_authcfg(authcfg_id=AUTHCFG_ID):
    """Check if the given authcfg_id (or the default) exists, and if it's valid
    OAuth2, return the configuration or None"""
    # Handle empty strings
    if not authcfg_id:
        authcfg_id = AUTHCFG_ID
    configs = auth_manager().availableAuthMethodConfigs()
    if authcfg_id in configs \
            and configs[authcfg_id].isValid() \
            and configs[authcfg_id].method() == 'OAuth2':
        return configs[authcfg_id]
    return None

def setup_oauth(username, password, basemaps_token_uri, authcfg_id=AUTHCFG_ID, authcfg_name=AUTHCFG_NAME):
    """Setup oauth configuration to access the BCS API,
    return authcfg_id on success, None on failure
    """
    cfgjson = {
     "accessMethod" : 0,
     "apiKey" : "",
     "clientId" : "",
     "clientSecret" : "",
     "configType" : 1,
     "grantFlow" : 2,
     "password" : password,
     "persistToken" : False,
     "redirectPort" : '7070',
     "redirectUrl" : "",
     "refreshTokenUrl" : "",
     "requestTimeout" : '30',
     "requestUrl" : "",
     "scope" : "",
     "state" : "",
     "tokenUrl" : basemaps_token_uri,
     "username" : username,
     "version" : 1
    }

    if authcfg_id not in auth_manager().availableAuthMethodConfigs():
        authConfig = QgsAuthMethodConfig('OAuth2')
        authConfig.setId(authcfg_id)
        authConfig.setName(authcfg_name)
        authConfig.setConfig('oauth2config', json.dumps(cfgjson))
        if auth_manager().storeAuthenticationConfig(authConfig):
            return authcfg_id
    else:
        authConfig = QgsAuthMethodConfig()
        auth_manager().loadAuthenticationConfig(authcfg_id, authConfig, True)
        authConfig.setName(authcfg_name)
        authConfig.setConfig('oauth2config', json.dumps(cfgjson))
        if auth_manager().updateAuthenticationConfig(authConfig):
            return authcfg_id
    return None
