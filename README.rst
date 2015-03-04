=========
brutal-ng
=========

``brutal-ng`` is the new generation of ``brutal``, an asyc centered chat
bot framework for python programmers written using the twisted framework.

``brutal`` has been created by Corey Bertram at Netflix, its repositoriy
can be found at https://github.com/Netflix/brutal/

``brutal-ng`` is currently maintained and developed by members of the XLC
Team.


Documentation
-------------

See documentation of ``brutal`` can be found at http://brutal.readthedocs.org


Backwards compatibility
-----------------------

``brutal-ng`` tries to be as backwards compatible as possible. The goal is
to be able to replace ``brutal`` with ``brutal-ng`` and not to be required
to change any plugin you wrote for the older version.

Tests
------

Believe it or not, we do have some tests now. To run them you can execute::

    nosetests tests/
