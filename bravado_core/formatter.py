"""
Support for the 'format' key in the swagger spec as outlined in
https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#dataTypeFormat
"""

import warnings
from collections import namedtuple

import six
import dateutil.parser

from bravado_core import schema

if six.PY3:
    long = int

NO_OP = lambda x: None


def to_wire(spec, value):
    """Converts a python primitive or object to a reasonable wire
    representation given the 'format' in the given spec.

    :param spec: spec for a primitive type as a dict
    :type value: int, long, float, boolean, string, unicode, etc
    :rtype: int, long, float, boolean, string, unicode, etc
    """
    if value is None or not schema.has_format(spec):
        return value
    formatter = get_format(schema.get_format(spec))
    return formatter.to_wire(value) if formatter else value


def to_python(spec, value):
    """Converts a value in wire format to its python representation given
    the 'format' in the given spec.

    :param spec: spec for a primitive type as a dict
    :type value: int, long, float, boolean, string, unicode, etc
    :rtype: int, long, float, boolean, string, object, etc
    """
    if value is None or not schema.has_format(spec):
        return value
    formatter = get_format(schema.get_format(spec))
    return formatter.to_python(value) if formatter else value


def register_format(swagger_format):
    """Register a user defined format with bravado-core.

    :type swagger_format: :class:`SwaggerFormat`
    """
    global _formatters
    _formatters[swagger_format.format] = swagger_format


def get_format(format):
    """Get registered formatter mapped to given format.

    :param format: Format name like int, base64, etc.
    :type format: str
    :rtype: :class:`SwaggerFormat` or None
    """
    formatter = _formatters.get(format)
    if format and not formatter:
        warnings.warn(
            "%s format is not registered with bravado-core!" % format, Warning)
    return formatter


# validate should check the correctness of `wire` value
class SwaggerFormat(namedtuple('SwaggerFormat',
                    'format to_python to_wire validate description')):
    """It defines a user defined format which can be registered with
    bravado-core and then can be used for marshalling/unmarshalling data
    as per the user defined methods. User can also add `validate` method
    which is invoked during bravado-core's validation flow.

    :param format: Name for the user format.
    :param to_python: function to unmarshal a value of this format.
                      Eg. lambda val_str: base64.b64decode(val_str)
    :param to_wire: function to marshal a value of this format
                    Eg. lambda val_py: base64.b64encode(val_py)
    :param validate: function to validate the marshalled value. Raises
                     :class:`bravado_core.exception.SwaggerValidationError`
                     if value does not conform to the format.
    :param description: Short description of the format and conversion logic.
    """


_formatters = {
    'byte': SwaggerFormat(
        format='byte',
        to_wire=lambda b: b if isinstance(b, str) else str(b),
        to_python=(
            lambda s: s if isinstance(s, str) else str(s)),
        validate=NO_OP,  # jsonschema validates string
        description='Converts [wire]string:byte <=> python byte'),
    'date': SwaggerFormat(
        format='date',
        to_wire=lambda d: d.isoformat(),
        to_python=lambda d: dateutil.parser.parse(d).date(),
        validate=NO_OP,  # jsonschema validates date
        description='Converts [wire]string:date <=> python datetime.date'),
    # Python has no double. float is C's double in CPython
    'double': SwaggerFormat(
        format='double',
        to_wire=lambda d: d if isinstance(d, float) else float(d),
        to_python=lambda d: d if isinstance(d, float) else float(d),
        validate=NO_OP,  # jsonschema validates number
        description='Converts [wire]number:double <=> python float'),
    'date-time': SwaggerFormat(
        format='date-time',
        to_wire=lambda dt: dt.isoformat(),
        to_python=lambda dt: dateutil.parser.parse(dt),
        validate=NO_OP,  # jsonschema validates date-time
        description=(
            'Converts string:date-time <=> python datetime.datetime')),
    'float': SwaggerFormat(
        format='float',
        to_wire=lambda f: f if isinstance(f, float) else float(f),
        to_python=lambda f: f if isinstance(f, float) else float(f),
        validate=NO_OP,  # jsonschema validates number
        description='Converts [wire]number:float <=> python float'),
    'int32': SwaggerFormat(
        format='int32',
        to_wire=lambda i: i if isinstance(i, int) else int(i),
        to_python=lambda i: i if isinstance(i, int) else int(i),
        validate=NO_OP,  # jsonschema validates integer
        description='Converts [wire]integer:int32 <=> python int'),
    'int64': SwaggerFormat(
        format='int64',
        to_wire=lambda i: i if isinstance(i, long) else long(i),
        to_python=lambda i: i if isinstance(i, long) else long(i),
        validate=NO_OP,  # jsonschema validates integer
        description='Converts [wire]integer:int64 <=> python long'),
    }
