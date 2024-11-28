import os

from ofxstatement.ui import UI
from ofxstatement_fineco.plugin import FinecoPlugin


def test_sample() -> None:
    plugin = FinecoPlugin(UI(), {})
    here = os.path.dirname(__file__)

    # NOTE: The two sample files provided has been edidted with libreoffice
    # and although they keep the same layout and spreadsheet format as the original ones,
    # they do slightly differ in their raw content (metadata, cell types ecc).

    test_files = [
        os.path.join(here, "movements.xlsx"),  # Savings statement
        os.path.join(here, "my-cards.xls"),  # Cards statement
    ]

    for filename in test_files:
        parser = plugin.get_parser(filename)
        statement = parser.parse()

        assert statement is not None
