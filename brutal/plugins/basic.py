from brutal.core.plugin import cmd


@cmd
def help(event):
    """Returns some documentation for a given command.

    Examples:

        !help help
    """

    def prepare_doc(doc):
        return doc.split('\n')[0]

    plugin_manager = event.source_bot.plugin_manager
    prendex = 'Available commands: '

    if len(event.args) < 1:
        return prendex + ', '.join(plugin_manager.cmd_docs.keys())

    if len(event.args) > 1:
        return 'no...'

    cmd = event.args[0]
    doc = 'no...'
    if cmd in plugin_manager.cmd_docs:
        if plugin_manager.cmd_docs[cmd] is not None:
            doc = '{0}: {1}'.format(cmd,
                                    prepare_doc(plugin_manager.cmd_docs[cmd]))

    return doc
