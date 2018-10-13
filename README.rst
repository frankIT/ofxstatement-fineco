~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ofxstatement-fineco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a parser for the statement file produced from the italian bank Fineco.
It's written as a plugin for `ofxstatement`_, which handle the writing of the standard OFX file.

`ofxstatement`_ is a tool to convert proprietary bank statement to OFX format,
suitable for importing to `GnuCash`_ or any other standard-friendly accounting sofware.

It basically give you the freedom to use any accounting program you like,
without the need of propretary software that is sometimes advertised by the banks,
as the italian Fineco do with its `MoneyMap`_.

a use case
----------
You can import in `HomeBank`_ few years of your bank account history at once,
then categorize all the in/outcome in bulk with text matching rules on the memo/info field.
So in a few minutes you can analyze your money flow over time through graphical charts.

how
-----

::

    $ ofxstatement convert -t fineco file.xls file.ofx

install
-------

::

    $ pip3 install ofxstatement-fineco

about the parsing
-----------------
- A semi-unique id is generated for any transaction through a ofxstatement's native method.
- The ofx transaction type are set to generic DEBIT or CREDIT according to the in/outcome field.
- The only other two type set are XFER and CASH, when the transaction is evaluated respectively as a bank transfer or a withrawal
- The full description available is set to the memo field.
- Optionally the memo field could be duplicated on the payee/<NAME> one, to match a specific `HomeBank limit`_ during ofx import.
- The "Money Map" coulum, if found in the savings statement, will be appended to the memo field.

The plugin support both the xls file available from Fineco: the one from your savings, and the one from your debit/credit cards.
The debit card top-ups log it's not supported by purpose, since the same transactions are present in the savings statement.
I'm not aware of other statement files available from Fineco bank, if you do please send me a sample file, or feel free to contribute.

Simliar old projects
--------------------
`fineco2qif`_, `fineco2kmymoney`_

.. _ofxstatement: https://github.com/kedder/ofxstatement
.. _GnuCash: https://www.gnucash.org/
.. _MoneyMap: https://finecobank.com/en/online/conto-e-carte/moneymap/
.. _HomeBank: http://homebank.free.fr/
.. _HomeBank limit: https://bugs.launchpad.net/homebank/+bug/1645124
.. _fineco2qif: https://code.google.com/archive/p/fineco2qif/
.. _fineco2kmymoney: https://code.google.com/archive/p/fineco2kmymoney/
