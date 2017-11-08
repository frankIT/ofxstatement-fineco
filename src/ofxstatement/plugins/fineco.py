import xlrd
from datetime import datetime
from ofxstatement import statement
from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser


class FinecoPlugin(Plugin):
    """italian bank Fineco, it parses file.xls for private accounts
    """

    def get_parser(self, filename):
        return FinecoStatementParser(filename)


class FinecoStatementParser(StatementParser):
    date_format = '%d/%m/%Y'
    bank_id = 'FinecoBank'
    currency = 'EUR'
    account_id_str = 'Conto Corrente: '
    xfer_str = 'Bonifico '
    cash_str = 'Prelievi Bancomat '
    th_separator_idx = 0
    tpl_type = 'account'
    valid_header = [
        u"Data Operazione",
        u"Data Valuta",
        u"Entrate",
        u"Uscite",
        u"Descrizione",
        u"Descrizione Completa",
    ]
    # TODO: handle both sheet template
    valid_header_cards = [
        u"Data operazione",
        u"Data Registrazione",
        u"Descrizione Operazione",
        u"Tipo spesa",
        u"Tipo rimborso",
        #u"Importo in €",
    ]


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

        # split heading from actual statement
        for row in range(sheet.nrows):
            if self.th_separator_idx > 0:
                rows.append(sheet.row_values(row))
            else:
                heading.append(sheet.row_values(row))

            if sheet.row_values(row)[0] == self.valid_header[0]:
                self.th_separator_idx = row
                # guess sheet tpl type
                if sheet.row_values(row)[1] == self.valid_header[1]:
                    self.tpl_type = 'account'
                elif sheet.row_values(row)[1] == self.valid_header_cards[1]:
                    self.tpl_type = 'cards'

        self.validate(heading)
        self.statement = statement.Statement(
            bank_id = self.bank_id,
            account_id = sheet.cell_value(0, 0).replace(self.account_id_str, ''),
            currency = self.currency
        )
        self.rows = rows
        return super(FinecoStatementParser, self).parse()


    def validate(self, heading):
        actual_header = heading[self.th_separator_idx]
        first_cell = heading[0][0]
        msg = None
        if self.tpl_type == 'cards':
            msg = "Credit card statement is not supported yet"
        elif not first_cell.startswith(self.account_id_str):
            msg = "No account id cell found"
        elif self.valid_header != actual_header:
            msg = "\n".join([
                "Header template doesn't match:",
                "expected: %s" % self.valid_header,
                "actual  : %s" % actual_header
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

        if row[2]:
            income = row[2]
            outcome = 0
            stmt_line.trntype = "CREDIT"
        elif row[3]:
            outcome = row[3]
            income = 0
            stmt_line.trntype = "DEBIT"

        memo_short = row[4]
        if memo_short.startswith(self.xfer_str):
            stmt_line.trntype = "XFER"
        elif memo_short.startswith(self.cash_str):
            stmt_line.trntype = "CASH"

        stmt_line.date = datetime.strptime(row[0], self.date_format)
        stmt_line.memo = row[5]
        stmt_line.amount = self.calc_amount(income, outcome)
        stmt_line.id = statement.generate_transaction_id(stmt_line)
        return stmt_line
