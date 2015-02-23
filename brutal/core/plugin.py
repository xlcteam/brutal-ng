import re
import logging
import inspect
import functools
from twisted.internet import reactor, task, defer, threads
from twisted.python.threadable import isInIOThread

from brutal.core.models import Action, Event
from brutal.conf import config

import shelve
import os

SRE_MATCH_TYPE = type(re.match("", ""))


def threaded(func=None):
    """
    tells bot to run function in a thread
    """
    def decorator(func):
        func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def cmd(func=None, command=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        func.__brutal_event_type = 'cmd'
        func.__brutal_trigger = None
        func.__brutal_command = None
        if command is not None and type(command) in (str, unicode):
            try:
                func.__brutal_trigger = re.compile(command)
                func.__brutal_command = command
            except Exception:
                logging.exception('failed to build regex for {0!r}'
                                  ' from func {1!r}'.format(command,
                                                            func.__name__))

        if func.__brutal_trigger is None:
            try:
                raw_name = r'^{0}$'.format(func.__name__)
                func.__brutal_trigger = re.compile(raw_name)
                func.__brutal_command = func.__name__
            except Exception:
                logging.exception('failing to build command'
                                  ' from {0!r}'.format(func.__name__))
                func.__brutal_event = False

        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# def parser(func=None, thread=True):
#     """
#     this decorator makes the function look at _all_ lines and attempt to
#     parse them
#     ex: logging
#     """
#     def decorator(func):
#         func.__brutal_parser = True
#
#         if thread is True:
#             func.__brutal_threaded = True
#
#         @functools.wraps(func)
#         def wrapper(*args, **kwargs):
#             return func(*args, **kwargs)
#         return wrapper
#
#     if func is None:
#         return decorator
#     else:
#         return decorator(func)


# make event_type required?
def event(func=None, event_type=None, thread=False):
    """
    this decorator is used to register an event parser that the bot will
    respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        if event_type is not None and type(event_type) in (str, unicode):
            func.__brutal_event_type = event_type

        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# TODO: maybe swap this to functools.partial
def match(func=None, regex=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        func.__brutal_event_type = 'message'
        func.__brutal_trigger = None
        if regex is not None and type(regex) in (str, unicode):
            try:
                func.__brutal_trigger = re.compile(regex)
            except Exception:
                logging.exception('failed to build regex for {0!r}'
                                  ' from func {1!r}'.format(regex,
                                                            func.__name__))

        if func.__brutal_trigger is None:
            try:
                raw_name = r'^{0}$'.format(func.__name__)
                func.__brutal_trigger = re.compile(raw_name)
            except Exception:
                logging.exception('failing to build match from {0!r}'
                                  .format(func.__name__))
                func.__brutal_event = False

        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# TODO: possibly abstract like this?
class Parser(object):
    def __init__(self, func, source=None):
        self.healthy = False

        self.source = source
        if inspect.isclass(source) is True:
            self.source_name = '{0}.{1}'.format(self.source.__module__,
                                                self.source.__name__)
        elif inspect.ismodule(source) is True:
            self.source_name = self.source.__name__
        else:
            try:
                test = isinstance(source, BotPlugin)
            except TypeError:
                self.source_name = 'UNKNOWN: {0!r}'.format(source)
            else:
                if test is True:
                    self.source_name = "{0}".format(self.__class__.__name__)
                else:
                    self.source_name = 'UNKNOWN instance: {0!r}'.format(source)

        self.func = func
        self.func_name = self.func.__name__

        self.event_type = None
        self.regex = None
        self.threaded = getattr(self.func, '__brutal_threaded', False)
        self.parse_bot_events = False
        self.command = getattr(self.func, '__brutal_command', None)

        cls = self.__class__

        self.log = logging.getLogger('{0}.{1}'.format(cls.__module__,
                                                      cls.__name__))

        # future use:
        # if true, wont run any more parsers after this.
        # self.stop_parsing = False
        # self.parent = None
        # self.children = None

        # TODO: check if healthy
        self.event_type = getattr(self.func, '__brutal_event_type', None)
        if self.event_type in ['cmd', 'message']:
            self.regex = getattr(self.func, '__brutal_trigger', None)

            if self.regex is None:
                self.log.error('failed to get compiled regex '
                               'from func for {0}'.format(self))
                self.healthy = False
            else:
                # should probably check that its a compiled re
                self.healthy = True
        else:
            self.healthy = True

        self.log.debug('built parser - event_type: {0!r}, '
                       ' source: {1!r}, func: {2!r}'.format(self.event_type,
                                                            self.source_name,
                                                            self.func_name))

    def __repr__(self):
        return '<{0} {1}:{2}>'.format(self.__class__.__name__,
                                      self.source_name,
                                      self.func_name)

    def __str__(self):
        return repr(self)

    def matches(self, event):
        if not isinstance(event, Event):
            self.log.error('invalid event passed to parser')
            return

        if event.event_type != self.event_type:
            self.log.debug('event_parser not meant for this event type')
            return

        if event.event_type == 'cmd':
            if event.cmd is None or self.regex is None:
                self.log.error('invalid event passed in')
                return

            return self.match_with_regex(event.cmd)

        elif event.event_type == 'message' and \
                isinstance(event.meta, dict) and  \
                'body' in event.meta:

            body = event.meta['body']
            # TODO: HERE, make this smarter.
            if self.regex is None or not (type(body) in (str, unicode)):
                self.log.error('message contains no body for the regex'
                               ' to match against')
                return

            return self.match_with_regex(body)

        else:
            return True

    def match_with_regex(self, text):
        """Decides whether the text matches the regexp of the function"""
        try:
            match = self.regex.match(text)
        except Exception:
            self.log.exception('invalid regex match attempt on {0!r},'
                               '{1!r}'.format(text, self))
        else:
            return match

    @classmethod
    def build_parser(cls, func, source):
        if getattr(func, '__brutal_event', False):
            return cls(func, source)


class PluginManager(object):
    def __init__(self, bot):
        cls = self.__class__
        self.log = logging.getLogger('{0}.{1}'.format(cls.__module__,
                                                      cls.__name__))
        self.bot = bot
        self.event_parsers = {None: [], }

        self.plugin_modules = {}
        self.plugin_instances = {}

        self.status = None

        self.cmd_docs = {}

        # possibly track which bot this PM is assigned to?
        # should track which module it came from for easy unloading

    # def start(self):
    #     installed_plugins = getattr(config, PLUGINS)

    def shutdown(self, *args, **kwargs):
        """A method that is called on bot shutdown."""
        for plugin, _ in self.plugin_instances.iteritems():
            plugin.close_storages()

    def update(self):
        """The metod which is executed every 30 seconds, gets propagated from
        BotManager."""
        pass

    def start(self, enabled_plugins=None):
        if enabled_plugins is not None \
           and not type(enabled_plugins) in (list, dict):
            self.log.error('improper plugin config, '
                           'list or dictionary required')
            return

        installed_plugins = getattr(config, 'PLUGINS')

        if installed_plugins is None:
            self.log.error('error getting INSTALLED_PLUGINS')
            return

        # find enabled plugin modules and instantiate classes
        # of every BotPlugin within modules
        for plugin_module in installed_plugins:
            if enabled_plugins is not None:
                if plugin_module.__name__ not in enabled_plugins:
                    continue

            self.plugin_modules[plugin_module] = plugin_module.__name__

            # get classes
            plugin_module_classes = inspect.getmembers(plugin_module,
                                                       inspect.isclass)
            for class_name, class_object in plugin_module_classes:
                if issubclass(class_object, BotPlugin):
                    try:
                        cfg = self.bot.enabled_plugins[plugin_module.__name__]
                        instance = class_object(bot=self.bot,
                                                config=cfg)
                    except Exception, e:
                        self.log.exception('failed to load plugin {0!r}'
                                           ' from {1!r} due to (2!r)'
                                           .format(class_name,
                                                   plugin_module.__name__,
                                                   e))
                    else:
                        try:
                            instance.setup()
                        except Exception, e:
                            self.log.exception('failed to setup plugin {0!r}'
                                               ' from {1!r} due to {2!r}'
                                               .format(class_name,
                                                       plugin_module.__name__,
                                                       e))
                        else:
                            name = plugin_module.__name__
                            self.plugin_instances[instance] = name

        self._register_plugins(self.plugin_modules, self.plugin_instances)

    def _register_plugins(self, plugin_modules, plugin_instances):
        """
        TODO: add default plugins

        for this bot, load all the plugins
        - find event handlers and register them
        """
        for module in plugin_modules:
            self._register_plugin_functions(module)

        for plugin_instance in plugin_instances:
            self._register_plugin_class_methods(plugin_instance)

    def remove_plugin(self, plugin_module):
        # TODO: fill out
        pass

    def _register_plugin_functions(self, plugin_module):
        """Register all (bare) functions form a module."""

        module_name = plugin_module.__name__
        self.log.debug('loading plugins from module {0!r}'.format(module_name))

        module_functions = inspect.getmembers(plugin_module,
                                              inspect.isfunction)
        self._build_parser(module_functions, plugin_module, module_name)

    def _register_plugin_class_methods(self, plugin_instance):
        """Register all functions from an instance of a class."""

        class_name = plugin_instance.__class__.__name__
        self.log.debug('loading plugins'
                       ' from instance of {0!r}'.format(class_name))

        plugin_methods = inspect.getmembers(plugin_instance, inspect.ismethod)
        self._build_parser(plugin_methods, plugin_instance, class_name)

    def _build_parser(self, functions, source, name):
        """Creates a parser for both functions that reside either directly in
        `source` which means that they can reside in modules or objects
        (classes). """
        for func_name, func in functions:
            try:
                parser = Parser.build_parser(func=func, source=source)
            except Exception:
                self.log.exception('failed to build parser '
                                   'from {0} ({1})'.format(func_name, name))
                continue
            else:
                if parser is not None:
                    if parser.event_type in self.event_parsers:
                        self.event_parsers[parser.event_type].append(parser)
                    else:
                        self.event_parsers[parser.event_type] = [parser, ]

                    # let's recall the documentation (docstring) of a function
                    # so that we can get a quick help.
                    if parser.event_type == 'cmd' and\
                       parser.command is not None:
                        self.cmd_docs[parser.command] = func.__doc__

    # event processing
    @defer.inlineCallbacks
    def _run_event_processor(self, event_parser, event, *args):
        run = True
        response = None
        # TODO: make this check if from_bot == _this_ bot
        if event.from_bot is True:
            if event_parser.parse_bot_events is not True:
                self.log.info('ignoring event from bot: {0!r}'.format(event))
                run = False

        if run is True:
            if event_parser.threaded is True:
                self.log.debug('executing event_parser {0!r} '
                               'in thread'.format(event_parser))
                response = yield threads.deferToThread(event_parser.func,
                                                       event,
                                                       *args)
            else:
                self.log.debug('executing'
                               ' event_parser {0!r}'.format(event_parser))
                # try:
                response = yield event_parser.func(event, *args)

        defer.returnValue(response)

    def process_event(self, event):
        # TODO: this needs some love

        # this will keep track of all the responses we get
        responses = []

        # TODO: wrap everything in try/except
        if not isinstance(event, Event):
            self.log.error('invalid event, ignoring: {0!r}'.format(event))
            raise

        self.log.debug('processing {0!r}'.format(event))

        # run only processors of this event_type
        if event.event_type is not None \
           and event.event_type in self.event_parsers:
            self.log.debug('detected'
                           ' event_type {0!r}'.format(event.event_type))
            for event_parser in self.event_parsers[event.event_type]:
                # check if match
                match = event_parser.matches(event)
                response = None
                if match is True:
                    self.log.debug('running'
                                   ' event_parser {0!r}'.format(event_parser))
                    response = self._run_event_processor(event_parser, event)
                elif isinstance(match, SRE_MATCH_TYPE):
                    self.log.debug('running event_parser {0!r}'
                                   ' with regex results'
                                   '{1!r}'.format(event_parser,
                                                  match.groups()))
                    response = self._run_event_processor(event_parser,
                                                         event,
                                                         *match.groups())

                if response is not None:
                    responses.append(response)

        # default 'all' parsers
        for event_parser in self.event_parsers[None]:
            self.log.debug('running event_parser {0!r}'.format(event_parser))
            # response = yield self._run_event_processor(event_parser, event)
            response = self._run_event_processor(event_parser, event)

            if response is not None:
                responses.append(response)

        for response in responses:
            response.addCallback(self.process_result, event)

        return responses
        # defer.returnValue(responses)

    # def emit_action() - out of band action to the bot.

    def process_result(self, response, event):
        if response is not None:
            self.log.debug('RESPONSE: {0!r}'.format(response))
            if isinstance(response, Action):
                return response
                # self.bot.action_queue.put(response)
            else:
                # a = self.build_action(response, event)
                return self.build_action(response, event)

                # if a is not None:
                #     self.bot.action_queue.put(a)

    def build_action(self, action_data, event=None):
        if not type(action_data) in (str, unicode):
            try:
                action_data = str(action_data)
            except Exception as e:
                self.log.exception('Failed to convert action_data ({0!r})'
                                   'to string'.format(action_data))
        try:
            action = Action(source_bot=self.bot,
                            source_event=event).msg(action_data)
        except Exception as e:
            self.log.exception('failed to build action from {0!r},'
                               ' for {1!r}: {2!r}'.format(action_data,
                                                          event,
                                                          e))
        else:
            return action


# TODO: completely changed, need to rework this...
class BotPlugin(object):
    """
    base plugin class

    """
    event_version = '1'
    built_in = False  # is this a packaged plugin

    # TODO: make a 'task' decorator...
    def __init__(self, bot=None, config=None):
        """
        don't touch me. plz?

        each bot that spins up, loads its own plugin instance

        TODO: move the stuff in here to a separate func and call it after we
            initialize the instance.
            that way they can do whatever they want in init
        """
        self.bot = bot
        self.config = config

        self.log = logging.getLogger('{0}.{1}'.format(self.__module__,
                                                      self.__class__.__name__))

        self._active = False  # is this instance active?
        self._delayed_tasks = []  # tasks scheduled to run in the future
        self._looping_tasks = []

        # shelves for persistent data storage.
        self.shelves = {}

    # Tasks

    def _clear_called_tasks(self):
        # yes.
        self._delayed_tasks[:] = [d for d in self._delayed_tasks if d.called()]

    def _handle_task_response(self, response, *args, **kwargs):
        self.log.debug('PLUGIN TASK RESULTS: {0!r}'.format(response))
        self.log.debug('TASK ARGS: {0!r}'.format(args))
        self.log.debug('TASK KWARGS: {0!r}'.format(kwargs))
        # hacking this in for now:
        event = kwargs.get('event')
        try:
            a = self.build_action(action_data=response, event=event)
        except Exception:
            self.log.exception('failed to build action from plugin task '
                               '{0!r}, {1!r}, {2!r}'.format(response,
                                                            args,
                                                            kwargs))
        else:
            self.log.debug('wat: {0!r}'.format(a))
            if a is not None:
                self._queue_action(a, event)

    def build_action(self, action_data, event=None):
        # TODO this is hacky - fix it.
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self.bot,
                           source_event=event).msg(action_data)
            except Exception:
                logging.exception('failed to build action'
                                  ' from {0!r}, for {1!r}'.format(action_data,
                                                                  event))
            else:
                return a

    @defer.inlineCallbacks
    def _plugin_task_runner(self, func, *args, **kwargs):
        try:
            if getattr(func, '__brutal_threaded', False):
                # add func details
                self.log.debug('executing plugin task in thread')
                response = yield threads.deferToThread(func, *args, **kwargs)
            else:
                self.log.debug('executing plugin task')  # add func details
                response = yield func(*args, **kwargs)

            yield self._handle_task_response(response, *args, **kwargs)
            # defer.returnValue(response)
        except Exception as e:
            self.log.error('_plugin_task_runner failed: {0!r}'.format(e))

    def delay_task(self, delay, func, *args, **kwargs):
        if inspect.isfunction(func) or inspect.ismethod(func):
            self.log.debug('scheduling task {0!r} to run in '
                           '{1} seconds'.format(func.__name__,
                                                delay))
            # trying this.. but should probably just use callLater
            d = task.deferLater(reactor,
                                delay,
                                self._plugin_task_runner,
                                func,
                                *args,
                                **kwargs)
            self._delayed_tasks.append(d)

    def loop_task(self, loop_time, func, *args, **kwargs):
        """Starts looping a function ``func`` every ``loop_time`` seconds.

        Note: If the ``now`` parameter is present and set to True the function
        is called right after declaration too."""
        if inspect.isfunction(func) or inspect.ismethod(func):
            self.log.debug('scheduling task {0!r} to'
                           ' run every {1} seconds'.format(func.__name__,
                                                           loop_time))
            now = kwargs.pop('now', True)
            # event = kwargs.pop('event', None)
            t = task.LoopingCall(self._plugin_task_runner,
                                 func,
                                 *args,
                                 **kwargs)
            t.start(loop_time, now)
            self._looping_tasks.append(t)

    def start_poller(self, loop_time, func, *args, **kwargs):
        """Start to pool a the function ``func``."""

        return self.loop_task(loop_time, func, *args)

    def open_storage(self, name):
        """Opens persistent storage with a given name."""
        if name not in self.shelves:
            path = config.DATA_DIR + os.sep + \
                self.bot.nick + '.' + name + config.STORAGE_SUFFIX
            self.shelves[name] = shelve.DbfilenameShelf(path, protocol=2)
        return self.shelves[name]

    def close_storage(self, name):
        """Closes persistent storage with a given name that is already open."""
        if name in self.shelves:
            self.shelves[name].close()
        else:
            msg = "No storage called '{0}' found!".format(name)
            self.log.error(msg)
            raise ValueError(msg)

    def close_storages(self):
        """Closes all open persistent storages."""
        for _, shelf in self.shelves.iteritems():
            shelf.close()

    # Actions

    def _queue_action(self, action, event=None):
        if isinstance(action, Action):
            if isInIOThread():
                self.bot.route_response(action, event)
            else:
                reactor.callFromThread(self.bot.route_response, action, event)
        else:
            self.log.error('tried to queue invalid action: '
                           '{0!r}'.format(action))

    def msg(self, msg, room=None, event=None):
        a = Action(source_bot=self.bot, source_event=event).msg(msg, room=room)
        self._queue_action(a, event)

    # internal

    def enable(self):
        cls = self.__class__
        self.log.info('enabling plugin on {0!r}: {1!r}'.format(self.bot,
                                                               cls.__name__))

        # eh. would like to be able to resume... but that's :effort:
        self._delayed_tasks = []
        self._looping_tasks = []
        # set job to clear task queue
        self.loop_task(15, self._clear_called_tasks, now=False)
        self._active = True

    def disable(self):
        cls = self.__class__
        self.log.info('disabling plugin on {0!r}: {1!r}'.format(self.bot,
                                                                cls.__name__))
        self._active = False

        for func in self._delayed_tasks:
            if func.called is False:
                func.cancel()

        for func in self._looping_tasks:
            if func.running:
                func.stop()

        self._delayed_tasks = []
        self._looping_tasks = []

#     def handle_event(self, event):
#         if isinstance(event, Event):
#             if self._version_matches(event):
# #                if self._is_match(event):
#                 self._parse_event(event)
#
    # min_version
    # max_version
    def _version_matches(self, event):
        # TODO: ugh.. figure out what i want to do here...
        if event.version == self.event_version:
            return True
        return False

    def setup(self, *args, **kwargs):
        """
        use this to do any one off actions needed to initialize the bot once
        it is active
        """
        pass
        # raise NotImplementedError

    def _is_match(self, event):
        """
        returns t/f based if the plugin should parse the event
        """
        return True
        # raise NotImplementedError

    def _parse_event(self, event):
        """
        takes in an event object and does whatever the plugins supposed
        to do...
        """
        raise NotImplementedError
