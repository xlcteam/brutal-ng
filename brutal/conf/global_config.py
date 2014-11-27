import logging

DEBUG = False
LOG_LEVEL = logging.INFO
LOG_FILE = 'bot.log'
LOG_FORMAT = '%({})-21s %({})s %({})s (%({})-s) %({})d:%({})d - %({})s'
LOG_FORMAT = LOG_FORMAT.format('asctime',
                               'levelname',
                               'name',
                               'funcName',
                               'process',
                               'thread',
                               'message')

INSTALLED_PLUGINS = ()
DATA_DIR = './data/'
STORAGE_SUFFIX = '.db'
