from six import iteritems

from bravado_core import formatter, schema
from bravado_core.exception import SwaggerMappingError
from bravado_core.model import is_model, MODEL_MARKER
from bravado_core.schema import (
    is_dict_like,
    is_list_like,
    SWAGGER_PRIMITIVES,
    get_spec_for_prop
)


def marshal_schema_object(swagger_spec, schema_object_spec, value):
    """
    Marshal the value using the given schema object specification.

    Marshaling includes:
    - transform the value according to 'format' if available
    - return the value in a form suitable for 'on-the-wire' transmission

    :type swagger_spec: :class:`bravado_core.spec.Spec`
    :type schema_object_spec: dict
    :type value: int, long, string, unicode, boolean, list, dict, Model type
    :return: marshaled value
    :rtype: int, long, string, unicode, boolean, list, dict
    :raises: SwaggerMappingError
    """
    obj_type = schema_object_spec['type']

    if obj_type in SWAGGER_PRIMITIVES:
        return marshal_primitive(schema_object_spec, value)

    if obj_type == 'array':
        return marshal_array(swagger_spec, schema_object_spec, value)

    if is_model(schema_object_spec):

        # Allow models to be passed in as dicts for flexibility.
        if is_dict_like(value):
            return marshal_object(swagger_spec, schema_object_spec, value)

        # It is important that the 'model' check comes before 'object' check
        # below. Model specs are of type 'object' but also have a MODEL_MARKER
        # key for identification.
        return marshal_model(swagger_spec, schema_object_spec, value)

    if obj_type == 'object':
        return marshal_object(swagger_spec, schema_object_spec, value)

    if obj_type == 'file':
        return value

    raise SwaggerMappingError('Unknown type {0} for value {1}'.format(
        obj_type, value))


def marshal_primitive(spec, value):
    """Marshal a python primitive type into a jsonschema primitive.

    :type spec: dict or jsonref.JsonRef
    :type value: int, long, float, boolean, string, unicode, or an object
        based on 'format'
    :rtype: int, long, float, boolean, string, unicode, etc
    :raises: SwaggerMappingError
    """
    default_used = False

    if value is None and schema.has_default(spec):
        default_used = True
        value = schema.get_default(spec)

    if value is None and schema.is_required(spec):
        raise SwaggerMappingError('Spec {0} is a required value'.format(spec))

    if not default_used:
        value = formatter.to_wire(spec, value)

    return value


def marshal_array(swagger_spec, array_spec, array_value):
    """Marshal a jsonschema type of 'array' into a json-like list.

    :type swagger_spec: :class:`bravado_core.spec.Spec`
    :type array_spec: dict or jsonref.JsonRef
    :type array_value: list
    :rtype: list
    :raises: SwaggerMappingError
    """
    if not is_list_like(array_value):
        raise SwaggerMappingError('Expected list like type for {0}:{1}'.format(
            type(array_value), array_value))

    result = []
    for element in array_value:
        result.append(marshal_schema_object(
            swagger_spec, array_spec['items'], element))

    return result


def marshal_object(swagger_spec, object_spec, object_value):
    """Marshal a jsonschema type of 'object' into a json-like dict.

    :type swagger_spec: :class:`bravado_core.spec.Spec`
    :type object_spec: dict or jsonref.JsonRef
    :type object_value: dict
    :rtype: dict
    :raises: SwaggerMappingError
    """
    if not is_dict_like(object_value):
        raise SwaggerMappingError('Expected dict like type for {0}:{1}'.format(
            type(object_value), object_value))

    result = {}
    for k, v in iteritems(object_value):

        # Values cannot be None - skip them entirely!
        if v is None:
            continue

        prop_spec = get_spec_for_prop(object_spec, object_value, k)
        if prop_spec:
            result[k] = marshal_schema_object(swagger_spec, prop_spec, v)
        else:
            # Don't marshal when a spec is not available - just pass through
            result[k] = v

    return result


def marshal_model(swagger_spec, model_spec, model_value):
    """Marshal a Model instance into a json-like dict.

    :type swagger_spec: :class:`bravado_core.spec.Spec`
    :type model_spec: dict or jsonref.JsonRef
    :type model_value: Model instance
    :rtype: dict
    :raises: SwaggerMappingError
    """
    model_name = model_spec[MODEL_MARKER]
    model_type = swagger_spec.definitions.get(model_name, None)

    if model_type is None:
        raise SwaggerMappingError('Unknown model {0}'.format(model_name))

    if not isinstance(model_value, model_type):
        raise SwaggerMappingError(
            'Expected model of type {0} for {1}:{2}'
            .format(model_name, type(model_value), model_value))

    # just convert the model to a dict and feed into `marshal_object` because
    # models are essentially 'type':'object' when marshaled
    attr_names = dir(model_value)
    object_value = dict(
        (attr_name, getattr(model_value, attr_name))
        for attr_name in attr_names)

    return marshal_object(swagger_spec, model_spec, object_value)
