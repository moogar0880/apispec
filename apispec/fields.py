# -*- coding: utf-8 -*-
import re

__all__ = ['Descriptor', 'Typed', 'Integer', 'SizedInteger', 'Float',
           'SizedFloat', 'String', 'Bytes', 'Boolean', 'Regex', 'Date',
           'DateTime', 'Array']


class Descriptor:
    def __init__(self, name=None, default=None):
        self.name = name
        self.value = default

    def __get__(self, instance, owner):
        return self.value

    def __set__(self, instance, value):
        self.value = value

    def __delete__(self, instance):
        raise AttributeError("Can't delete")


class Typed(Descriptor):
    ty = object

    def __init__(self, *args, default=None, **kwargs):
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
        if not isinstance(value, self.ty):
            raise TypeError('Expected %s' % self.ty)
        super(Typed, self).__set__(instance, value)


class Sized(Descriptor):
    def __init__(self, *args, minimum=None, maximum=None, **kwargs):
        self.maximum, self.minimum = maximum, minimum
        super(Sized, self).__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if self.minimum is not None and value <= self.minimum:
            raise ValueError('Value %s is too small. Minimum is %s' %
                             (str(value), str(self.minimum)))
        if self.maximum is not None and value >= self.maximum:
            raise ValueError('Value %s is too large. Maximum is %s' %
                             (str(value), str(self.minimum)))
        super(Sized, self).__set__(instance, value)


class Integer(Typed):
    ty = int


class SizedInteger(Integer, Sized):
    pass


class Float(Typed):
    ty = float


class SizedFloat(Float, Sized):
    pass


class String(Typed):
    ty = str


class Bytes(Typed):
    ty = bytes


class Boolean(Typed):
    ty = bool


class Array(Typed):
    def __init__(self, *args, items, **kwargs):
        from .models import LazyRef
        default = TypedList(ref=LazyRef(items['$ref']))
        self.ty = type(default)
        super(Array, self).__init__(*args, default=default, **kwargs)

    def __set__(self, instance, value):
        self.value.extend(value)
        super(Array, self).__set__(instance, self.value)


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


# Pattern matching
class Regex(Descriptor):
    def __init__(self, *args, pat, **kwargs):
        self.pat = re.compile(pat)
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if not self.pat.match(value):
            raise ValueError('Invalid string')
        super().__set__(instance, value)


class Date(Regex):
    pass


class DateTime(Regex):
    pass
