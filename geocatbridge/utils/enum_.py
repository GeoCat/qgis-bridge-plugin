class LabeledInt(int):
    """ Subclass of int that allows to assign a name to a number.
    Can be used to set metadata profile enum constants with labels.
    """
    def __new__(cls, index, parent: type, name, value):
        return int.__new__(cls, int(index))  # noqa

    def __init__(self, index, parent: type, name, value):  # noqa
        super().__init__()
        if not issubclass(parent, LabeledIntEnum):
            raise TypeError(f'{LabeledInt.__name__} parent must be of type {LabeledIntEnum.__name__}')
        self._parent = object.__getattribute__(parent, '__name__')  # noqa
        self._name = str(name)
        self._value = value

    def __eq__(self, other):
        if isinstance(other, int):
            int_equals = int(self) == int(other)
            if isinstance(other, self.__class__):
                return int_equals and self._parent == other._parent and \
                       self.name == other.name and self.value == other.value
            return int_equals
        return False

    def __bool__(self):
        index = int(self)
        if index > 0 or (index == 0 and self.name and self.value):
            return True
        return False

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"<{self._parent}.{self.name}: ({int(self)}, {repr(self.value)})>"

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self):
        return self._value


class LabeledIntEnumType(type):
    """ Container base class for MetadataProfile type constants.
    Provides class methods to make the container iterable and to check if a given profile is contained.
    """

    def _items(cls):
        for i, (attr, val) in enumerate((attr, val) for (attr, val) in
                                        object.__getattribute__(cls, '__dict__').items()
                                        if attr.isupper() and not attr.startswith('_')):
            yield attr, LabeledInt(i, cls, attr, val)

    def __iter__(cls):
        for _, constant in object.__getattribute__(cls, '_items')():
            yield constant

    def __contains__(cls, profile):
        return any(v == profile for v in cls)

    def __getattribute__(cls, item):
        constant = dict(object.__getattribute__(cls, '_items')()).get(item)
        if constant is not None:
            return constant
        return object.__getattribute__(cls, item)

    def __getitem__(cls, item):
        if not isinstance(item, int):
            raise TypeError(f'{cls.__name__} indices must be integers, not {type(item)}')
        for _, constant in object.__getattribute__(cls, '_items')():
            if item == int(constant):
                return constant
        raise IndexError(f'{cls.__name__} index out of range')

    def __len__(cls):
        return len(list(v for v in cls))

    def from_value(cls, value) -> LabeledInt:
        """ Finds the LabeledIntEnum constant with the given value (label).
        Values are checked as-is: no conversion or case change takes place.

        :raises:    KeyError if no LabeledIntEnum constant had the given value.
        """
        for constant in cls:
            if constant.value == value:
                return constant
        raise KeyError(f'no {LabeledIntEnum.__name__} constant with value {repr(value)} in {cls.__name__}')


class LabeledIntEnum(metaclass=LabeledIntEnumType):
    def __init__(self):
        raise NotImplementedError(f'{LabeledIntEnum.__name__} types cannot be instantiated')


__all__ = [LabeledIntEnum.__name__]
