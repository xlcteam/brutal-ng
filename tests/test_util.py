"""Basic tests for brutal.core.utils"""

from brutal.core.utils import split_args_by, change_cmd
from brutal.core.models import Event
from collections import namedtuple
import sys
sys.path.insert(0, '../')


def test_split_args_by():
    args = ['test', '-', 'something', '-', 'else']
    assert split_args_by(args, '-') == ['test', 'something', 'else']


def test_change_cmd():
    Bot = namedtuple('Bot', 'command_token nick')
    bot = Bot._make(['!', 'bot'])
    evt = Event(source_bot=bot, raw_details={
        'type': 'message',
        'source': 'room',
        'meta': {
            'body': '!test',
            'recipients': []
        }
    })

    event = change_cmd(evt, 'result')
    assert event.cmd == 'result'
    assert event.meta['body'] == '!result'
