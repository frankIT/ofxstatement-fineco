~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ofxstatement-fineco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a parser for the statement file produced from the italian bank Fineco.
It's written as a plugin for `ofxstatement`_ , which handle the writing of the standard OFX file.

`ofxstatement`_ is a tool to convert proprietary bank statement to OFX format,
suitable for importing to GnuCash or any other standard-friendly accounting sofware.

It basically give you the freedom to use any accounting program you like,
without the need of propretary software that is often proposed by some banks as paid service, as in the case of the italian Fineco bank.

it's simple as::
    $ ofxstatement convert -t fineco file.xls file.ofx

After that, for example, you can import in HomeBank few years of your bank account history at once, then categorize all the in/outcome in bulk with text matching rules on the memo field,
so you can analyze your money flow over time through graphical charts.

At the time of writing the plugin support the xls file of the personal bank account statement, not the credit/debit cards statement file yet.
I'm not aware of other types of statement files produced from Fineco bank, if you do please send me a sample file, or feel free to contribute.

.. _ofxstatement: https://github.com/kedder/ofxstatement
