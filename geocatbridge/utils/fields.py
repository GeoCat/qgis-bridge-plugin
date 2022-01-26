from collections import Counter, OrderedDict
from contextlib import contextmanager
from typing import Dict, Iterable, Union, List

from geocatbridge.utils import strings
from geocatbridge.utils.layers import BridgeLayer


class ShpFieldLookup(OrderedDict):
    def __init__(self, *fields, max_chars: int = 10):
        """
        Creates a lookup dictionary that maps original input field name keys
        to 10-character dBase (Shapefile DBF) field name values and replaces invalid chars.
        See https://support.esri.com/en/technical-article/000005588 for field name specifications.

        :param fields:      Sequence of field names to translate.
        :param max_chars:   Number of characters to which to truncate the field names.
                            Defaults to 10 characters (standard dBase3 limitation).
        """
        super().__init__({
            f: strings.normalize(f, allowed_chars=strings.BASIC_CHARS, first_letter='F')[:max_chars]
            for f in fields
        })
        fcount = Counter(self.values())
        for k, v in reversed(self.items()):
            suffix = str(fcount[v])
            if suffix != '1':
                self[k] = v[:-len(suffix)] + suffix
                fcount = Counter(self.values())


def fieldIndexLookup(layer: BridgeLayer, field_names: Iterable = None) -> Dict[str, int]:
    """ Returns a dictionary of field names and indices for the given layer and field names.
    If no fields are specified, all field names and indices are returned.
    """
    if not field_names:
        field_names = []
    return {f.name(): i for i, f in enumerate(layer.fields()) if len(field_names) == 0 or f.name() in field_names}


def renameFields(layer: BridgeLayer, lookup: ShpFieldLookup):
    """ Renames fields of the given vector layer if they are mapped in the lookup.
    Note that layer.startEditing() must have been called prior to calling this function!
    """
    if not layer.is_vector or not layer.isEditable():
        return
    field_idx = fieldIndexLookup(layer, lookup.keys())
    for field, idx in field_idx.items():
        layer.renameAttribute(idx, lookup.get(field))


def fieldsForLayer(layer: BridgeLayer, all_layer_fields: dict,
                   shp_fields: bool = False) -> Union[List[str], ShpFieldLookup, None]:
    """ Gets a list of field names to export for the given layer. Note that the FID field is ignored (avoid conflicts).

    :param layer:               The QGIS layer for which to get the selected export fields.
    :param all_layer_fields:    Lookup dictionary for all layers and fields that need to be published.
    :param shp_fields:          If True, a ShpFieldLookup will be returned instead of a regular list of field names.
                                This ShpFieldLookup can be used by the fieldNameEditor to temporarily rename fields
                                for Shapefile export.
    :return:                    None if not a vector layer, a ShpFieldLookup if 'shp_fields' is True,
                                or a list of field names otherwise.
    """
    if not layer.is_vector:
        return
    fields = [_name for _name, publish_ in all_layer_fields[layer.id()].items() if publish_ and _name.lower() != 'fid']
    if shp_fields:
        return ShpFieldLookup(fields)
    return fields


@contextmanager
def fieldNameEditor(layer: BridgeLayer, fields: Union[List[str], ShpFieldLookup, None]):
    """ Context manager function that will temporarily rename the given field names
    so they're suitable for Shapefile exports, if 'fields' is a ShpFieldLookup.

    If the layer is not a vector layer or 'fields' is not a ShpFieldLookup,
    this function will leave the layer untouched. Otherwise, the layer will be put
    in editing mode, which will be rolled back when the context manager exits.

    :param layer:   A BridgeLayer object for which to (potentially) edit the field names.
    :param fields:  If this is a ShpFieldLookup, fields will be temporarily renamed.
    """
    editing = False
    try:
        if layer.is_vector and isinstance(fields, ShpFieldLookup):
            # Modify the layer fields for Shapefile export
            editing = layer.startEditing()
            if editing:
                renameFields(layer, fields)
        yield layer
    finally:
        if editing:
            layer.rollBack()
