import unicodedata
from string import digits as DIGITS, ascii_letters as ASCII_LETTERS  # noqa
from typing import Iterable

BASIC_CHARS = frozenset(DIGITS + ASCII_LETTERS + '_')
FILEPATH_CHARS = BASIC_CHARS.union("-")  # technically, dots and spaces are also allowed
WORKSPACE_CHARS = FILEPATH_CHARS.union(".")
RFC3986_CHARS = WORKSPACE_CHARS.union("~")


def replace_spaces(text: str) -> str:
    """ Replaces spaces for underscores in the given text string. """
    return text.replace(' ', '_')


def force_first_alpha(text: str, first_letter: str, prepend: bool = False) -> str:
    """
    Ensures that the given 'text' starts with the given 'first_letter',
    if it does NOT start with a letter but a non-letter character (e.g. digit).

    :param text:            Text string to verify.
    :param first_letter:    The letter that 'text' should start with (if it starts with a non-alpha char).
    :param prepend:         If True, the letter will be prepended (output length will increase by 1).
                            If False (default), the first character will be replaced (output length remains the same).
    :raises ValueError:     If the 'first_letter' attribute value is invalid.
    """
    if not isinstance(first_letter, str) or len(first_letter) != 1 or not first_letter.isalpha():
        raise ValueError('first_letter attribute must be a single letter')
    if text[0].isalpha():
        return text
    return first_letter + text[0 if prepend else 1:]


def normalize(text: str, replacement: str = '_', allowed_chars: Iterable = RFC3986_CHARS, **kwargs) -> str:
    """
    Replaces all characters in the given string with a character that is guaranteed
    to contain only the specified `allowed_chars` (RFC3986_CHARS).
    Any characters that are not in the allowed set will be replaced by the `replacement` character,
    which defaults to an underscore.

    Note that letters like "ö" or "â" will be translated to "o" and "a" respectively
    (before validation of allowed characters takes place), which may change the meaning or pronunciation of the text.

    :param text:            The string to normalize.
    :param replacement:     The single character to use as a replacement for disallowed characters.
    :param allowed_chars:   Allowed characters in the output string. Defaults to RFC3986_CHARS (basic URL chars).
                            This may be a `str` or any iterable (e.g. set, list) of single characters.
    :raises ValueError:     If the 'replacement' attribute value is invalid.
    :returns:               The normalized string.
    """
    if not (isinstance(replacement, str) and replacement in allowed_chars):
        raise ValueError('replace_char attribute must be an allowed character')
    out = ''.join(c if c in allowed_chars else replacement
                  for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return force_first_alpha(out, **kwargs) if kwargs else out


def validate(text: str, first_alpha: bool = False, allowed_chars: Iterable = RFC3986_CHARS) -> bool:
    """
    Returns True if the given text consists of the given `allowed_chars` only.

    :param text:            The string to validate.
    :param first_alpha:     If True, the function will also verify if the first character is an ASCII letter.
    :param allowed_chars:   Allowed characters in the output string. Defaults to RFC3986_CHARS (basic URL chars).
                            This may be a `str` or any iterable (e.g. set, list) of single characters.
    :return:                True if valid, False otherwise.
    """
    first_ok = text[0].isalpha() if first_alpha else True
    return first_ok and frozenset(text).issubset(allowed_chars)


def layer_slug(layer, to_web: bool = True) -> str:
    """ Convenience function to quickly convert the given layer/name to a "slug" for URLs or file names.

    :param layer:   Layer object or name. If the first, the name() property will be used.
    :param to_web:  If True (default), a web slug is returned. Otherwise, a file slug.
    """
    name = layer.name() if hasattr(layer, 'name') else layer
    norm_options = {'first_letter': 'L', 'prepend': True}
    if not to_web:
        norm_options['allowed_chars'] = FILEPATH_CHARS
    return normalize(name, **norm_options)
