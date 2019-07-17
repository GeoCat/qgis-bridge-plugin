import uuid 

def uuidForLayer(layer):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, layer.source()))

