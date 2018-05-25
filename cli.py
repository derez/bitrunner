# -*- coding: utf-8 -*

import os
import sys
from pathlib import Path

current_path = Path('.')

import configparser
import logging
import logging.handlers
import logging.config
from logging import Formatter, StreamHandler
import subprocess
import argparse
import ast

import logging_tree 
import importlib
import logging

from plugin import PluginManager

if not sys.version_info[0:2] == (3, 6):
    print("Code written for Python 3.6 or higher")
    sys.exit(1)

__version__ = '0.2'
__description__ = 'Prototype execution engine'
__author__ = 'Danny Walker [dwalker@digital-tradecraft.com]'


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


class CLI(object):
    '''CLI module.
    '''
    name = 'bitrunner'
    commands = {}
    plugins = {}

    def __init__(self, name=None, **kwargs):

        if name:
            self.name = name
        else:
            self.name = type(self).name

        self.log = logging.getLogger(self.name)
        self.log.info('Initialize cli')
        self.unknown_args = None

        global_parser = self.global_parser()
        # pre-parse from global_parser as well as config file and use for commands
        self.pre_parser = argparse.ArgumentParser(add_help=False, parents=[global_parser])
        # specifically parsing arguments from associated config file if any
        #self.options = argparse.Namespace()
        self.options, self.unknown = self.pre_parser.parse_known_args( )

        self.setup_logger(self.options.logfile, self.options.verbose)

        # then set up the real parser, cloning the initial one
        self.parser = argparse.ArgumentParser(parents=[self.pre_parser], add_help=True,
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        if self.unknown:
            if '-h' or '-?' in self.unknown:
                self.parser.print_help()
                sys.exit(1)
            self.log.warn('Not parsing unknown arguments: {!s}'.format(self.unknown))


        # check for application configs and parse
        app_config = current_path.absolute().joinpath('{0}.conf'.format(self.name))
        self.read_config(app_config)

        # check for user config parameter and parse
        if self.options.config:
            self.read_config(self.options.config)

        self.plugin_manager = PluginManager(self.options)

        self.setup_plugins()
        self.log.debug('Current Params: {!s}'.format(self.options))
        self.log.info('Complete CLI initialization')


    def global_parser(self):
        
        default_logfile = '{0}.log'.format(self.name)
        parser = argparse.ArgumentParser(description=self.__doc__, add_help=False,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('--config', help='Parse a local configuration file.')
        parser.add_argument('--version', action='version', version='%(prog)s {!s}'.format(__version__))

        parser.add_argument('--logfile', default=default_logfile, action='store', help='Log to file')
        parser.add_argument('-v', '--verbose', default=0, action='count', help='Raise the verbosity')
        parser.add_argument('--profile', action='store_true', help='Profile application')
        parser.add_argument('--debug', action='store_true', help='Debug')
       
        return parser

    def setup_logger(self, logFile=None, verbose=0):
        # reconfigure root logger based on user input unless above flag thrown
        log = logging.getLogger()
        #TODO: review this....
        #  continue to keep root logger at DEBUG and allow each handler to control its own settings.
        #log.setLevel(logging.DEBUG)

        level = logging.ERROR - (10 * verbose)
        # Critical 50  Error 40  Warning 30  Info 20  Debug 10  NotSet 0

        if level >= logging.CRITICAL:
            level = logging.CRITICAL
        elif level <= logging.NOTSET:
            level = logging.DEBUG

        log.setLevel(level)

        stream_handler = StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        log.addHandler(stream_handler)

        #if logFile:
        #    file_handler = logging.handlers.RotatingFileHandler(logFile, maxBytes=102400, backupCount=5)
        #    message_format = '%(asctime)s [%(process)d] %(name)-10s %(levelname)-8s %(message)s'
        #    date_format = '%Y-%m-%d %H:%M:%S'
        #    formatter = logging.Formatter(fmt=message_format, datefmt=date_format)
        #    file_handler.setFormatter(formatter)
            #Set logging level for file handler
        #    file_handler.setLevel(logging.INFO)
        #    log.addHandler(file_handler)


    def read_config(self, configName=None):
        try:
            if not configName:
                return 
            
            _config = configparser.ConfigParser(strict=True)
            configPath = os.path.join(current_path.absolute(), configName)
            if os.path.isfile(configPath):
                _config.read(configPath)
                self.log.info('Added params from config file at {0}'.format(configPath))
                bools = ['True','true','TRUE','False','false','FALSE','yes','no','YES','NO','Yes','No']

                if _config.has_section('LOGGING'):
                    log_dict = ast.literal_eval(_config.get('LOGGING', 'conf', raw=True))
                    logging.config.dictConfig(log_dict)

                else:
                    for sect in _config.sections():
                        for key, value in _config.items(sect):
                            if value in bools: 
                                #config_dict[key] = _config.getboolean(sect, key)
                                setattr(self.options, key, _config.getboolean(sect, key))
                            else:
                                #config_dict[key] = value
                                setattr(self.options, key, value)
                    
                
                self.log.debug('Namespace {!s}'.format(self.options))

        # If no such file
        except IOError:
            self.log.error('No config file found at {0}'.format(configPath))

        except configparser.Error as err:
            self.log.error('Config {0!s} failed: {1!r}'.format(configName, err))


    def setup_plugins(self):
        '''
        Add in external plugins
        '''
        self.subparsers = self.parser.add_subparsers(title='plugins', help='Following plugins are available:')

        plugin_dict = self.plugin_manager.get_plugin_registry()

        if not plugin_dict:
            self.log.warn('No plugins were available!')
            return

        else:
            self.log.info('Plugins: {0!s}'.format(plugin_dict))

        for plugin_class, plugin_module in plugin_dict.items():
            try:
                assert isinstance(plugin_module, object)
                
                plugin_class = getattr(plugin_module, plugin_class)
                plugin = plugin_class()
                plugin_config_file = plugin.get_config_file()
                self.log.debug('Added params from plugin file at {0}'.format(plugin_config_file))

                #plugin_args = {}
                self.read_config(plugin_config_file)

                parser = self.subparsers.add_parser(plugin.name, help=plugin.__doc__)

                parser.set_defaults(execute=plugin.execute)
                #parser.set_defaults(**plugin_args)

                plugin.setup(parser)
                self.log.info('Plugin Intialized: {0}'.format(plugin.name))

            except Exception as err:
                self.log.warn('Plugin Failed To Load: {0} - {1!r}'.format(plugin.name, err))



    def pre_execute(self):
        '''
        Perform any last-minute configuration.
        '''
        self.log.debug('Params before parsing in pre_execute:{0}'.format(self.options))

        try:
            self.parser.parse_args(namespace=self.options)
            self.log.debug('Params after parsing in pre_execute:{0}'.format(self.options))
            if self.unknown_args:
                self.log.debug('Unknown Arguments after parsing in pre_execute:{0}'.format(self.unknown_args))

        except SystemExit:
            sys.exit(0)

        except Exception as err:
            raise Abort(err)


    def post_execute(self, returned):
        ''' Clean up after the application.
        '''
        self.log.debug('Calling post_execute')

        # Interpret the returned value in the same way sys.exit() does.
        if returned is None:
            returned = 0
        elif isinstance(returned, Abort):
            returned = returned.status

        else:
            try:
                returned = int(returned)
            except:
                returned = 1

        return returned

    def execute(self, args=None):
        ''' Execute the application, returning its return value.
        Executes pre_execute and post_execute as well.
        '''
        try:
            if hasattr(self.options, 'execute'):
                execute_method = getattr(self.options, 'execute')
                self.log.debug('Execute attribute exists: {0}({1})'.format(execute_method,type(execute_method)))

                self.pre_execute()
                self.log.info('[*] Execute: {0}'.format(self.options))

                try:
                    returned = execute_method.im_self.execute(self.options)

                except Exception as err:
                    self.log.exception('Execute method execution failure: {0}'.format(err))
                    returned = err
            else:
                raise Abort('Plugin execution failure')


            #else:
                #setup command line console using existing params. Do teardown afterward.
                #args = (self,)
                #self.log.debug('No execute method found: process {0}'.format(args))
                #if is_method_of(self.main, self):
                #    if self.unknown_args:
                #        args = self.unknown_args
                #try:
                    #returned = subprocess.Popen('ls -la', env=os.environ)
                #    returned = self.main(*args)
                #except Exception as err:
                #    self.log.exception('Execution failure: {0}'.format(err))
                #    returned = err

            return self.post_execute(returned)
        except KeyboardInterrupt:
            raise

        except SystemExit:
            raise

        except Exception as err:
            logger.exception('Exception occurred : {0!r}'.format(err))


if __name__ == '__main__':
    
    #print('logging tree debug: {0}'.format(logging_tree.printout()))

    c = CLI()
    c.execute()

    #print('logging tree debug: {0}'.format(logging_tree.printout()))
