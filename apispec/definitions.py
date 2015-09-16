# -*- coding: utf-8 -*-

from iso8601 import (ISO8601_YEAR_RE, ISO8601_MONTH_RE, ISO8601_DAY_RE,
                     ISO8601_RE)

from .fields import *

__author__ = 'Jon Nappi'

__all__ = ['DefinitionMeta', 'DefinitionBase', 'generate_defintion_class']


def _make_init(args, kwargs):
    """Given a list of required and optional field names, generate an
    __init__ method. Optional fields will default to :const:`None`
    """
    fields = args + [arg[0] for arg in kwargs]
    kwargs = [name + '={}()'.format(typ.__name__) for (name, typ) in kwargs]
    code = 'def __init__(self, %s):\n' % ', '.join(args + kwargs)

    for name in fields:
        code += '    self.%s = %s\n' % (name, name)
    return code


class DefinitionMeta(type):
    """Metaclass for Definition types. Dynamically generate the __init__
    method for each class.
    """

    def __new__(cls, clsname, bases, clsdict):
        args = [k for k in clsdict if isinstance(clsdict[k], dict) and
                clsdict[k].get('required', False)]
        kwargs = [(k, cls.type_from_name(clsdict[k].get('type')))
                  for k in clsdict if isinstance(clsdict[k], dict) and
                  not clsdict[k].get('required', False)]
        fields = args + [arg[0] for arg in kwargs]

        # Make the init function and inject it into our new class's namespace
        if fields:
            exec(_make_init(args, kwargs), globals(), clsdict)

        clsobj = super().__new__(cls, clsname, bases, dict(clsdict))
        setattr(clsobj, '_properties', fields)
        for field_name in fields:
            field = clsdict[field_name]
            typ = cls.type_from_name(field['type'])

            type_map = {
                int: cls.int_field,
                float: cls.float_field,
                str: cls.string_field,
                bool: cls.bool_field,
                tuple: cls.array_field
            }

            # Set the descriptor into the class's namespace
            setattr(clsobj, field_name,
                    type_map[typ](field_name, field))
        return clsobj

    @staticmethod
    def type_from_name(name):
        """Given the name of a specification type, return the corresponding
        Python data type

        :param name: The specification type name
        :return: The Python data type corresponding to *name*
        """
        if name in ('integer', 'long'):
            return int
        elif name in ('float', 'double'):
            return float
        elif name in ('string', 'byte', 'binary'):
            return str
        elif name == 'boolean':
            return bool
        elif name == 'array':
            # return tuple rather than list for use as default __init__
            # arguments in order to force immutibility
            return tuple
        raise TypeError('Encountered Unsupported Type: %s' % name)

    @classmethod
    def array_field(cls, name, field):
        return Array(name, items=field['items'])

    @classmethod
    def int_field(cls, name, field):
        if 'minimum' in field or 'maximum' in field:
            return SizedInteger(name, default=field.get('default', None),
                                minimum=field.get('minimum', None),
                                maximum=field.get('maximum', None))
        return Integer(name, default=field.get('default', None))

    @classmethod
    def float_field(cls, name, field):
        return Float(name, default=field.get('default', None))

    @classmethod
    def string_field(cls, name, field):
        format_ = field.get('format', None)
        if format_ == 'byte' or format_ == 'binary':
            return cls.byte_field(name, field)
        elif format_ == 'date':
            pass
        elif format_ == 'date-time':
            pass
        elif format_ == 'password':
            pass
        return String(name, default=field.get('default', None))

    @classmethod
    def byte_field(cls, name, field):
        return Bytes(name, default=field.get('default', None))

    @classmethod
    def bool_field(cls, name, field):
        return Boolean(name, default=field.get('default', None))

    @classmethod
    def date_field(cls, name, field):
        format_ = field.get('format', None)
        if format_ is None or format_ == 'iso8601':
            regex = (r'\A' + ISO8601_YEAR_RE + r'(?:' + r'(?P<datesep>-?)' +
                     ISO8601_MONTH_RE + r'(?:' + r'(?P=datesep)' +
                     ISO8601_DAY_RE + r')?' + r')?')
            return Date(name=name, pat=regex)
        raise NotImplementedError

    @classmethod
    def datetime_field(cls, name, field):
        format_ = field.get('format', None)
        if format_ is None or format_ == 'iso8601':
            return DateTime(name=name, pat=ISO8601_RE)
        raise NotImplementedError

    @classmethod
    def password_field(cls, name, field):
        pass


class DefinitionBase(metaclass=DefinitionMeta):
    """Base class for all defintion type models"""
    pass


def generate_defintion_class(name, bases=(DefinitionBase,), **kwargs):
    """Generate a defintion model class with the properties provided in
    kwargs['properties'].

    :param name: The name of the model being defined
    :param bases: Any base classes for the generated type. By default the only
        base class is :class:`DefinitionBase`
    :param kwargs: Arbitrary keyword args defining the model's properties
    :return: The newly created class type
    """
    # TODO(moogar0880): Definition examples
    # TODO(moogar0880): regex formatting for strings
    # TODO(moogar0880): allOf support (requires $ref) (spec inheritance)
    # TODO(moogar0880): enum support
    return type(name, bases, kwargs.get('properties', {}))
