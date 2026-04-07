Command-line reference
======================

This page is generated directly from the live Click command tree via
:mod:`sphinx_click`, so it always reflects the options and help text of
the installed :command:`ptools` binary.

Top-level ``ptools``
--------------------

.. click:: ptools.main:cli
   :prog: ptools
   :nested: none

Subcommands
-----------

The top-level ``ptools`` group lazily loads each subcommand on first
use. The sections below document each subcommand tree in full.

``ptools rsync``
~~~~~~~~~~~~~~~~

.. click:: ptools.rsync:cli
   :prog: ptools rsync
   :nested: full

``ptools shell``
~~~~~~~~~~~~~~~~

.. click:: ptools.shell:cli
   :prog: ptools shell
   :nested: full

``ptools flow``
~~~~~~~~~~~~~~~

.. click:: ptools.flow:cli
   :prog: ptools flow
   :nested: full

``ptools time``
~~~~~~~~~~~~~~~

.. click:: ptools.time:cli
   :prog: ptools time
   :nested: full

``ptools llm``
~~~~~~~~~~~~~~

.. click:: ptools.llm:cli
   :prog: ptools llm
   :nested: full

``ptools llm-opts``
~~~~~~~~~~~~~~~~~~~

.. click:: ptools.llm:opts
   :prog: ptools llm-opts
   :nested: full
