# Copyright 2013 Christoph Reiter
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

import os
import types
import inspect

from .klass import GObjectGenerator, InterfaceGenerator
from .flags import FlagsGenerator
from .constants import ConstantsGenerator
from .function import FunctionGenerator
from .enum import EnumGenerator
from .repo import Repository
from .structures import StructGenerator
from .union import UnionGenerator
from . import util


def import_namespace(namespace, version):
    import gi
    try:
        gi.require_version(namespace, version)
    except ValueError as e:
        raise ImportError(e)
    module = __import__("gi.repository", fromlist=[namespace])
    return getattr(module, namespace)


class ModuleGenerator(util.Generator):

    def __init__(self, dir_, namespace, version):
        # create the basic package structure
        self.namespace = namespace
        self.version = version

        nick = "%s_%s" % (namespace, version)
        self._index_name = os.path.join(nick, "index")
        self._module_path = os.path.join(dir_, nick)

    def get_names(self):
        return [self._index_name]

    def _add_dependency(self, module, name, version):
        """Import the module in the generated code"""
        module.write("import pgi\n")
        module.write("pgi.set_backend('ctypes,null')\n")
        module.write("pgi.require_version('%s', '%s')\n" % (name, version))
        module.write("from pgi.repository import %s\n" % name)

    def write(self):

        namespace, version = self.namespace, self.version

        os.mkdir(self._module_path)
        module_path = os.path.join(self._module_path, namespace + ".py")
        module = open(module_path, "wb")

        # utf-8 encoded .py
        module.write("# -*- coding: utf-8 -*-\n")
        # for references to the real module
        self._add_dependency(module, namespace, version)
        # basic deps
        self._add_dependency(module, "GObject", "2.0")
        self._add_dependency(module, "Gio", "2.0")
        self._add_dependency(module, "GLib", "2.0")
        self._add_dependency(module, "Atk", "1.0")

        try:
            mod = import_namespace(namespace, version)
        except ImportError:
            print "Couldn't import %s-%s, skipping" % (namespace, version)
            return

        repo = Repository(namespace, version)

        for dep in repo.get_dependencies():
            self._add_dependency(module, *dep)

        from gi.repository import GObject, Gtk, GLib
        class_base = GObject.Object
        iface_base = GObject.GInterface
        flags_base = GObject.GFlags
        enum_base = GObject.GEnum
        struct_base = Gtk.AccelKey.__mro__[-2]  # FIXME
        union_base = GLib.DoubleIEEE754.__mro__[-2]  # FIXME

        obj_gen = GObjectGenerator(self._module_path, module)
        iface_gen = InterfaceGenerator(self._module_path, module)
        flags_gen = FlagsGenerator(self._module_path, module)
        enums_gen = EnumGenerator(self._module_path, module)
        func_gen = FunctionGenerator(self._module_path, module)
        struct_gen = StructGenerator(self._module_path, module)
        union_gen = UnionGenerator(self._module_path, module)
        const_gen = ConstantsGenerator(self._module_path, module)

        def is_method_owner(cls, method_name):
            for base in util.merge_in_overrides(cls):
                if hasattr(base, method_name):
                    return False
            return True

        for key in dir(mod):
            if key.startswith("_"):
                continue
            obj = getattr(mod, key)

            # skip classes which are renamed
            if inspect.isclass(obj):
                if obj.__name__ != key:
                    print "Skipping %s: renamed clas" % key
                    continue
                if obj.__module__ != namespace:
                    print  obj.__module__, namespace
                    print "Skipping %s: originated from other namespace" % key
                    continue

            name = "%s.%s" % (namespace, key)

            if isinstance(obj, types.FunctionType):
                code = repo.parse_function(name, None, obj)
                if code:
                    func_gen.add_function(name, code)
            elif inspect.isclass(obj):
                if issubclass(obj, (iface_base, class_base)):

                    if issubclass(obj, class_base):
                        class_gen = obj_gen
                    else:
                        class_gen = iface_gen

                    code = repo.parse_class(name, obj, add_bases=True)
                    class_gen.add_class(obj, code)

                    code = repo.parse_properties(obj)
                    class_gen.add_properties(obj, code)

                    code = repo.parse_signals(obj)
                    class_gen.add_signals(obj, code)

                    for attr in dir(obj):
                        if attr.startswith("_"):
                            continue

                        if not is_method_owner(obj, attr):
                            continue

                        try:
                            attr_obj = getattr(obj, attr)
                        except NotImplementedError:
                            # FIXME.. pgi exposes methods it can't compile
                            continue

                        if callable(attr_obj):
                            func_key = name + "." + attr
                            code = repo.parse_function(func_key, obj, attr_obj)
                            if code:
                                class_gen.add_method(obj, attr_obj, code)

                elif issubclass(obj, flags_base):
                    code = repo.parse_flags(name, obj)
                    flags_gen.add_flags(obj, code)
                elif issubclass(obj, enum_base):
                    code = repo.parse_flags(name, obj)
                    enums_gen.add_enum(obj, code)
                elif issubclass(obj, (struct_base, union_base)):
                    # Hide FooPrivate if Foo exists
                    if key.endswith("Private") and hasattr(mod, key[:-7]):
                        continue
                    code = repo.parse_class(name, obj, add_bases=True)

                    if issubclass(obj, struct_base):
                        gen = struct_gen
                        struct_gen.add_struct(obj, code)
                    else:
                        gen = union_gen
                        union_gen.add_union(obj, code)

                    for attr in dir(obj):
                        if attr.startswith("_"):
                            continue

                        if not is_method_owner(obj, attr):
                            continue

                        try:
                            attr_obj = getattr(obj, attr)
                        except NotImplementedError:
                            # FIXME.. pgi exposes methods it can't compile
                            continue

                        if callable(attr_obj):
                            func_key = name + "." + attr
                            code = repo.parse_function(func_key, obj, attr_obj)
                            if code:
                                gen.add_method(obj, attr_obj, code)
                        else:
                            # fields
                            pass
                else:
                    # unions..
                    code = repo.parse_class(name, obj)
                    if code:
                        obj_gen.add_class(obj, code)
            else:
                code = repo.parse_constant(name)
                if code:
                    const_gen.add_constant(name, code)

        handle = open(os.path.join(self._module_path, "index.rst"),  "wb")

        title = "%s %s" % (namespace, version)
        handle.write(title + "\n")
        handle.write(len(title) * "=" + "\n")

        handle.write("""
.. toctree::
    :maxdepth: 1

""")

        gens = [func_gen, iface_gen, obj_gen, struct_gen, union_gen,
                flags_gen, enums_gen, const_gen]
        for gen in gens:
            if gen.is_empty():
                continue
            for name in gen.get_names():
                handle.write("    %s\n" % name)
            gen.write()

        module.close()

        # make sure the generated code is valid python
        with open(module.name, "rb") as h:
            exec h.read() in {}