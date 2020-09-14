~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sample plugin for ofxstatement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This project provides a boilerplate for custom plugins for ofxstatement.

`ofxstatement`_ is a tool to convert proprietary bank statement to OFX format,
suitable for importing to GnuCash. Plugin for ofxstatement parses a
particular proprietary bank statement format and produces common data
structure, that is then formatted into an OFX file.

.. _ofxstatement: https://github.com/kedder/ofxstatement


Users of ofxstatement have developed several plugins for their banks. They are
listed on main `ofxstatement`_ site. If your bank is missing, you can develop
your own plugin.

Setting up development environment
==================================

It is recommended to use ``pipenv`` to make a clean development environment.
Setting up dev environment for writing a plugin is easy::

  $ git clone https://github.com/kedder/ofxstatement-sample ofxstatement-yourbank
  $ cd ofxstatement-yourbank
  $ pipenv sync --dev
  $ pipenv shell

This will download all the dependencies and install them into your virtual
environment. After this, you should be able to do::

  $ ofxstatement list-plugins
  The following plugins are available:

    sample           Sample plugin (for developers only)



Your own plugin
===============

To create your own plugin, follow these steps:

* Edit ``setup.py`` and provide relevant metadata for your plugin.  Pay
  close attention to ``entry_points`` parameter to ``setup`` function: it
  lists plugins you are registering within ofxstatement. Give meaningful
  name to the plugin and provide plugin class name
* Replace contents of ``README.rst`` with description of your plugin
* Rename ``ofxstatement/plugins/sample.py`` to match plugin package name
  you have provided in ``entry_points`` parameter.
* Open renamed sample.py and rename ``SamplePlugin`` and ``SampleParser``
  classes to match your plugin class name.
* Now, draw the rest of the owl (c).

.. _ofxstatement-sample: https://github.com/kedder/ofxstatement-sample

Your ``StatementParser`` is the main object that does all the hard work. It
has only one public method: ``parse()``, that should return
``ofxstatement.statement.Statement`` object, filled with data from given input.
The default implementation, however, splits this work into two parts:
``split_records()`` to split the whole file into logical parts, e.g.
transaction records, and ``parse_record()`` to extract information from
individual record. See ``src/ofxstatement/parser.py`` for details. If your
statement' format looks like CSV file, you might find ``CsvStatementParser``
class useful: it simplifies mapping bettween CSV columns and ``StatementLine``
attributes.

``Plugin`` interface consists only of ``get_parser()`` method, that returns
configured StatementParser object for given input filename. Docstrings on
Plugin class is also useful for describing the purpose of your plugin. First
line of it is visible in ``ofxstatement list-plugins`` output.

Testing
=======

Test your code as you would do with any other project.  To make sure
ofxstatement is still able to load your plugin, run::

  (.venv)$ ofxstatement list-plugins

You should be able to see your plugin listed.

After you are done
==================

After your plugin is ready, feel free to open an issue on `ofxstatement`_
project to include your plugin in "known plugin list". That would hopefully
make life of other clients of your bank easier.
