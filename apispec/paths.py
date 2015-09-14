# -*- coding: utf-8 -*-
from .models import SpecObjectBase, string_field, list_field
from .objects import Documentation, Parameters, Responses, SecurityRequirements


class PathOperation(SpecObjectBase):
    __attrs__ = [
        string_field('Summary',     'summary',      False),
        string_field('Description', 'description',  False),
        string_field('OperationID', 'operation_id', False),
        string_field('Deprecated',  'deprecated',   False),
        list_field('Tags',          'tags',         False, str),
        list_field('Consumes',      'consumes',     False, str),
        list_field('Produces',      'produces',     False, str),
        list_field('Schemes',       'schemes',      False, str),
        Documentation,
        Parameters,
        Responses,
        SecurityRequirements,
    ]


class Path(SpecObjectBase):
    def __init__(self, key=None, **kwargs):
        self._key = key
        self.operations = [
            PathOperation(**kwargs.get(k))
            for k in kwargs
        ]
        super(Path, self).__init__(**kwargs)

    def __str__(self):
        return '<Path: {}>'.format(self._key)
    __repr__ = __str__
