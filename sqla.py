# -*- coding: utf-8 -*

import logging
logger = logging.getLogger(__file__)
try:
    import sqlalchemy
except ImportError, err:
    #logger.error('SqlAlchemy import not available')
    raise LibraryImportError('SqlAlchemy import not available ({0})'.format(err))

from sqlalchemy.orm import RelationshipProperty, ColumnProperty, SynonymProperty
import sqlalchemy.orm.collections

from sqlalchemy import (Table, Column, ForeignKey, Sequence, desc,
                        UniqueConstraint, and_, or_, MetaData, create_engine,
                        __version__ as sa_version)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper, sessionmaker, scoped_session, validates
from sqlalchemy.orm import relation, backref, deferred, eagerload
import sqlite3

from contextlib import contextmanager

@contextmanager
def managed(sessionClass, auto_flush=False, auto_commit=False, callback=None):
    session = sessionClass()
    session.autoflush = auto_flush
    session.autocommit = auto_commit
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        if isinstance(callback, Callback):
            callback()
        raise
    finally:
        session.close()


@contextmanager
def commit_on_success(session):
    try:
        yield session
        session.commit()
    except:
        raise


class Callback:
    def __init__(self, func, *args, **kwargs):
        if not callable(func):
            raise TypeError("Argument func must be a callable!")

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        try:
            self.func(*self.args, **self.kwargs)
        except:
            # FIXME: silently failing
            pass

default_exclude = None

# Default value for asdict_exclude
default_exclude_underscore = True

# Default value for fromdict_allow_pk if not set
default_fromdict_allow_pk = False



def get_relation_keys(model):
    """Get relation keys for a model

    :returns: List of RelationProperties
    """
    return [k.key for k in model.__mapper__.iterate_properties if
            isinstance(k, RelationshipProperty)]


def get_column_keys(model):
    """Get column keys for a model

    :returns: List of column keys
    """
    return [k.key for k in model.__mapper__.iterate_properties if
            isinstance(k, ColumnProperty)]


def get_synonym_keys(model):
    """Get synonym keys for a model

    :returns: List of keys for synonyms
    """
    return [k.key for k in model.__mapper__.iterate_properties if
            isinstance(k, SynonymProperty)]


def get_primary_key_properties(model):
    """Get the column properties that affects a primary key

    :returns: Set of column keys
    """
    # Find primary keys
    primary_keys = set()
    for k in model.__mapper__.iterate_properties:
        if hasattr(k, 'columns'):
            for c in k.columns:
                if c.primary_key:
                    primary_keys.add(k.key)
    return primary_keys


def asdict(self, exclude=None, exclude_underscore=None, exclude_pk=None, follow=None):
    """Get a dict from a model
    This method can also be set on a class directly.

    :param follow: List or dict of relationships that should be followed. \
            If the parameter is a dict the value should be a dict of \
            keyword arguments.
    :param exclude: List of properties that should be excluded, will be \
            merged with self.dictalchemy_exclude.
    :param exclude_pk: If True any column that refers to the primary key will \
            be excluded.
    :param exclude_underscore: Overides self.exclude_underscore if set

    :raises: :class:`ValueError` if follow contains a non-existent relationship

    :returns: dict

    """
    if follow == None:
        follow = []
    try:
        follow = dict(follow)
    except ValueError:
        follow = dict.fromkeys(list(follow), {})

    exclude = exclude or []
    exclude += getattr(self, 'dictalchemy_exclude', default_exclude) \
        or []
    if exclude_underscore is None:
        exclude_underscore = getattr(self, 'dictalchemy_exclude_underscore', default_exclude_underscore)
    if exclude_underscore:
        # Exclude all properties starting with underscore
        exclude += [k.key for k in self.__mapper__.iterate_properties \
                    if k.key[0] == '_']
    if exclude_pk is True:self.Session = sessionmaker(bind=self.engine)
    exclude += get_primary_key_properties(self)

    columns = get_column_keys(self)
    synonyms = get_synonym_keys(self)
    relations = get_relation_keys(self)

    data = dict([(k, getattr(self, k)) for k in columns + synonyms \
                 if k not in exclude])

    for (k, args) in follow.iteritems():
        if k not in relations:
            raise ValueError( \
                "Key '%r' in parameter 'follow' is not a relations" % \
                k)
        rel = getattr(self, k)
        if hasattr(rel, 'asdict'):
            data.update({k: rel.asdict(**args)})
        elif isinstance(rel, InstrumentedList):
            children = []
            for child in rel:
                if hasattr(child, 'asdict'):
                    children.append(child.asdict(**args))
                else:
                    children.append(dict(child))
            data.update({k: children})

    return data


def fromdict(self, data, exclude=None, exclude_underscore=None, allow_pk=None, follow=None):
    """Update a model from a dict

    This method updates the following properties on a model:

    * Simple columns
    * Synonyms
    * Simple 1-m relationshipsmodel

    :param data: dict of data
    :param exclude: list of properties that should be excluded
    :param exclude_underscore: If True underscore properties will be excluded,\
            if set to None self.dictalchemy_exclude_underscore will be used.
    :param allow_pk: If True any column that refers to the primary key will \
            be excluded. Defaults self.dictalchemy_fromdict_allow_pk or \
            dictable.constants.fromdict_allow_pk
    :param follow: Dict of relations that should be followed, the key is the \
            arguments passed to the relation. Relations only works on simple \
            relations, not on lists.

    :raises: :class:`Exception` If a primary key is in data and \
            allow_pk is False

    :returns nothing:

    """

    if follow == None:
        follow = []
    try:
        follow = dict(follow)
    except ValueError:
        follow = dict.fromkeys(list(follow), {})

    exclude = exclude or []
    exclude += getattr(self, 'dictalchemy_exclude', default_exclude) or []
    if exclude_underscore is None:
        exclude_underscore = getattr(self, 'dictalchemy_exclude_underscore', default_exclude_underscore)

    if exclude_underscore:
        # Exclude all properties starting with underscore
        exclude += [k.key for k in self.__mapper__.iterate_properties \
                    if k.key[0] == '_']

    if allow_pk is None:
        allow_pk = getattr(self, 'dictalchemy_fromdict_allow_pk', default_fromdict_allow_pk)

    columns = get_column_keys(self)
    synonyms = get_synonym_keys(self)
    relations = get_relation_keys(self)
    primary_keys = get_primary_key_properties(self)

    # Update simple data
    for k, v in data.iteritems():
        if not allow_pk and k in primary_keys:
            raise Exception("Primary key(%r) cannot be updated by fromdict."
                            "Set 'dictalchemy_fromdict_allow_pk' to True in your Model"
                            " or pass 'allow_pk=True'." % k)
        if k in columns + synonyms:
            setattr(self, k, v)

    # Update simple relations
    for (k, args) in follow.iteritems():
        if k not in data:
            continue
        if k not in relations:
            raise ValueError( \
                "Key '%r' in parameter 'follow' is not a relations" % \
                k)
        rel = getattr(self, k)
        if hasattr(rel, 'asdict'):
            rel.fromdict(data[k], **args)


def iter(model):
    """iter method for models"""
    for i in model.asdict().iteritems():
        yield i


def make_class_dictable(cls, exclude=default_exclude,
                        exclude_underscore=default_exclude_underscore,
                        fromdict_allow_pk=default_fromdict_allow_pk):
    """Make a class dictable

    Useful for when the Base class is already defined, for example when using
    Flask-SQLAlchemy.

    Warning: This method will overwrite existing attributes if they exists.

    :param exclude: Will be set as dictalchemy_exclude on the class
    :param exclude_underscore: Will be set as dictalchemy_exclude_underscore \
            on the class

    :returns: The class
    """

    setattr(cls, 'dictalchemy_exclude', exclude)
    setattr(cls, 'dictalchemy_exclude_underscore', exclude_underscore)
    setattr(cls, 'dictalchemy_fromdict_allow_pk', fromdict_allow_pk)
    setattr(cls, 'asdict', asdict)
    setattr(cls, 'fromdict', fromdict)
    setattr(cls, '__iter__', iter)
    return cls


class SAContext(object):
    '''Convenient SQLALchemy initialization.

    Usage::

        from bag.sqlalchemy.context import *
        # The above single statement imports most if not all of
        # what you need to define a model and use it.

        sa = SAContext()  # you can provide create_engine's args here
        # Now define your model with sa.metadata and sa.base

        # Add a working engine:
        sa.create_engine('sqlite:///db.sqlite3', echo=False)
        # or...
        sa.use_memory()  # This one immediately creates the tables.

        # Now use it:
        sa.drop_tables().create_tables()
        session = sa.Session()
        # Use that session...
        session.commit()

        # You can also create a copy of sa, bound to another engine:
        sa2 = sa.clone('sqlite://')
    '''
    __slots__ = ('metadata', 'base', 'dbURI', 'engine', 'Session')

    def __init__(self, *args, **kwargs):

        #if self.debugFlag:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.dialects').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.orm').setLevel(logging.DEBUG)

        self.echo=False

        #if self.verbose:
        #    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        #    self.echo=True

        #self.metadata = MetaData()
        #self.base = declarative_base(metadata=self.metadata)

        #if dbURI:
        #   self.create_engine(dbURI, echo=True, **kwargs)
        self.base = model.Base
        self.metadata = model.metadata


    def connect_databases(self, dbList):
        conn = None
        for ndx, dbPath in enumerate(dbList):
            if ndx == 0:
                conn = sqlite3.connect(dbPath)
            else:
                conn.execute("ATTACH DATABASE '{0}' AS 'db{1}'".format(dbPath, ndx))

        print conn
        cur = conn.cursor()
        cur.execute('PRAGMA database_list;')
        print cur.fetchall()


        return conn


    def setup_attached_engine(self, dbURI, dbList):

        def connect_databases(dbList):

            initDB = dbList.pop()
            conn = sqlite3.connect(initDB)
            for ndx, dbPath in enumerate(dbList):
                conn.execute("ATTACH DATABASE '{0}' AS 'db{1}'".format(dbPath, ndx))

            cur = conn.cursor()
            cur.execute('PRAGMA database_list;')
            print cur.fetchall()

            return conn

        self.engine = create_engine(dbURI, echo=True, creator=connect_databases(dbList))
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine)
        #self.Session = scoped_session(sessionmaker(bind=self.engine))
        return self


    # cur.execute('PRAGMA database_list') 3rd parameter is database

    def create_engine(self, dbURI, echo=False, **kwargs):
        self.dbURI = dbURI
        self.engine = create_engine(self.dbURI, echo=echo, **kwargs)
        self.metadata.bind = self.engine
        #self.Session = sessionmaker(bind=self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        return self

    def use_memory(self, **kwargs):
        self.create_engine('sqlite:///:memory:', **kwargs)
        self.create_tables()
        return self

    def drop_tables(self, tables=None):
        self.metadata.drop_all(tables=tables, bind=self.engine)
        #self.metadata.drop_all(tables=tables, bind=self.engine)
        return self

    def create_tables(self, tables=None):
        self.metadata.create_all(tables=tables, bind=self.engine)
        #self.metadata.create_all(tables=tables, bind=self.engine)
        return self

    def tables_in(self, adict):
        '''Returns a list containing the tables in the context *adict*. Usage::
           tables = sa.tables_in(globals())
        '''
        tables = []
        for val in adict.values():
            if hasattr(val, '__base__') and val.__base__ == self.Base:
                tables.append(val.__table__)
            elif isinstance(val, Table):
                tables.append(val)
        return tables

    def clone(self, *args, **kwargs):
        from copy import copy
        o = copy(self, *args, **kwargs)
        return o

