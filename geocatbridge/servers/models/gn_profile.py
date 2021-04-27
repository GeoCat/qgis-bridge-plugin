from geocatbridge.utils.enum_ import LabeledIntEnum


class GeoNetworkProfiles(LabeledIntEnum):
    """ Container class for GeoNetwork profile constants. """
    DEFAULT = 'Default'
    INSPIRE = 'INSPIRE'
    DUTCH = 'Dutch Geography'
