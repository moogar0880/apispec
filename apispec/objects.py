# -*- coding: utf-8 -*-

from .definitions import generate_defintion_class
from .models import SpecObjectBase, LazyRef, string_field, list_field
from .parameters import Parameter

__author__ = 'Jon Nappi'


class Contact(SpecObjectBase):
    """The :class:`Contact` exposes contact information about the exposed API.

    :param name: The identifying name of the contact person/organization.
    :param url: The URL pointing to the contact information. MUST be a
        properly formatted URL.
    """
    KEY = 'contact'

    __attrs__ = [
        string_field('Name',  'name',  False),
        string_field('URL',   'url',   False),
        string_field('EMail', 'email', False),
    ]


class License(SpecObjectBase):
    """The :class:`License` exposes licesnsing information about the exposed
    API.

    :param name: Required. The license name used for the API.
    :param url: A URL to the license used for the API. MUST be a properly
        formatted URL.
    """
    KEY = 'license'

    __attrs__ = [
        string_field('Name', 'name', True),
        string_field('URL',  'url',  False),
    ]


class Info(SpecObjectBase):
    """The :class:`Info` class provides metadata about the specified API. This
    metadata can be used by any client, if needed.

    :param title: Required. The title of the REST API being described.
    :param version: Required. Provides the version of the application API.
    :param description: A short description of this REST API.
    :param terms_of_service: The Terms of Service for the API.
    :param contact: A :class:`Contact` instance containing contact
        information for the exposed API.
    :param license: A :class:`License` instance containing licensing
        information for the exposed API.
    """
    KEY, REQUIRED = 'info', True

    __attrs__ = [
        string_field('Title',       'title',            True),
        string_field('Description', 'description',      False),
        string_field('TOS',         'terms_of_service', False),
        string_field('Version',     'version',          True),
        Contact,
        License,
    ]

    def __str__(self):
        """str override"""
        # title is a required field, so we know that it will exist
        return '<Info> {}'.format(self.title)
    __repr__ = __str__


class Paths(list, SpecObjectBase):
    KEY, REQUIRED = 'paths', True

    def __init__(self, **kwargs):
        from .paths import Path
        paths = [Path(key=k, **kwargs[k]) for k in kwargs]
        super(Paths, self).__init__(paths)


class Definitions(dict, SpecObjectBase):
    """An object to hold data types that can be consumed and produced by
    operations. These data types can contain primitives, arrays and other
    definition models.
    """
    KEY = 'definitions'

    def __init__(self, **kwargs):
        defs = {name: generate_defintion_class(name, **kwargs[name])
                for name in kwargs}
        super(Definitions, self).__init__(defs)


class Parameters(list, SpecObjectBase):
    """An object to hold parameters to be reused across operations. Parameter
    definitions can be referenced to the ones defined here.
    """
    KEY = 'parameters'

    def __init__(self, *args, **kwargs):
        if args:
            parameters = [Parameter(key=arg.get('name', None),
                                    **arg) if '$ref' not in arg
                          else LazyRef(arg['$ref']) for arg in args[0]]
        else:
            parameters = [Parameter(key=k, **kwargs[k]) for k in kwargs]
        super(Parameters, self).__init__(parameters)


class Schema(SpecObjectBase):
    KEY = 'schema'

    __attrs__ = [
        LazyRef,
        string_field('Type', 'type', False),
    ]


class Response(SpecObjectBase):
    KEY = 'response'

    __attrs__ = [
        Schema,
        string_field('Description', 'description', True),
        string_field('Headers',     'headers',     False),
        string_field('Examples',    'examples',    False),
    ]

    def __init__(self, key=None, **kwargs):
        self._key = key
        super(Response, self).__init__(**kwargs)

    def __str__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self._key)
    __repr__ = __str__


class Responses(list, SpecObjectBase):
    """Describes a single response from from performing a specific API
    operation
    """
    KEY = 'responses'

    def __init__(self, **kwargs):
        responses = [Response(key=k, **kwargs[k]) for k in kwargs]
        super(Responses, self).__init__(responses)


class SecurityDefinitions(Definitions):
    """A declaration of the security schemes available to be used in the
    specification. This does not enforce the security schemes on the
    operations and only serves to provide the relevant details for each scheme.
    """
    KEY = 'security_definitions'


class SecurityRequirement(SpecObjectBase):
    """A :class:`SecurityRequirement` lists the required security schemes to
    execute a specific operation. The object can have multiple security
    schemes declared in it which are all required (that is, there is a logical
    AND between the schemes).

    This instance's name MUST correspond to an existing
    :class:`SecurityDefintion`.

    :param name: Required. The name of the corresponding
        :class:`SecurityDefintion`
    :param requirements: If the security scheme is of type "oauth2", then the
        value is a list of scope names required for the execution. For other
        security scheme types, the array can be used for whatever purposes you
        see fit, but be prepared to perform your own validation on it.
    """

    __attrs__ = [
        string_field('Name',       'name',         True),
        list_field('Requirements', 'requirements', True, str),
    ]

    def __str__(self):
        """str override"""
        return '<SecurityRequirement: {}>'.format(self.name)
    __repr__ = __str__


class SecurityRequirements(SpecObjectBase):
    """The :class:`SecurityRequirements` class is a container for instances of
    the :class:`SecurityRequirement` class.
    """
    KEY = 'security'

    __attrs__ = [
        list_field('Requirements', 'requirements', False, SecurityRequirement)
    ]

    def __init__(self, **kwargs):
        self.requirements = [
            SecurityRequirement(name=k, requirements=kwargs.get(k))
            for k in kwargs.keys()
        ]
        super(SecurityRequirements, self).__init__(**{})


class Documentation(SpecObjectBase):
    """A :class:`Documentation` instance allows for the referencing of an
    external resource for extended documentation on all supported objects.

    :param description: A short description of the target documentation.
    :param url: Required. The URL for the target documentation. Value MUST be
        a valid URL.
    """
    KEY = 'external_docs'

    __attrs__ = [
        string_field('Description', 'description', False),
        string_field('URL',         'url',         True),
    ]


class Tag(SpecObjectBase):
    """A :class:`Tag` is a piece of mmeta data that can be added to a single
    tag used by any supported object. It is not mandatory for a Tag Object per
    tag, as tag's also support being created as simple strings.

    :param name: Required. The name of this :class:`Tag`
    :param description: A short description for the tag.
    :param documentation: A :class:`Documentation` object, referencing
        external documentation for this :class:`Tag`
    """

    __attrs__ = [
        string_field('Name',        'name',        True),
        string_field('Description', 'description', False),
        Documentation,
    ]

    def __init__(self, *args, **kwargs):
        """Support being created as an actual tag object, or just as a string
        tag.

        :param args: If set, will be of size 1 and will contain the name of
            this tag
        :param kwargs: kwargs defining the full Tag object to be created
        """
        if len(kwargs) > 0:
            super().__init__(**kwargs)
        else:
            super().__init__(name=args[0])
            self.description = ''
            self.documentation = None

    def __str__(self):
        return '<Tag: {}>'.format(self.name)
    __repr__ = __str__
