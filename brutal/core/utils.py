import copy
import re


def split_args_by(args, by):
    a = ' '.join(args)
    return map(lambda x: x.strip(), a.split(by))


def change_cmd(evt, new_cmd):
    """Takes an event and returns an event with the same metadata but a
    different command."""
    event = copy.copy(evt)
    event.cmd = new_cmd

    old_cmd = '{0}{1}'.format(event.source_bot.command_token, evt.cmd)
    new_cmd = '{0}{1}'.format(event.source_bot.command_token, new_cmd)
    event.meta['body'] = re.sub('^{0}'.format(old_cmd),
                                new_cmd,
                                evt.meta['body'])
    return event


class PluginRoot(type):
    """
    metaclass that all plugin base classes will use
    """
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            # only execs when processing mount point itself
            cls.plugins = []
        else:
            # plugin implementation, register it
            cls.plugins.append(cls)
