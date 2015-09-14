# -*- coding: utf-8 -*-
import logging

from ..loaders import YAMLFileLoader
from ..models import SpecObjectBase, string_field, list_field
from ..objects import (Info, Paths, Definitions, Parameters, Responses,
                       SecurityDefinitions, SecurityRequirements, Tag,
                       Documentation)

__author__ = 'Jon Nappi'

LOGGER = logging.getLogger(__name__)


def extract_includes(filepath='main.yaml'):
    """Given the provided *filepath*, load the list of swaggregator include
    statements, in the order that they appear in *filepath*

    :param filepath: The path to the swaggregator compliant yaml file
    :return: A :const:`list` of swagger files to include
    """
    includes = []
    include_stmt = '#include:'
    with open(filepath) as f:
        comment_lines = (l for l in f if l.startswith('#'))
        for line in comment_lines:
            if line.startswith(include_stmt):
                includes.append(line.replace(include_stmt, '').strip())
    return includes


class SwaggerSpec(SpecObjectBase):
    """A object representation of a Swagger API specification namespace."""

    # Assortment of attributes to attempt to import into this specification's
    # namespace and their assorted default types. These attrs are tuples of
    # the form (key, required, callback, default_type)
    __attrs__ = [
        Definitions,
        Documentation,
        Info,
        Parameters,
        Paths,
        Responses,
        SecurityDefinitions,
        SecurityRequirements,
        string_field('Host', 'host', False),
        string_field('BasePath', 'base_path', False),
        list_field('Schemes', 'schemes', False, str),
        list_field('Consumes', 'consumes', False, str),
        list_field('Produces', 'produces', False, str),
        list_field('Tags', 'tags', False, Tag),
    ]

    LOADER = YAMLFileLoader

    def __init__(self, spec='main.yaml'):
        """Create a new SwaggerSpec instance based off of the root
        specification from the file specified by *spec*

        :param spec: The swagger spec file entry point
        """
        logging.basicConfig(level=logging.DEBUG)
        self._spec = spec
        self._loader = self.LOADER(spec)

        # Load our main swagger file's specification into this instance
        super(SwaggerSpec, self).__init__(**self._loader.load())
        self.load_refs(self)

    def load_includes(self):
        """Load include statements and register them into this namespace"""
        includes = extract_includes(self._spec)
        for include in includes:
            self._include(include)

    def _include(self, include):
        """Recursive include method used to recursively include any
        specification files
        """
        self.merge(include)
        includes = extract_includes(include)
        for include in includes:
            self._include(include)

    def merge(self, include):
        """Merge the data stored in the *include* spec file, into our current
        SwaggerSpec instance
        """
        data = self.LOADER(include).load()
        for key, typ in self.__attrs__:
            if typ is dict:
                self.__dict__[key].update(data.get(key, typ()))
            else:
                self.__dict__[key] += data.get(key, typ())

    def output(self, filepath):
        """Write the contents of this SwaggerSpec instance to *filepath*

        :param filepath: The path to the file to output the fully compiled spec
            out to
        """
        with open(filepath, 'w') as f:
            f.write(self.__yaml__())
