def split_args_by(args, by):
    a = ' '.join(args)
    return map(lambda x: x.strip(), a.split(by))


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
