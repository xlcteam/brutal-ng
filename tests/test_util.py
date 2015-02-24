"""Basic tests for brutal.core.utils"""

import sys
sys.path.insert(0, '../')

from brutal.core.utils import split_args_by


def test_split_args_by():
    args = ['test', '-', 'something', '-', 'else']
    assert split_args_by(args, '-') == ['test', 'something', 'else']
