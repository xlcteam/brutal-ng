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
    Bot = namedtuple('Bot', 'command_token')
    bot = Bot._make('!')
    evt = Event(source_bot=bot, raw_details={
        'cmd': 'test',
        'meta': {
            'body': '!test'
        }
    })

    # TODO: seriously simulate processing
    evt.cmd = 'test'

    event = change_cmd(evt, 'result')
    assert event.cmd == 'result'
    assert event.meta['body'] == '!result'
