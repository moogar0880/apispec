# -*- coding: utf-8 -*-
import logging
import yaml

__author__ = 'Jon Nappi'


class Loader:
    """Base Loader type. Subclasses of :class:`Loader` are responsible for
    converting raw specification files into Python dict objects via whatever
    form of data manipulation is required.
    """
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)


class YAMLLoader(Loader):
    """:class:`YAMLLoader` is responsible for loading raw YAML specification
    data into a :const:`dict`
    """
    def __init__(self, raw_data):
        super(YAMLLoader, self).__init__()
        self.raw_data = raw_data

    def load(self):
        self._logger.info('Loading YAML Data')
        return yaml.load(self.raw_data)


class YAMLFileLoader(YAMLLoader):
    """:class:`YAMFileLLoader` is responsible for loading a YAML specification
    file's data into a :const:`dict`
    """
    def __init__(self, file_path):
        with open(file_path) as f:
            super(YAMLFileLoader, self).__init__(f.read())
