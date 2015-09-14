# -*- coding: utf-8 -*-

from .definitions import DefinitionBase


class SecurityDefintionBase(DefinitionBase):
    __attrs__ = [
        '',
    ]


class OAUTH2Definition(SecurityDefintionBase):
    pass


class APIKeyDefinition(SecurityDefintionBase):
    pass


class BasicDefinition(SecurityDefintionBase):
    pass

