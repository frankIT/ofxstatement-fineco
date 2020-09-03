import xlrd
from datetime import datetime
from ofxstatement import statement
from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser


class FinecoPlugin(Plugin):
    """italian bank Fineco, it parses both xls files available for private accounts
    """

    def get_parser(self, filename):
        return FinecoStatementParser(filename)


class FinecoStatementParser(StatementParser):

    # HomeBank import payee/<NAME> in its description field, that can be used by assignement rules
    memo2payee = True
    date_format = '%d/%m/%Y'
    bank_id = 'FinecoBank'
    currency = 'EUR'
    tpl = {
        'savings' : {
            'th' : [
                u"Data",
                u"Entrate",
                u"Uscite",
                u"Descrizione",
                u"Descrizione Completa",
                u"Stato",
            ],
            'account_id_str' : 'Conto Corrente: ',
            'xfer_str' : 'Bonifico ',
            'cash_str' : 'Prelievi Bancomat ',
            'extra_field' : 'Money Map',
        },
        'savings_legacy' : {
            'th' : [
                u"Data Operazione",
                u"Data Valuta",
                u"Entrate",
                u"Uscite",
                u"Descrizione",
                u"Descrizione Completa",
            ],
            'account_id_str' : 'Conto Corrente: ',
            'xfer_str' : 'Bonifico ',
            'cash_str' : 'Prelievi Bancomat ',
            'extra_field' : 'Money Map',
        },
        'cards' : {
            'th' : [
                u"Data operazione",
                u"Data Registrazione",
                u"Descrizione Operazione",
                u"Tipo spesa",
                u"Tipo rimborso",
                u"Importo in €",
            ],
            'th_row' : 0,
            'amount_field' : 5,
            'account_id_str' : ' **** **** ',
        }
    }
    common_footer_marker = 'Totale'
    th_separator_idx = 0
    cur_tpl = 'savings'
    extra_field = False;


    def __init__(self, filename):
        self.filename = filename


    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        workbook = xlrd.open_workbook(self.filename)
        sheet = workbook.sheet_by_index(0)
        heading, rows = [], []

        # split heading from current statement
        for rowidx in range(sheet.nrows):
            row = sheet.row_values(rowidx)

            # issue #5 and #3: dates might be formatted as excel dates (floats) rather than strings
            if type(row[0]) is float:
                row[0] = datetime.strftime(xlrd.xldate_as_datetime(row[0], 0), self.date_format)

            if self.th_separator_idx > 0:
                if row[0] != '' and not row[0].startswith(self.common_footer_marker):
                    rows.append(row)
            else:
                heading.append(row)

            # guess sheet tpl type
            for name, tpl in self.tpl.items():
                if row[0] == tpl['th'][0]:
                    self.th_separator_idx = rowidx
                    self.cur_tpl = name

        # issue #1: check if the file has the "Money Map" extra field
        if self.cur_tpl == 'savings' and heading[-1][-1] == self.tpl['savings']['extra_field']:
            self.tpl['savings']['th'].append(self.tpl['savings']['extra_field'])
            self.extra_field = True

        # issue #2: some cards statements could miss "Tipo Spesa" and "Tipo Rimborso" columns
        elif self.cur_tpl == 'cards' and heading[-1][3] == self.tpl['cards']['th'][5]:
            self.tpl['cards']['th'].remove("Tipo spesa")
            self.tpl['cards']['th'].remove("Tipo rimborso")
            self.tpl['cards']['th'].append("")
            self.tpl['cards']['th_row'] = 1
            self.tpl['cards']['amount_field'] = 4

        self.validate(heading)

        if self.cur_tpl == 'savings':
            account_id = sheet.cell_value(0, 0).replace(self.tpl[self.cur_tpl]['account_id_str'], '')
        elif self.cur_tpl == 'cards':
            account_id = sheet.cell_value(self.tpl['cards']['th_row'], 2).replace(self.tpl[self.cur_tpl]['account_id_str'], '-')

        self.statement = statement.Statement(
            bank_id = self.bank_id,
            account_id = account_id,
            currency = self.currency
        )

        self.rows = rows
        return super(FinecoStatementParser, self).parse()


    def validate(self, heading):
        if self.th_separator_idx == 0:
            raise ValueError('unkown file')

        current_header = heading[self.th_separator_idx]
        first_cell = heading[0][0]
        msg = None

        if self.cur_tpl == 'savings' and not first_cell.startswith(self.tpl[self.cur_tpl]['account_id_str']):
            msg = "No account id cell found"

        elif self.tpl[self.cur_tpl]['th'] != current_header:
            msg = "\n".join([
                "Header template doesn't match:",
                "expected: %s" % self.tpl[self.cur_tpl]['th'],
                "current  : %s" % current_header
            ])

        if msg:
            raise ValueError(msg)


    def calc_amount(self, income, outcome):
        assert (income > 0) ^ (outcome > 0)
        if income > 0:
            return income
        elif outcome > 0:
            return -1 * outcome
        else:
            return 0.0


    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        for row in self.rows:
            yield row


    def parse_record(self, row):
        """Parse given transaction line and return StatementLine object
        """
        stmt_line = statement.StatementLine()

        if self.cur_tpl == 'savings':
            if row[2]:
                income = row[2]
                outcome = 0
                stmt_line.trntype = "CREDIT"
            elif row[3]:
                outcome = row[3]
                income = 0
                stmt_line.trntype = "DEBIT"

            memo_short = row[4]
            if memo_short.startswith(self.tpl['savings']['xfer_str']):
                stmt_line.trntype = "XFER"
            elif memo_short.startswith(self.tpl['savings']['cash_str']):
                stmt_line.trntype = "CASH"

            stmt_line.memo = row[5]
            if self.extra_field and row[6] != '':
                stmt_line.memo = stmt_line.memo + ' - ' + row[6]

            stmt_line.amount = self.calc_amount(income, outcome)

        elif self.cur_tpl == 'cards':
            if row[3] == 'P':
                stmt_line.trntype = "CASH"

            if row[ self.tpl['cards']['amount_field'] ] < 0:
                stmt_line.trntype = "DEBIT"
            else:
                stmt_line.trntype = "CREDIT"

            stmt_line.memo = row[2]
            stmt_line.amount = row[ self.tpl['cards']['amount_field'] ]

        if self.memo2payee:
            stmt_line.payee = stmt_line.memo

        stmt_line.date = datetime.strptime(row[0], self.date_format)
        stmt_line.id = statement.generate_transaction_id(stmt_line)

        return stmt_line
