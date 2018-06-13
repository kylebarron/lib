#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import symlink, unlink, path, walk, makedirs
from collections import Iterable as Iter
from sys import argv, version_info

def main():
    # dirname = "."
    dirname = path.dirname(path.abspath(argv[0]))
    out     = "all" if len(argv) == 1 else argv[1]
    makedirs_safe(out)
    tolink  = []
    for root, dirs, files in walk(dirname, topdown = True):
        if (dirs == [] and files != []):
            tolink += [root]

    for f in uniquelist(tolink):
        if path.isdir(f) and f.strip().lower() != out:
            dest = path.join(dirname, out, path.basename(f))
            src  = path.relpath(f, path.join(dirname, out))
            symlink_replace(src, dest, target_is_directory = True)


# symlink_replace(path.join(fls, sf), path.join(dirname, "all"))
def symlink_replace(src, dest, **kwargs):
    try:
        symlink(src, dest, **kwargs)
        return dest
    except OSError:
        if path.islink(dest):
            try:
                unlink(dest)
                symlink(src, dest, **kwargs)
                return dest
            except OSError:
                raise
        else:
            raise


try:  # Python 2
    "" is basestring
except NameError:  # Python 3
    basestring = str


def flatten(l):
    if version_info >= (3, 0):
        for el in l:
            if isinstance(el, Iter) and not isinstance(el, (str, bytes)):
                for sub in flatten(el):
                    yield sub
            else:
                yield el
    else:
        for el in l:
            if isinstance(el, Iter) and not isinstance(el, basestring):
                for sub in flatten(el):
                    yield sub
            else:
                yield el


def uniquelist(x):
    return list(set(flatten([x])))


def makedirs_safe(directory):
    try:
        makedirs(directory)
        return directory
    except OSError:
        if not path.isdir(directory):
            raise


if __name__ == "__main__":
    main()
