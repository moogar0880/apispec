# -*- coding: utf-8 -*-
from .models import SpecObjectBase, string_field

# TODO: Parameter "in" support
# TODO: Parameter "array" support
# TODO:     - Parameter "items" support


class ParameterLocation(str, SpecObjectBase):
    """Encapsulation class for the location of a specific parameter.
    Responsible for exposing additional required fields on a per-location
    basis.
    """
    KEY, REQUIRED = 'in', True

    def __init__(self, location):
        valid = ("query", "header", "path", "formData", "body")
        if location not in valid:
            raise ValueError('%s is not a valid location' % location)
        self.location = location
        super(ParameterLocation, self).__init__()


class Parameter(SpecObjectBase):
    __attrs__ = [
        ParameterLocation,
        string_field('Name',             'name',              True),
        string_field('Required',         'required',          True),
        string_field('Type',             'type',              True),
        string_field('Description',      'description',       False),
        string_field('Format',           'format',            False),
        string_field('AllowEmpty',       'allow_empty',       False),
        string_field('Items',            'items',             False),
        string_field('CollectionFormat', 'collection_format', False),
        string_field('Default',          'default',           False),
        string_field('Maximum',          'maximum',           False),
        string_field('ExclusiveMaximum', 'exclusive_maximum', False),
        string_field('Minimum',          'minimum',           False),
        string_field('ExclusiveMinimum', 'exclusive_minimum', False),
        string_field('MaxLength',        'max_length',        False),
        string_field('MinLength',        'min_length',        False),
        string_field('Pattern',          'pattern',           False),
        string_field('MaxItems',         'max_items',         False),
        string_field('MinItems',         'min_items',         False),
        string_field('UniqueItems',      'unique_items',      False),
        string_field('Enum',             'enum',              False),
        string_field('MultipleOf',       'multiple_of',       False),
    ]

    def __init__(self, key=None, **kwargs):
        self._key = key
        super(Parameter, self).__init__(**kwargs)

    def __str__(self):
        return '<Parameter: {}>'.format(self._key)
    __repr__ = __str__
