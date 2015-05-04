import logging

from twisted.internet.task import LoopingCall
from twisted.words.protocols.jabber import jid

from wokkel import muc
from wokkel import xmppim
from wokkel.client import XMPPClient
from wokkel.subprotocols import XMPPHandler

from brutal.protocols.core import ProtocolBackend

import re

XMPP_DEFAULT_PORT = 5222


class XmppBot():
    pass


class MucBot(muc.MUCClient):

    recipients_split_regex = '^((?:[\s]*[0-9A-Za-z_-~]{0,12}[\s]*:[\s]*)+)(.*)$'

    def __init__(self, rooms,  nick, backend):
        super(MucBot, self).__init__()

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))
        self.backend = backend

        self.raw_rooms = rooms or []
        self.room_jids = []
        self.nick = nick

        self.recipients_regex = re.compile(self.recipients_split_regex)

        for room in self.raw_rooms:
            password = None
            if type(room) is tuple:
                if len(room) > 1:
                    room, password = room
                else:
                    room = room[0]

            self.room_jids.append((jid.internJID(room), password))

    def connectionInitialized(self):
        super(MucBot, self).connectionInitialized()

        def joined_room(room):
            self.log.debug('joined room: {0!r}'.format(room.__dict__))
            if room.locked:
                self.log.error('room locked?')
                return self.configure(room.roomJID, {})

        def join_room(room_jid):
            d = self.join(room_jid, self.nick)
            d.addCallback(joined_room)
            #d.addCallback(lambda _: log.msg("joined room"))
            d.addErrback(self.log.error, 'join of {0!r} failed'.format(room_jid))

        for room in self.room_jids:
            join_room(room[0])

    def receivedGroupChat(self, room, user, message):
        self.log.debug('groupchat - user: {0}, room: {1!r}, msg: {2!r}'.format(user, room, message.body))
        if user is None:
            self.log.error('groupchat recieved from None?')
            return

        recipients = []
        match = self.recipients_regex.findall(message.body)
        if match != []:
            cleaned_recipients = match[0][0].strip().split(':')[:-1]
            recipients = [recipient.strip() for recipient in cleaned_recipients]

        event_data = {'type': 'message',
                      'scope': 'public',
                      'room': room.roomJID.full(),
                      'meta': {'nick': user.nick,
                               'body': message.body,
                               'recipients': recipients}}

        if self.nick in recipients:
            event_data['source'] = 'highlight'
            event_data['meta']['body'] = match[0][1].strip()
        else:
            event_data['source'] = 'room'

        if user.nick == self.nick:
            event_data['from_bot'] = True

        self.log.debug('event_data: {0!r}'.format(event_data))
        # log.msg('room: {0!r}, room.nick: {1!r}'.format(room, room.nick), logLevel=logging.DEBUG)
        # log.msg('roomJID: {0!s}, full: {1!r}, host: {2!r}, resource: {3!r}, user: {4!r}'.format(room.roomJID,
        #                                                                                         room.roomJID.full,
        #                                                                                         room.roomJID.host,
        #                                                                                         room.roomJID.resource,
        #                                                                                         room.roomJID.user),
        #         logLevel=logging.DEBUG)
        #self.groupChat(room.roomJID, 'wat')
        self._bot_process_event(event_data)

    #-- BOT STUFF
    def _bot_process_event(self, raw_event):
        self.backend.handle_event(raw_event)


class ClientKeepalive(XMPPHandler):
    DEFAULT_INTERVAL = 15.0
    lc = None

    def __init__(self, interval=None):
        super(ClientKeepalive, self).__init__()
        self.interval = interval or self.DEFAULT_INTERVAL

    def space(self):
        #self.xmlstream.send(' ')
        self.send(' ')

    def connectionInitialized(self):
        self.lc = LoopingCall(self.space)
        self.lc.start(self.interval, now=False)

    def connectionLost(self, reason):
        if self.lc:
            self.lc.stop()

class PrivateChatBot(xmppim.MessageProtocol):

    def __init__(self, backend):
        super(PrivateChatBot, self).__init__()
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))
        self.backend = backend

    def connectionMade(self):

        # send initial presence
        self.send(xmppim.AvailablePresence())

    def connectionLost(self, reason):
        pass

    def onMessage(self, message):
        if message is not None and hasattr(message, "body") and message.body != None:
            self.log.debug('XMPP Private message: {0!r} - {1} - {2} - {3}'.format(message, str(message.body), message["from"], message["type"]))

            if message["type"] == "chat":
                nick, other = message["from"].split('@')
                host = other.split('/')[0]
                event_data = {
                        'type': 'message',
                        'scope': 'private',
                        'source': 'query',
                        'meta': {'from': message["from"],
                                 'nick': message["from"],
                                 'body': str(message.body).strip(),
                                 'recipients': [self.backend.nick]}}

                self.backend.handle_event(event_data)


class XmppBackend(ProtocolBackend):
    protocol_name = 'xmpp'

    def configure(self, *args, **kwargs):
        # user args
        self.nick = kwargs.get('nick')
        # TODO: remove, make this just the bot name...
        self.room_nick = kwargs.get('room_nick')
        if self.room_nick is None:
            self.room_nick = self.nick

        self.log_traffic = kwargs.get('log_traffic', False)
        #TODO: remove localhost default, fail.
        self.server = kwargs.get('server', 'localhost')
        self.port = kwargs.get('port', XMPP_DEFAULT_PORT)
        self.use_ssl = kwargs.get('use_ssl', True)
        self.keepalive_freq = kwargs.get('keepalive_freq')  # defaults to None
        if type(self.keepalive_freq) not in (None, float):
            try:
                self.keepalive_freq = float(self.keepalive_freq)
            except Exception as e:
                self.log.error('invalid keepalive passed in, {0!r}: {1!r}'.format(self.keepalive_freq, e))
                self.keepalive_freq = None

        #TODO: have this default to botname @ .
        self.jabber_id = kwargs.get('jabber_id', self.nick + '@' + self.server)
        #self.room_jabber_id =  # do we need this for servers that act wonky? maybe.
        self.password = kwargs.get('password')

        self.rooms = kwargs.get('rooms')

        # allow users to define custom handlers? not now.
        #self.subprotocol_handlers = kwargs.get()

        # internal
        self.bot_jid = jid.internJID(self.jabber_id)

        # probably want to override client?
        self.client = XMPPClient(self.bot_jid, self.password, host=self.server)

        if self.log_traffic is True:
            self.client.logTraffic = True

    # def connect_handlers(self):
    #     for subprotocol in self.subprotocol_handlers:
    #         instance = subprotocol()
    #         instance.setHandlerParent(self.client)

    def connect(self, *args, **kwargs):
        #TODO: try moving this below
        self.client.startService()

        # setup handlers
        self.muc_handler = MucBot(self.rooms, self.room_nick, backend=self)
        self.muc_handler.setHandlerParent(self.client)

        self.privatechat_handler = PrivateChatBot(backend=self)
        self.privatechat_handler.setHandlerParent(self.client)

        self.presence = xmppim.PresenceClientProtocol()
        self.presence.setHandlerParent(self.client)
        self.presence.available()

        self.keepalive = ClientKeepalive(interval=self.keepalive_freq)
        self.keepalive.setHandlerParent(self.client)

    def handle_action(self, action):
        self.log.debug('XMPP ACTION : {0!r}'.format(action))

        if action.action_type != 'message':
            return

        body = str(action.meta.get('body'))
        if not body:
            return

        if not action.destination_rooms:
            return

        for room in action.destination_rooms:
            if action.scope == 'public':
                room_jid = jid.internJID(room)
                message = muc.GroupChat(recipient=room_jid, body=body)
                self.client.send(message.toElement())

            if action.scope == 'private':
                if room is not None:
                    msg = xmppim.Message(recipient=jid.internJID(room),
                                         sender=self.bot_jid,
                                         body=body)
                    self.client.send(msg.toElement())
