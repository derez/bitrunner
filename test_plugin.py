# -*- coding: utf-8 -*

import os
import sys
from pathlib import Path
current_path = Path('.').absolute()

from plugin import Plugin

PLUGIN_NAME = __name__

import logging

logger = logging.getLogger(PLUGIN_NAME)

class TestPlugin(Plugin):
    """TestPlugin implements a subset of tools for testing."""

    name    = PLUGIN_NAME
    version = '0.1'

    def __init__(self):
        super(TestPlugin, self).__init__(name=type(self).name)
        self.log.info('[+] Initialize {0} Plugin Module'.format(type(self).name))


    def setup(self, parser):
        self.log.debug('Plugin Setup {0} : {1}'.format(self.__class__.__name__,self.__class__.__dict__))
        parser.add_argument('-s', action='store', dest='simple_value', help='Store a simple value')
        parser.add_argument('-c', action='store_const', dest='constant_value', const='value-to-store',
                            help='Store a constant value')
        parser.add_argument('-t', action='store_true', default=False, dest='boolean_switch',
                            help='Set a switch to true')
        parser.add_argument('-f', action='store_false', default=False, dest='boolean_switch',
                            help='Set a switch to false')
        parser.add_argument('-a', action='append', dest='collection', default=[], help='Add repeated values to a list')


    def execute(self, params):
        self.log.debug('{0} Plugin -  Args:{1}'.format(self.__class__.__name__, params))



    def get_config_file(self):
        file_path = current_path.absolute().joinpath('{!s}.conf'.format(type(self).name.lower()))
        self.log.debug('{0} Plugin - Config File {1}'.format(self.__class__.__name__, file_path))
        return file_path

