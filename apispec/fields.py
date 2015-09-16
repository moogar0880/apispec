# -*- coding: utf-8 -*-
"""The fields module contains an assortment of Descriptor types that allow us
to force rules provided by an API spec onto the attributes of the generated
classes
"""
import re

__all__ = ['Descriptor', 'Typed', 'Integer', 'SizedInteger', 'Float',
           'SizedFloat', 'String', 'Bytes', 'Boolean', 'Regex', 'Date',
           'DateTime', 'Array']


class Descriptor:
    """Base descriptor type. Provides the ability to attach a setter and
    getter to instance attributes of a class
    """

    def __init__(self, name=None, default=None):
        """Create a new :class:`Descriptor` type

        :param name: The name of the attribute mapped to this descriptor
        :param default: The default value to return for this descriptor
        """
        self.name = name
        self.default = default

    def __get__(self, instance, owner):
        """Return the private variable proxied by this descriptor"""
        return getattr(instance, '_' + self.name, self.default)

    def __set__(self, instance, value):
        """Set the private variable proxied by this descriptor"""
        return setattr(instance, '_' + self.name, value)

    def __delete__(self, instance):
        raise AttributeError("Can't delete")


class Typed(Descriptor):
    """Descriptor type capable of performing type checking of the value
    proxied by this descriptor. A ValueError will be raised if you attempt to
    set this descriptor to a different type
    """
    ty = object

    def __init__(self, *args, default=None, **kwargs):
        """Create a new typed descriptor instance

        :param default: See :class:`Descriptor`. Used here to attempt to set
            the default value if not specified
        """
        if default is None:
            try:
                default = self.ty()
            except TypeError:
                # Try to default if we have a type that doesn't require
                # aruments, (ie a builtin), otherwise move on and let it
                # default as :const:`None`
                pass
        super(Typed, self).__init__(*args, default=default, **kwargs)

    def __set__(self, instance, value):
        """Attempt to set the instances variable to *value*. Fail if the types
        don't match
        """
        if not isinstance(value, self.ty):
            raise TypeError('Expected %s, got %s' % (self.ty, type(value)))
        super(Typed, self).__set__(instance, value)


class Sized(Descriptor):
    """Descriptor responsible for enforcing a valid range of values on a
    the underlying attribute
    """

    def __init__(self, *args, minimum=None, maximum=None, **kwargs):
        """Create a sized descriptor instance

        :param minimum: The minimum allowed value for the underlying attribute
        :param maximum: The maximum allowed value for the underlying attribute
        """
        self.maximum, self.minimum = maximum, minimum
        super(Sized, self).__init__(*args, **kwargs)

    def __set__(self, instance, value):
        """Perform bounds checking against the minimum and maximum value.

        :raises ValueError: If *value* is outside the range of this descriptor
        """
        if self.minimum is not None and value <= self.minimum:
            raise ValueError('Value %s is too small. Minimum is %s' %
                             (str(value), str(self.minimum)))
        if self.maximum is not None and value >= self.maximum:
            raise ValueError('Value %s is too large. Maximum is %s' %
                             (str(value), str(self.minimum)))
        super(Sized, self).__set__(instance, value)


class Integer(Typed):
    """Type check for :const:`int` values"""
    ty = int


class SizedInteger(Integer, Sized):
    """Type check for :const:`int` values within a certain range"""
    pass


class Float(Typed):
    """Type check for :const:`float` values"""
    ty = float


class SizedFloat(Float, Sized):
    """Type check for :const:`float` values within a certain range"""
    pass


class String(Typed):
    """Type check for :const:`str` values"""
    ty = str


class Bytes(Typed):
    """Type check for :const:`bytes` values"""
    ty = bytes


class Boolean(Typed):
    """Type check for :const:`bool` values"""
    ty = bool


# Pattern matching
class Regex(Descriptor):
    """Check that the provided stirng matches the provided regex"""

    def __init__(self, *args, pattern, **kwargs):
        """Create a new regex descriptor and store it's compiled pattern"""
        self.pattern = re.compile(pattern)
        super(Regex, self).__init__(*args, **kwargs)

    def __set__(self, instance, value):
        """Pass the assignment up the chain only if the provided value matches
        this descriptors pattern
        """
        if not self.pattern.match(value):
            raise ValueError('Invalid pattern. %s did not match %s' %
                             (value, self.pattern))
        super(Regex, self).__set__(instance, value)


class Date(Regex):
    pass


class DateTime(Regex):
    pass


# Collection validation
class Array(Typed):
    """Type check for :class:`TypedList` (:const:`list`) values. This
    :class:`Descriptor` type allows us to set definition attributes that
    are lists of either builtin types or LazyRef'd user defined types
    """

    def __init__(self, *args, items, **kwargs):
        from .models import LazyRef
        if '$ref' in items:
            default = TypedList(ref=LazyRef(items['$ref']))
        else:
            default = TypedList(ref=self.descriptor_by_name(items['type']))
        self.ty = type(default)
        super(Array, self).__init__(*args, default=default, **kwargs)

    def __set__(self, instance, value):
        val = getattr(instance, '_' + self.name, self.default)
        val.extend(value)
        super(Array, self).__set__(instance, val)

    @staticmethod
    def descriptor_by_name(name):
        """Return the descriptor for the provided type *name*"""
        subs = Descriptor.__subclasses__()
        for sub in subs:
            if sub.ty.__name__ == name:
                return sub
        # return Descriptor
        raise ValueError('No Descriptor for unsupported type: %s' % name)


class TypedList(list):

    def __init__(self, ref, iterable=()):
        self.ref = ref
        valid = [isinstance(x, self.ty) for x in iterable]
        if not all(valid):
            self.raise_()
        super(TypedList, self).__init__(iterable)

    def append(self, p_object):
        if not isinstance(p_object, self.ty):
            self.raise_()
        super(TypedList, self).append(p_object)

    def extend(self, iterable):
        super(TypedList, self).extend(TypedList(self.ref, iterable))

    def insert(self, index, p_object):
        if not isinstance(p_object, self.ty):
            self.raise_()
        super(TypedList, self).insert(index, p_object)

    def raise_(self):
        raise TypeError('This list may only contain instances of %s' % self.ty)

    @property
    def ty(self):
        return self.ref.__object__
