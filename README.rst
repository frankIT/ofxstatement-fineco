~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ofxstatement-fineco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a parser for the statement file produced from the italian bank Fineco.
It's written as a plugin for `ofxstatement`_, which handle the writing of the standard OFX file.

`ofxstatement`_ is a tool to convert proprietary bank statement to OFX format,
suitable for importing to `GnuCash`_ or any other standard-friendly accounting sofware.

It basically give you the freedom to use any accounting program you like,
without the need of propretary software that is sometimes advertised by the banks, as the italian Fineco do.

a use case
----------
You can import in `HomeBank`_ few years of your bank account history at once, then categorize all the in/outcome in bulk with text matching rules on the memo/info field.
So in a few minutes you can analyze your money flow over time through graphical charts.

how
-----

::

    $ ofxstatement convert -t fineco file.xls file.ofx

install
-------
I still not packetized for pip, so you still have to

::

    $ git clone https://github.com/frankIT/ofxstatement-fineco.git fineco
    $ cd fineco && python setup.py develop

about the parsing
-----------------
- A semi-unique id is generated for any transaction through a ofxstatement's native method.
- The ofx transaction type are set to generic DEBIT or CREDIT according to the in/outcome field.
- The only other two type set are XFER and CASH, when the transaction is evaluated respectively as a bank transfer or a withrawal
- The full description available are set to the memo field.
- Optionally the memo field could be duplicated on the payee one, to match a specific `HomeBank`_ limit during ofx import.

!! At the time of writing the plugin support the xls file of the personal bank account statement, not the credit/debit cards statement file yet. !!

I'm not aware of other types of statement files produced from Fineco bank, if you do please send me a sample file, or feel free to contribute.

Simliar old projects
--------------------
`fineco2qif`_, `fineco2kmymoney`_

.. _ofxstatement: https://github.com/kedder/ofxstatement
.. _GnuCash: https://www.gnucash.org/
.. _HomeBank: http://homebank.free.fr/
.. _fineco2qif: https://code.google.com/archive/p/fineco2qif/
.. _fineco2kmymoney: https://code.google.com/archive/p/fineco2kmymoney/
