# -*- coding: utf-8 -*

import os
import logging
import re
import hashlib

logger = logging.getLogger(__file__)


def bytesFromFile(fileName, chunkSize=8192):
    with open(fileName, 'rb') as f:
        while True:
            chunk = f.read(chunkSize)
            if chunk:
                for b in chunk:
                    yield b
                else:
                    break

def chunkFromFile(fileName, chunkSize=8192):
    with open(fileName, 'rb') as f:
        while True:
            chunk = f.read(chunkSize)
            if chunk:
                yield chunk
            else:
                break


def md5FileHash(filePath):
    md5 = hashlib.md5()

    if os.path.exists(filePath):
        with open(filePath, 'rb') as fp:
            md5.update(fp.read())

        return md5.hexdigest().upper()

    else:
        return None




def sha1hashFile(filePath):
    sha = hashlib.sha1()

    if os.path.isfile(filePath):
        with open(filePath, 'rb') as fp:
            sha.update(fp.read())

        return sha.hexdigest().upper()
    else:
        return None



def sha1hashStr(str):
    sha1 = hashlib.sha1()
    sha1.update(str)
    return sha1.hexdigest()



def sha256FileHash(filePath):
    sha = hashlib.sha256()

    if os.path.exists(filePath):
        with open(filePath, 'rb') as fp:
            sha.update(fp.read())

        return sha.hexdigest().upper()

    else:
        return None



def renameFile(src, dst, verbose):
    try:
        os.rename(src, dst)
        if verbose:
            print 'Move file from %s to %s' % (src, dst)
        return True
    except OSError:
        pass


def replaceFile(src, dst, verbose):
    try:
        os.remove(dst)
        os.rename(src, dst)
        if verbose:
            print 'Replace file %s with %s' % (dst, src)

    except OSError:
        pass


def removeFile(src, verbose):
    try:
        os.remove(src)
        if verbose:
            print 'Remove file %s' % src
        return True
    except OSError:
        pass



def convert(data):
    if isinstance(data, unicode):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data





def ifElse(a, predicate, b):
    """Return *a* if *predicate* evaluates to True; else *b*.

    This emulates the logic of the if..else ternary operator introduced in
    Python 2.5.
    """
    if predicate:
        return a
    else:
        return b

def is_method_of(method, obj):
    """Return True if *method* is a method of *obj*.

    *method* should be a method on a class instance; *obj* should be an instance
    of a class.
    """
    # Check for both 'im_self' (Python < 3.0) and '__self__' (Python >= 3.0).
    cls = obj.__class__
    mainObj = getattr(method, "im_self", getattr(method, "__self__", None))
    return isinstance(mainObj, cls)





def requireVersion(version1, version2):
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split('.')]
    return cmp(normalize(version1), normalize(version2))



def bin(a):
    s=''
    t={'0':'000','1':'001','2':'010','3':'011','4':'100','5':'101','6':'110','7':'111'}

    for c in oct(a)[1:]:
        s+=t[c]

    return s

import json, datetime, collections

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):

        if isinstance(obj, collections.Iterable):
            chunks = json._iterencode_list(json.value, json._current_indent_level)

        elif isinstance(obj, datetime):
            return obj.datetime.strftime('%Y-%m-%dT%H:%M:%S')

        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)




def contains(small, big):
    for i in xrange(len(big) - len(small)+1):
        for j in xrange(len(small)):
            if big[i+j] != small[j]:
                break
        else:
            return i, i+len(small)
    return False




class Stats:
    def __init__(self, name=None, verbose=False):
        if name:
            self.name = name
        else:
            self.name = "Stats"
        self.statusDict = dict()
        self.verbose = verbose
        self.entry = 0

    def update(self, event):
        if self.verbose:
            print(event)

        #if self.entry % 100 == 0:
        #    sys.stdout.write('.')
        self.entry += 1

        if self.statusDict.has_key(event):
            self.statusDict[event] += 1
        else:
            self.statusDict[event] = 1

    def printStats(self):
        for key in self.statusDict.iterkeys():
            print("{0} : {1} - {2}".format(self.name, key, self.statusDict[key]))

    def stringStats(self):
        statStr = str("\n")
        for key in self.statusDict.iterkeys():
            statStr += "{0} : {1}\n".format(key, self.statusDict[key])

        return statStr

    def logStats(self, filename=None):
        if filename:
            logFile = filename
        else:
            logFile = '{0}.stats'.format(self.name)
        with open(logFile, 'a') as f:
            for key in self.statusDict.iterkeys():
                f.write("{0} : {1}\n".format(key, self.statusDict[key]))


#=========================================================================
# tracer
#=========================================================================

import functools
import inspect
import sys


def name(item):
  """Return an item's name."""
  return item.__name__


def is_classmethod(instancemethod):
  """Determine if an instancemethod is a classmethod."""
  return instancemethod.im_self is not None


def is_class_private_name(member_name):
  """Determine if a name is a class private name."""
  # Exclude system defined names such as __init__, __add__ etc
  return member_name.startswith("__") and not member_name.endswith("__")


def method_name(method):
  """Return a method's name.

  This function returns the name the method is accessed by from
  outside the class (i.e. it prefixes "private" methods appropriately).
  """
  mname = name(method)
  if is_class_private_name(mname):
    mname = "_%s%s" % (name(method.im_class), mname)
  return mname


def format_arg_value(arg_val):
  """Return a string representing a (name, value) pair.

  >>> format_arg_value(("x", (1, 2, 3)))
  "x=(1, 2, 3)"
  """
  arg, val = arg_val
  return "%s=%r" % (arg, val)


def trace(func, write=sys.stdout.write):
  """Echo calls to a function.

  Returns a decorated version of the input function which "tracees" calls
  made to it by writing out the function's name and the arguments it was
  called with.
  """
  # Unpack function's arg count, arg names, arg defaults
  code = func.func_code
  argcount = code.co_argcount
  argnames = code.co_varnames[:argcount]
  fn_defaults = func.func_defaults or list()
  argdefs = dict(zip(argnames[-len(fn_defaults):], fn_defaults))

  @functools.wraps(func)
  def wrapped(*v, **k):
    """Collect function arguments by chaining together positional,
defaulted, extra positional and keyword arguments."""
    positional = map(format_arg_value, zip(argnames, v))
    defaulted = [format_arg_value((a, argdefs[a]))
                 for a in argnames[len(v):] if a not in k]
    nameless = map(repr, v[argcount:])
    keyword = map(format_arg_value, k.items())
    args = positional + defaulted + nameless + keyword
    write("%s(%s)\n" % (name(func), ", ".join(args)))
    return func(*v, **k)

  return wrapped


def trace_instancemethod(klass, method, write=sys.stdout.write):
  """Change an instancemethod so that calls to it are traceed.

  Replacing a classmethod is a little more tricky.
  See: http://www.python.org/doc/current/ref/types.html
  """
  mname = method_name(method)
  never_trace = "__str__", "__repr__",  # Avoid recursion printing method calls
  if mname in never_trace:
    pass
  elif is_classmethod(method):
    setattr(klass, mname, classmethod(trace(method.im_func, write)))
  else:
    setattr(klass, mname, trace(method, write))


def trace_class(klass, write=sys.stdout.write):
  """Echo calls to class methods and static functions
  """
  for _, method in inspect.getmembers(klass, inspect.ismethod):
    trace_instancemethod(klass, method, write)
  for _, func in inspect.getmembers(klass, inspect.isfunction):
    setattr(klass, name(func), staticmethod(trace(func, write)))


def trace_module(mod, write=sys.stdout.write):
  """Echo calls to functions and methods in a module.
  """
  for fname, func in inspect.getmembers(mod, inspect.isfunction):
    setattr(mod, fname, trace(func, write))
  for _, klass in inspect.getmembers(mod, inspect.isclass):
    trace_class(klass, write)





FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])

def hexdump(src, length=16, prefix=''):
    """
        Print hexdump of string

        >>> print hexdump("abcd\x00" * 4)
        0000  61 62 63 64 00 61 62 63  64 00 61 62 63 64 00 61  abcd.abc d.abcd.a
        0010  62 63 64 00                                       bcd.
    """
    n = 0
    left = length / 2
    right = length - left
    result= []
    while src:
        s,src = src[:length],src[length:]
        l,r = s[:left],s[left:]
        hexa = "%-*s" % (left*3,' '.join(["%02x"%ord(x) for x in l]))
        hexb = "%-*s" % (right*3,' '.join(["%02x"%ord(x) for x in r]))
        lf = l.translate(FILTER)
        rf = r.translate(FILTER)
        result.append("%s%04x  %s %s %s %s" % (prefix, n, hexa, hexb, lf, rf))
        n += length
    return "\n".join(result)
