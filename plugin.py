# -*- coding: utf-8 -*
import os
import sys
from pathlib import Path

current_path = Path('.')

import configparser
import subprocess
import argparse

import importlib
import logging


logger = logging.getLogger(__name__)


class Error(Exception):
    '''A base class for all exceptions the module throws.'''
    def __init__(self, error, *args, **kwargs):
        super(Error, self).__init__(
            error.format(*args, **kwargs) if args or kwargs else error)

class Abort(Error):
    '''Raised when an application exits unexpectedly.
    '''
    def __init__(self, status):
        self.status = status
        message = 'Application terminated {!s}'.format(self.status)
        super(Abort, self).__init__(message, self.status)


class PluginAbort(Abort):
    """ Exception raised for errors when executing
    """
    def __init__(self, name, msg):
        self.name = name
        self.msg = msg

    def __str__(self):
        return "Plugin {0} error: {1}".format(self.name, self.msg)


class PluginImportError(Error):
    """ Exception raised for errors when loading a plugin
    """
    def __init__(self, name, msg):
        self.name = name
        self.msg = msg

    def __str__(self):
        return "Plugin {0} failed: {1}".format(self.name, self.msg)




class Plugin(object):
    """ Plugin help information for this command...
    """

    def __init__(self, name, *args, **kwargs):
        self.name = name

        self.log = logging.getLogger(self.name)
        self.log.debug('Plugin class called from {0}'.format( self.name))

    def __repr__(self):
        return "Plugin: {0}:{1}".format(self.name, type(self))

    def help(self):
        return self.__doc__

    def setup(self, parser):
        """called before the plugin is asked to do anything"""
        raise NotImplementedError

    def execute(self, params):
        """ execute plugin code """
        raise NotImplementedError




class PluginManager(object):
    _instance = []
    registry = {}

    def __init__(self, options):
        self.blacklist = []
        if 'blacklist' in options:
            self.blacklist.append(options.blacklist)

        self.plugin_path =  current_path.absolute()
        self.log = logging.getLogger(self.__class__.__name__)
        self.initialize_plugins()

    def initialize_plugins(self):
      
        for plug_path in self.plugin_path.glob('*_plugin.py'):
            plug_name = plug_path.stem
            self.log.info('Initialize plug_name: {0!s}'.format(plug_name))

            if plug_name in self.blacklist:
                self.log.warn('Plugin: {!s} blacklisted'.format(plug_name))
                continue

            plug_class = self.get_class_name(plug_name)

            try:
                if plug_path not in sys.path:
                    sys.path.append(plug_path)

                if plug_name in type(self).registry.keys():
                    continue

                modObj = importlib.import_module(plug_name, plug_path.absolute())

                self.log.info('Imported module {0} as {1} ({2}) and added to registry'.format(plug_name, modObj, type(modObj)))
                type(self).registry['{!s}'.format(plug_class)] = modObj

            except PluginImportError as err:
                self.log.error('PluginImportError:{0}-{1}'.format(dir, err))

            except Exception as err:
                self.log.exception(err)


    def get_class_name(self, module_name):
        """Return the class name from a plugin name"""
        output = ""
        words = module_name.split("_")
        for word in words:
            output += word.title()
        return output


    def update_plugin_registry(self):
        num = self.findAllPlugins()
        return self.get_plugin_registry()

    def get_plugin_registry(self):
        return type(self).registry

    def findAllPlugins(self):
        pluginList = Plugin.__subclasses__()
        pluginNum = 0
        self.log.debug('++++ Found Plugin List: {0}'.format(str(pluginList)))
        for plugin in pluginList:
            if plugin in type(self).registry.keys():
                continue

            type(self).registry['{!s}'.format(self.get_class_name(plugin))] = plugin

            pluginNum += 1

        self.log.debug(pluginList)

        return pluginNum

