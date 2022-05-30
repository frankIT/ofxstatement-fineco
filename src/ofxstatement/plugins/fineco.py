from typing import Iterable

import xlrd
from datetime import datetime
from ofxstatement import statement
from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser
# from ofxstatement.statement import Statement, StatementLine


class FinecoPlugin(Plugin):
    """italian bank Fineco, it parses both xls files available for private accounts"""

    def get_parser(self, filename: str) -> "FinecoStatementParser":
        return FinecoStatementParser(filename)


class FinecoStatementParser(StatementParser[str]):

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
            'account_id_pos' : [1, 0],
            'account_id_str' : 'Conto Corrente: ',
            'xfer_str' : 'Bonifico ',
            'cash_str' : 'Prelievi Bancomat ',
            'extra_field' : 'Moneymap',
        },
        # this will be dropped as soon as it will not be available to download
        'savings_legacy' : {
            'th' : [
                u"Data Operazione",
                u"Data Valuta",
                u"Entrate",
                u"Uscite",
                u"Descrizione",
                u"Descrizione Completa",
            ],
            'account_id_pos' : [0, 0],
            'account_id_str' : 'Conto Corrente: ',
            'xfer_str' : 'Bonifico ',
            'cash_str' : 'Prelievi Bancomat ',
            'extra_field' : 'Money Map',
        },
        'cards' : {
            'th' : [
                u"Data operazione",
                u"Data registrazione",
                u"Descrizione",
                u"Tipo spesa",
                u"Tipo rimborso",
                u"Importo in EUR",
            ],
            'amount_field' : 5,
            'account_id_pos' : [1, 2],
            'account_id_str' : ' **** **** ',
        }
    }
    common_footer_marker = 'Totale'
    th_separator_idx = 0
    cur_tpl = 'savings'
    extra_field = False;


    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename


    def parse(self) -> statement.Statement:
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        workbook = xlrd.open_workbook(self.filename)
        sheet = workbook.sheet_by_index(0)
        heading, rows = [], []

        for rowidx in range(sheet.nrows):
            row = sheet.row_values(rowidx)

            # issue #5 and #3: dates might be formatted as excel dates (floats) rather than strings
            if type(row[0]) is float:
                row[0] = datetime.strftime(xlrd.xldate_as_datetime(row[0], 0), self.date_format)

            # split heading from current statement
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
        if 'extra_field' in self.tpl[self.cur_tpl] and heading[-1][-1] == self.tpl[self.cur_tpl]['extra_field']:
            self.tpl[self.cur_tpl]['th'].append(self.tpl[self.cur_tpl]['extra_field'])
            self.extra_field = True

        # issue #2: some cards statements could miss "Tipo Spesa" and "Tipo Rimborso" columns
        if self.cur_tpl == 'cards' and heading[-1][3] == self.tpl['cards']['th'][5]:
            self.tpl['cards']['th'].remove("Tipo spesa")
            self.tpl['cards']['th'].remove("Tipo rimborso")
            self.tpl['cards']['th'].append("")
            self.tpl['cards']['amount_field'] = 4

        self.validate(heading)

        row = self.tpl[self.cur_tpl]['account_id_pos'][0]
        col = self.tpl[self.cur_tpl]['account_id_pos'][1]
        account_id = sheet.cell_value(row, col).replace(self.tpl[self.cur_tpl]['account_id_str'], '')

        self.statement = statement.Statement(
            bank_id = self.bank_id,
            account_id = account_id,
            currency = self.currency
        )

        self.rows = rows
        return super().parse()


    def validate(self, heading):
        if self.th_separator_idx == 0:
            raise ValueError('unkown file')

        current_header = heading[self.th_separator_idx]
        msg = None

        row = self.tpl[self.cur_tpl]['account_id_pos'][0]
        col = self.tpl[self.cur_tpl]['account_id_pos'][1]
        if self.cur_tpl != 'cards' and not heading[row][col].startswith(self.tpl[self.cur_tpl]['account_id_str']):
            msg = "No account id cell found"

        elif self.tpl[self.cur_tpl]['th'] != current_header:
            msg = "\n".join([
                "Header template doesn't match:",
                "expected: %s" % self.tpl[self.cur_tpl]['th'],
                "current  : %s" % current_header
            ])

        if msg:
            raise ValueError(msg)


    # returns a negative number as outcome or a positive one as income
    def calc_amount(self, income, outcome):
        assert (income > 0) ^ (outcome != 0)
        if income > 0:
            return income
        elif outcome != 0:
            return -1 * outcome
        else:
            return 0.0


    def split_records(self) -> Iterable[str]:
        """Return iterable object consisting of a line per transaction"""
        for row in self.rows:
            yield row


    def parse_record(self, row: str) -> statement.StatementLine:
        """Parse given transaction line and return StatementLine object"""
        stmt_line = statement.StatementLine()

        if self.cur_tpl == 'savings' or self.cur_tpl == 'savings_legacy':
            col_shift = 1 if self.cur_tpl == 'savings_legacy' else 0
            if row[1+col_shift]:
                income = row[1+col_shift]
                outcome = 0
                stmt_line.trntype = "CREDIT"
            elif row[2+col_shift]:
                outcome = row[2+col_shift]
                income = 0
                stmt_line.trntype = "DEBIT"

            memo_short = row[3+col_shift]
            if memo_short.startswith(self.tpl['savings']['xfer_str']):
                stmt_line.trntype = "XFER"
            elif memo_short.startswith(self.tpl['savings']['cash_str']):
                stmt_line.trntype = "CASH"

            stmt_line.memo = row[4+col_shift].replace("N°", "N.")
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
