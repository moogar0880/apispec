# -*- coding: utf-8 -*-
import logging
import yaml
import json
from functools import wraps

from .definitions import DefinitionBase
from .loaders import Loader

__all__ = ['string_field', 'list_field', 'SpecObjectBase']


def string_field(name, key, required=False):
    """Dynamically generate a custom string type that can be used when loading
    in api specification data. These string objects will have the attributes
    required for them to be able to be used as SpecObjectBase's, but will
    inherit from the builtin str class.

    :param name: The name of the class to be generated. MUST be a valid Python
        class name
    :param key: The KEY attribute to set for filtering when used as an
        attribute to a :class:`SpecObjectBase` instance
    :param required: Boolean flag indicating whether or not the key is
        required from the provided spec file
    :return: The newly generated class type
    """
    return type(name, (str,), dict(KEY=key, REQUIRED=required))


def list_field(name, key, required=False, contains=object):
    """Dynamically generate a custom list type that can be used when loading
    in api specification data. These list objects will have the attributes
    required for them to be able to be used as SpecObjectBase's, but will
    inherit from the builtin str class.

    :param name: The name of the class to be generated. MUST be a valid Python
        class name
    :param key: The KEY attribute to set for filtering when used as an
        attribute to a :class:`SpecObjectBase` instance
    :param required: Boolean flag indicating whether or not the key is
        required from the provided spec file
    :return: The newly generated class type
    """
    return type(name, (SpecList,),
                dict(KEY=key, REQUIRED=required, CONTAINS=contains))


class SpecList(list):
    """An API Specification list type. A subclass of the builtin *list* type
    which can configure the type of item contained inside of itself.
    """
    CONTAINS = object

    def __init__(self, iterable=None):
        if iterable is None:
            iterable = []
        super(SpecList, self).__init__([self.CONTAINS(x) for x in iterable])


class SpecObjectBase:
    """Base class for all API Spec implementation classes. Provides the
    ability to Load API Specification from source content. Also, provides the
    ability to define how to manipulate the specification data into an
    instance via the :func:`SpecObjectBase.build` method. Additionally, you
    can specify the name of the key corresponding to a Spec object, a default
    value for that key, and whether or not that key is required.

    :param __attrs__:
    :param KEY:
    :param DEFAULT_VALUE:
    :param REQUIRED:
    :param LOADER:
    """
    __attrs__ = []
    KEY = DEFAULT_VALUE = None
    REQUIRED = False
    LOADER = Loader

    def __init__(self, **kwargs):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.build(**kwargs)

    def build(self, **spec_data):
        """Build this Specification based on the provided

        :param spec_data:
        :return:
        """
        valid_keys = [t.KEY for t in self.__attrs__]
        for typ in self.__attrs__:
            if typ.KEY not in valid_keys:
                self._logger.warning('%s is not a valid key', typ.KEY)
                continue

            # Check that we didn't skip a required field
            if typ.REQUIRED and typ.KEY not in spec_data:
                self._logger.warning('Missing required key: %s', typ.KEY)
                pass  # Raise exception

            # Ignore non-required keys that weren't specified
            if not typ.REQUIRED and typ.KEY not in spec_data:
                self._logger.info('Key Not Set: %s', typ.KEY)
                continue

            # Pull our key out of the spec data, defaulting to None if the key
            # does not exist. If the extracted value isn't None (if the key
            # was specified) then it will be a dict and should be cast to the
            # appropriate type.
            value = spec_data.get(typ.KEY, None)

            if value is not None:
                # Build a new class instance
                if isinstance(value, dict):
                    value = typ(**{str(k): value[k] for k in value})
                else:
                    value = typ(value)
            else:
                value = typ()  # Default to the type of this key

            # Need to filter out $ref since it isn't a valid python variable
            typ_key = typ.KEY if typ.KEY != '$ref' else 'ref'
            setattr(self, typ_key, value)

    def load_refs(self, spec=None):
        while LazyRefMeta.REGISTRY:
            unloaded_ref = LazyRefMeta.REGISTRY.pop()
            try:
                self._logger.info('Loading $ref: %s', str(unloaded_ref))
                unloaded_ref.load(spec)
            except AttributeError:
                self._logger.warning('ERROR LOADING $ref')

    def __yaml__(self):
        """Express this apispec instance as a YAML string"""
        data = {k: self.__dict__[k] for k in self.__dict__
                if not k.startswith('_')}
        return yaml.dump(data, default_flow_style=False)

    def __json__(self):
        """Express this apispec instance as a json string"""
        data = {k: self.__dict__[k] for k in self.__dict__
                if not k.startswith('_')}
        return json.dumps(data)


class LazyRefMeta(type):
    """Metaclass for the LazyRef type. Handles registering each $ref instance
    that's created with the $ref Registry so we can ensure that we proxy all
    of our ref's before we complete our parsing of the spec file.
    """
    REGISTRY = []

    def __new__(cls, clsname, bases, clsdict):
        clsobj = super().__new__(cls, clsname, bases, dict(clsdict))
        clsobj.__init__ = cls.registry_init(clsobj.__init__)
        return clsobj

    @classmethod
    def registry_init(cls, f):
        @wraps(f)
        def register(self, *args, **kwargs):
            cls.REGISTRY.append(self)
            return f(self, *args, **kwargs)

        return register


class LazyRef(metaclass=LazyRefMeta):
    """The :class:`LazyRef` class type implements the JSON Reference protocol by
    acting as a placeholder for objects defined elsewhere in the API
    specification document. The LazyRef itself acts as a proxy to the $ref'd
    API Spec object, once the object has been discovered and checked to be
    valid.
    """
    KEY, REQUIRED = '$ref', False

    #: Keys that need to be looked up locally, not via the proxy object
    _local_lookups = ('__dict__', '_proxy_loaded', '__unproxy__', '__object__',
                      '_local_lookups', '__proxy_delattr__',
                      '__proxy_setattr__',
                      '__proxy_getattribute__')

    def __init__(self, reference):
        """Create a new LazyRef proxy

        :param reference: The path to the object being referenced. May be
            either a local path (ie, #/definitions/MyDefinition), a relative
            or absolute path to a spec file on the system
            (ie, /etc/swagger/myspec.yaml), or a url pointing to a remote spec
            file somewhere on the internet (ie, http://mysite.com/swagger)
        """
        # _proxy_loaded is a flag set to indicate whether or not this LazyRef
        # has started proxying the referenced object yet or not
        self._proxy_loaded = False
        self.reference = reference

        #: __object__ is the object being proxied by this LazyRef
        self.__object__ = None

    def load(self, spec=None):
        """Determine what type of reference we've been given and load the
        reference accordingly

        :param spec: A loaded API Specification object
        :return: The proxied __object__
        """
        # It doesn't make sense to load a spec once it's already been loaded.
        if self._proxy_loaded:
            return self.__object__

        if self.reference.startswith('#'):
            self.local_reference(spec)
        elif self.reference.startswith('http'):
            self.remote_reference()
        else:
            self.relative_reference()

        # If we were able to load our ref'd object, being proxying requests
        # through to our ref'd object
        if self.__object__ is not None:
            self._proxy_loaded = True
        return self.__object__

    def local_reference(self, spec):
        """Load an object reference that is local to the currently loaded API
        specification
        """
        ref_path = self.reference.split('/')
        ref_type, name = ref_path[1], ref_path[2]
        if ref_type == 'definitions':
            self.__object__ = self.get_definition(name)
        elif ref_type == 'parameters':
            self.__object__ = self.get_parameter(name, spec)
        elif ref_type == 'responses':
            self.__object__ = self.get_response(name, spec)

    def relative_reference(self):
        """*Not Implemented*
        Load an object reference from a specification file somewhere else on
        the file system
        """
        raise NotImplementedError

    def remote_reference(self):
        """*Not Implemented*
        Load an object reference from a specification somewhere on the
        internet
        """
        raise NotImplementedError

    def _ref_search(self, name, collection, key=None):
        """Perform a search for a $ref named *name*. If such a ref isn't found
        :const:`None` is returned
        """
        if key is None:
            key = lambda x: x == name
        # Definition will either be the first item returned from the generator
        # of subclass names, or it will be None
        return next(
            (x for x in collection if key(x)),
            None
        )

    def get_definition(self, name):
        """Return a loaded Model definition that matches the given *name*

        :param name: The name of the model definition to load
        :return: The discovered Model Definition
        :raises TypeError: If no model definition matching *name* can be found
        """
        subs = DefinitionBase.__subclasses__()

        definition = self._ref_search(name, subs,
                                      lambda x: x.__name__ == name)
        if definition is None:
            raise TypeError(
                "A model definition named %s doesn't exist." % name)
        return definition

    def get_parameter(self, name, spec):
        """Return a loaded Parameter definition that matches the given *name*

        :param name: The name of the parameter definition to load
        :return: The discovered parameter Definition
        :raises TypeError: If no model definition matching *name* can be found
        """
        parameter = self._ref_search(name, spec.parameters,
                                     lambda x: x._key == name)
        if parameter is None:
            raise TypeError("A parameter named %s doesn't exist." % name)
        return parameter

    def get_response(self, name, spec):
        """Return a loaded Response definition that matches the given *name*

        :param name: The name of the response definition to load
        :return: The discovered response Definition
        :raises TypeError: If no model definition matching *name* can be found
        """
        response = self._ref_search(name, spec.responses,
                                    lambda x: x._key == name)
        if response is None:
            raise TypeError("A response named %s doesn't exist." % name)
        return response

    def __unproxy__(self):
        """Disable our attribute proxying methods"""
        self.__dict__['__object__ '] = None
        self.__dict__['_proxy_loaded '] = False

    def __getattribute__(self, name):
        """If we haven't loaded our proxy object yet, run as normal. If we
        have loaded our proxy there are a few special attributes that we don't
        proxy, otherwise, run a lookup on our proxied object. If we fail to
        find the specified, raise an AttributeError as expected

        :param name: The name of the attribute to retrieve
        :return: The retrieved attribute
        :raises AttributeError: If the provided attribute can't be found in
            the :class:`LazyRef`'s namespace or the proxied object's namespace
        """
        local_lookups = ('__dict__', '_proxy_loaded', '__unproxy__',
                         '__object__', '_local_lookups', '__proxy_delattr__',
                         '__proxy_setattr__', '__proxy_getattribute__',
                         '_local_lookups', '__str__')
        if name in local_lookups:
            return super(LazyRef, self).__getattribute__(name)
        elif not self._proxy_loaded:
            return super(LazyRef, self).__getattribute__(name)
        return self.__proxy_getattribute__(name)

    def __proxy_getattribute__(self, name):
        """Proxy a getattr call to our proxied object if our proxy has been
        loaded

        :param name: The name of the attribute to retrieve
        """
        if self._proxy_loaded:
            return getattr(self.__object__, name)

    def __delattr__(self, name):
        """If we haven't loaded our proxy object yet, run as normal. If we
        have loaded our proxy there are a few special attributes that we don't
        proxy, otherwise, run a delattr on our proxied object. If we fail to
        find the specified, raise an AttributeError as expected

        :param name: The name of the attribute to delete
        :return: :const:`None`
        :raises AttributeError: If the provided attribute can't be found in
            the :class:`LazyRef`'s namespace or the proxied object's namespace
        """
        if name in self._local_lookups or not self._proxy_loaded:
            return super(LazyRef, self).__delattr__(name)
        return self.__proxy_delattr__(name)

    def __proxy_delattr__(self, name):
        """Proxy a delattr call to our proxied object if our proxy has been
        loaded

        :param name: The name of the attribute to delete
        """
        if self._proxy_loaded:
            return delattr(self.__object__, name)

    def __setattr__(self, name, value):
        """If we haven't loaded our proxy object yet, run as normal. If we
        have loaded our proxy there are a few special attributes that we don't
        proxy, otherwise, run a setattr on our proxied object. If we fail to
        set the specified, raise an AttributeError as expected

        :param name: The name of the attribute to set
        :param value: The value to set *name* to
        :raises AttributeError: If the provided attribute can't be set in
            the :class:`LazyRef`'s namespace or the proxied object's namespace
        """
        if name in self._local_lookups or not self._proxy_loaded:
            return super(LazyRef, self).__setattr__(name, value)
        return self.__proxy_setattr__(name, value)

    def __proxy_setattr__(self, name, value):
        """Proxy a setattr call to our proxied object if our proxy has been
        loaded

        :param name: The name of the attribute to assign
        :param value: The value to assign *name* to
        """
        if self._proxy_loaded:
            return setattr(self.__object__, name, value)

    def __str__(self):
        """Return our default string representation if we haven't loaded our
        proxy yet, otherwise load our proxy's string representation.
        """
        if self._proxy_loaded:
            return str(self.__object__)
        return '<{}: {}>'.format(self.__class__.__name__, self.reference)
    __repr__ = __str__
