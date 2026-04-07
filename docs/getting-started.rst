Getting started
===============

Installation
------------

``ptools`` is distributed as a regular Python package. From a clone of
the repository, install it in editable mode along with the optional
``docs`` extras if you plan to build this documentation locally:

.. code-block:: bash

   pip install -e .
   pip install -e '.[docs]'   # only needed to build the docs

Once installed, the :command:`ptools` entry point is available on your
``$PATH``:

.. code-block:: bash

   ptools --help

Building the docs
-----------------

From the repository root:

.. code-block:: bash

   sphinx-build -b html docs docs/_build/html

or equivalently, using the provided Makefile:

.. code-block:: bash

   ptools dev docs

Open ``docs/_build/html/index.html`` in a browser to view the rendered
site. A convenience :file:`Makefile` is also provided ``make -C docs
html`` is equivalent.

Project layout
--------------

.. code-block:: text

   src/ptools/
   ├── main.py            # top-level ``ptools`` CLI (LazyGroup)
   ├── rsync.py           # ``ptools rsync`` - rsync wrappers
   ├── shell.py           # ``ptools shell`` - shell-config helpers
   ├── flow.py            # ``ptools flow`` - FP-flavored pipeline engine
   ├── llm.py             # ``ptools llm`` - chat interface
   ├── time.py            # ``ptools time`` - timing utilities
   ├── formats/           # JSON / YAML helpers
   ├── utils/             # reusable library helpers
   └── lib/               # subcommand-specific internals

See :doc:`cli` for the full list of subcommands and their options, or
:doc:`api/index` for the Python API reference.
