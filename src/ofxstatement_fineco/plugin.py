import xlrd, json, os  # type: ignore
from typing import Iterable, TypedDict
from pathlib import Path
from datetime import datetime
from ofxstatement import statement, configuration
from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser


class TemplateDict(TypedDict):
    savings: dict
    cards: dict


class FinecoPlugin(Plugin):
    """italian bank Fineco, it parses both xls files available for private accounts"""

    defaultsPath = os.path.join(Path(__file__).parent, "config", "defaults.ini")

    def config_parser(self, parser: "FinecoStatementParser") -> "FinecoStatementParser":
        """Configure parser with the current settings or from defaults.ini"""

        defaults = configuration.read(self.defaultsPath)
        if not defaults:
            self.ui.error("Unable to load the default configuration")
            return parser

        parser.tpl = {"savings": {}, "cards": {}}

        for option in defaults["fineco"]:
            if option == "plugin":
                continue

            default_value = defaults.get("fineco", option)

            # Handle dotted notation for templates
            if option.startswith(("savings.", "cards.")):
                section, key = option.split(".", 1)
                value = self.settings.get(option, default_value)

                if value.startswith("["):
                    parser.tpl[section][key] = json.loads(value)  # type: ignore
                else:
                    parser.tpl[section][key] = (  # type: ignore
                        int(value)
                        if str(value).isdigit()
                        else (value.strip('"') if value.startswith('"') else value)
                    )
            else:
                # Handle basic settings
                value = self.settings.get(option, default_value)
                if value.startswith("["):
                    parsed_value = json.loads(value)
                elif value.lower() in ("true", "false"):
                    parsed_value = value.lower() == "true"
                else:
                    parsed_value = (
                        int(value)
                        if str(value).isdigit()
                        else (value.strip('"') if value.startswith('"') else value)
                    )

                if hasattr(parser, option):
                    setattr(parser, option, parsed_value)
                else:
                    self.ui.warning(
                        f"Unknown configuration option: {option}. Ignoring it."
                    )

        return parser

    def get_parser(self, filename: str) -> "FinecoStatementParser":
        return self.config_parser(FinecoStatementParser(filename))


class FinecoStatementParser(StatementParser[str]):

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

        # Initialize all the configurable attr to prevent AttributeError
        self.tpl: TemplateDict = {"savings": {}, "cards": {}}
        self.memo2payee: bool = False
        self.date_format: str = ""
        self.bank_id: str = ""
        self.currency: str = ""
        self.common_footer_marker: str = ""

        self.th_separator_idx: int = 0
        self.cur_tpl: str = "savings"
        self.extra_field: bool = False

    def parse(self) -> statement.Statement:
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        workbook = xlrd.open_workbook(self.filename)
        sheet = workbook.sheet_by_index(0)
        heading, rows = [], []
        first_col = sheet.col_values(0)

        first_col_empty = True
        for cell in first_col:
            if cell != "":
                first_col_empty = False
                break

        for rowidx in range(sheet.nrows):

            row = sheet.row_values(rowidx, 1 if first_col_empty else 0)

            # issue #5 and #3: dates might be formatted as excel dates (floats) rather than strings
            if type(row[0]) is float:  # savings tpl
                row[0] = datetime.strftime(
                    xlrd.xldate_as_datetime(row[0], 0), self.date_format
                )
            if first_col_empty and type(row[2]) is float:  # cards tpl
                row[2] = datetime.strftime(
                    xlrd.xldate_as_datetime(row[2], 0), self.date_format
                )

            # split heading from current statement
            if self.th_separator_idx > 0:
                if row[0] != "" and not row[0].startswith(self.common_footer_marker):
                    rows.append(row)
            else:
                heading.append(row)

            # guess sheet tpl type
            for name, tpl in self.tpl.items():
                if row[0] == tpl["th"][0]:  # type: ignore
                    self.th_separator_idx = rowidx
                    self.cur_tpl = name

        # issue #1: check if the file has the "Money Map" extra field
        if (
            "extra_field" in self.tpl[self.cur_tpl]  # type: ignore
            and heading[-1][-1] == self.tpl[self.cur_tpl]["extra_field"]  # type: ignore
        ):
            self.tpl[self.cur_tpl]["th"].append(self.tpl[self.cur_tpl]["extra_field"])  # type: ignore
            self.extra_field = True

        # issue #2: some cards statements could miss "Tipo Spesa" and "Tipo Rimborso" columns
        if self.cur_tpl == "cards" and heading[-1][3] == self.tpl["cards"]["th"][5]:
            self.tpl["cards"]["th"].remove("Tipo spesa")
            self.tpl["cards"]["th"].remove("Tipo rimborso")
            self.tpl["cards"]["th"].append("")
            self.tpl["cards"]["amount_field"] = 4

        self.validate(heading)

        row = self.tpl[self.cur_tpl]["account_id_pos"][0]  # type: ignore
        col = self.tpl[self.cur_tpl]["account_id_pos"][1]  # type: ignore
        account_id = sheet.cell_value(row, col).replace(
            self.tpl[self.cur_tpl]["account_id_str"], ""  # type: ignore
        )

        self.statement = statement.Statement(
            bank_id=self.bank_id, account_id=account_id, currency=self.currency
        )

        self.rows = rows
        return super().parse()

    def validate(self, heading):
        if self.th_separator_idx == 0:
            raise ValueError("unkown file")

        current_header = heading[self.th_separator_idx]

        # Check and remove empty last column if present
        if current_header and current_header[-1] == "":
            current_header = current_header[:-1]

        msg = None

        row = self.tpl[self.cur_tpl]["account_id_pos"][0]
        col = self.tpl[self.cur_tpl]["account_id_pos"][1]
        if self.cur_tpl != "cards" and not heading[row][col].startswith(
            self.tpl[self.cur_tpl]["account_id_str"]
        ):
            msg = "No account id cell found"

        elif self.tpl[self.cur_tpl]["th"] != current_header:
            msg = "\n".join(
                [
                    "Header template doesn't match:",
                    "expected:  %s" % self.tpl[self.cur_tpl]["th"],
                    "current:   %s" % current_header,
                ]
            )

        if msg:
            raise ValueError(msg)

    # returns a negative number as outcome or a positive one as income
    def calc_amount(self, income, outcome):
        # in/outcome has to be both positive values for this logic to work
        # turn them into positive numbers if they're not already
        if income < 0:
            income = -1 * outcome
        if outcome < 0:
            outcome = -1 * outcome
        # only one of the two fields has to be valorized
        assert (income > 0) ^ (outcome > 0)
        if income > 0:
            return income
        elif outcome > 0:
            return -1 * outcome  # turn outcome into a negative number
        else:
            return 0.0

    def split_records(self) -> Iterable[str]:
        """Return iterable object consisting of a line per transaction"""
        for row in self.rows:
            yield row

    def parse_record(self, row: str) -> statement.StatementLine:
        """Parse given transaction line and return StatementLine object"""
        stmt_line = statement.StatementLine()

        if self.cur_tpl == "savings":
            if row[1]:
                income = int(row[1])
                outcome = 0
                stmt_line.trntype = "CREDIT"
            elif row[2]:
                outcome = int(row[2])
                income = 0
                stmt_line.trntype = "DEBIT"

            memo_short = row[3]
            if memo_short.startswith(self.tpl["savings"]["xfer_str"]):
                stmt_line.trntype = "XFER"
            elif memo_short.startswith(self.tpl["savings"]["cash_str"]):
                stmt_line.trntype = "CASH"

            stmt_line.memo = row[4].replace("°", ".")
            if self.extra_field and row[6] != "":
                stmt_line.memo = stmt_line.memo + " - " + row[6]

            stmt_line.amount = self.calc_amount(income, outcome)
            stmt_line.date = datetime.strptime(row[0], self.date_format)

        elif self.cur_tpl == "cards":
            if row[3] == "P":
                stmt_line.trntype = "CASH"

            if float(row[self.tpl["cards"]["amount_field"]]) < 0:
                stmt_line.trntype = "DEBIT"
            else:
                stmt_line.trntype = "CREDIT"

            stmt_line.memo = row[4].replace("°", ".")
            stmt_line.amount = row[self.tpl["cards"]["amount_field"]]  # type: ignore
            stmt_line.date = datetime.strptime(row[2], self.date_format)

        if self.memo2payee:
            stmt_line.payee = stmt_line.memo

        stmt_line.id = statement.generate_transaction_id(stmt_line)

        return stmt_line
