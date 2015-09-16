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
    # Parse out the names of our args and kwargs, as well as the default value
    # for the kwargs
    fields = args + [arg[0] for arg in kwargs]
    kwargs = [name + '={}()'.format(typ.__name__) for (name, typ) in kwargs]
    code = 'def __init__(self, %s):\n' % ', '.join(args + kwargs)

    for name in fields:
        # When called `self.%s` will point at the descriptor for that field,
        # enfocing whatever type checking may be in place
        code += '    self.%s = %s\n' % (name, name)
    return code


def _generate_example_generator(**kwargs):
    """Generate a function that can be used as a class method that generates
    example instances of it's implementing class, given the examples provided
    via kwargs. If there is no 'examples' key provided in kwargs, return
    :const:`None`.

    :param kwargs: Keyword args from the model definition. If present, the
        'examples' key will be extracted
    :return: A function capable of being used as a class method to generate
        example instances of the implementing class. Or :const:`None` if no
        example definitions are provided.
    """
    # If we can't find any examples, return None
    if 'examples' not in kwargs:
        return None

    examples = kwargs.get('examples', [])

    def generate_examples(cls):
        """Generate example instances of this class"""
        return [cls(**ex) for ex in examples]
    return generate_examples


class DefinitionMeta(type):
    """Metaclass for Definition types. Dynamically generate the __init__
    method for each class.
    """

    def __new__(cls, clsname, bases, clsdict):
        properties = clsdict.get('properties', {})
        args = [k for k in properties if isinstance(properties[k], dict) and
                properties[k].get('required', False)]
        kwargs = [(k, cls.type_from_name(properties[k].get('type')))
                  for k in properties if isinstance(properties[k], dict) and
                  not properties[k].get('required', False)]
        fields = args + [arg[0] for arg in kwargs]

        # Make the init function and inject it into our new class's namespace
        if fields:
            exec(_make_init(args, kwargs), globals(), properties)

        # Handle checking to see if our definition has defined examples and
        # generating a class method to create instances from those examples
        example_gen = _generate_example_generator(**clsdict)
        if example_gen is not None:
            properties['generate_examples'] = classmethod(example_gen)

        # Create our class type by calling type's __new__ method
        clsobj = super().__new__(cls, clsname, bases, dict(properties))

        # Keep a handle on the names of our defined attributes
        setattr(clsobj, '__attrs__', fields)

        # Iterate over each of our fields and put a Descriptor of the
        # appropriate type into our class's namespace
        for field_name in fields:
            field = properties[field_name]

            # Check for special enum case. If we've found an enum, set it and
            # continue iterating
            if 'enum' in field:
                setattr(clsobj, field_name, cls.oneof_field(field_name, field))
                continue

            typ = cls.type_from_name(field['type'])

            # Map types to the methods that create their descriptors
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
        """Create an Array descriptor for the provided items"""
        return Array(name, items=field['items'])

    @classmethod
    def oneof_field(cls, name, field):
        """Create a Oneof descriptor for the provided items"""
        return Oneof(name, values=field['enum'])

    @classmethod
    def int_field(cls, name, field):
        """Create either an Integer or SizedInteger descriptor, depending on
        whether a minimum or maximum were specified
        """
        if 'minimum' in field or 'maximum' in field:
            return SizedInteger(name, default=field.get('default', None),
                                minimum=field.get('minimum', None),
                                maximum=field.get('maximum', None))
        return Integer(name, default=field.get('default', None))

    @classmethod
    def float_field(cls, name, field):
        """Create either a Float or SizedFloat descriptor, depending on
        whether a minimum or maximum were specified
        """
        if 'minimum' in field or 'maximum' in field:
            return SizedFloat(name, default=field.get('default', None),
                              minimum=field.get('minimum', None),
                              maximum=field.get('maximum', None))
        return Float(name, default=field.get('default', None))

    @classmethod
    def string_field(cls, name, field):
        """Create either a String, Byte, or Regex descriptor, depending on the
        format specified.
        """
        format_ = field.get('format', None)
        if format_ == 'byte' or format_ == 'binary':
            return cls.byte_field(name, field)
        elif 'pattern' in field:
            return Regex(name, pattern=field['pattern'],
                         default=field.get('default', None))
        elif format_ == 'date':
            pass
        elif format_ == 'date-time':
            pass
        elif format_ == 'password':
            pass
        return String(name, default=field.get('default', None))

    @classmethod
    def byte_field(cls, name, field):
        """Return a Bytes descriptor"""
        return Bytes(name, default=field.get('default', None))

    @classmethod
    def bool_field(cls, name, field):
        """Return a Boolean descriptor"""
        return Boolean(name, default=field.get('default', None))

    @classmethod
    def date_field(cls, name, field):
        """Return a Date descriptor"""
        format_ = field.get('format', None)
        if format_ is None or format_ == 'iso8601':
            regex = (r'\A' + ISO8601_YEAR_RE + r'(?:' + r'(?P<datesep>-?)' +
                     ISO8601_MONTH_RE + r'(?:' + r'(?P=datesep)' +
                     ISO8601_DAY_RE + r')?' + r')?')
            return Date(name=name, pat=regex)
        raise NotImplementedError

    @classmethod
    def datetime_field(cls, name, field):
        """Return a DateTime descriptor"""
        format_ = field.get('format', None)
        if format_ is None or format_ == 'iso8601':
            return DateTime(name=name, pat=ISO8601_RE)
        raise NotImplementedError

    @classmethod
    def password_field(cls, name, field):
        """Return a Password descriptor"""
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
    # TODO(moogar0880): allOf support (requires $ref) (spec inheritance)
    return type(name, bases, kwargs)
