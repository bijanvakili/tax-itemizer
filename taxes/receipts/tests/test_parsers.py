import logging
import functools
import os

import pytest

from taxes.receipts.types import Currency, TRANSACTION_SEQUENCE
from taxes.receipts.models import PaymentMethod
from taxes.receipts import parsers as parsers
from taxes.receipts.parsers_factory import ParserFactory
from taxes.receipts.tests.logging import log_contains_message, MockLogger
from taxes.receipts.util.datetime import parse_iso_datestring


@pytest.fixture()
def parser_factory_setup(request, monkeypatch, transaction_fixture_dir):
    mock = MockLogger()
    monkeypatch.setattr(parsers, 'LOGGER', mock)
    request.cls.mock_logger = mock

    request.cls.transaction_fixture_dir = transaction_fixture_dir
    request.cls.parser_factory = ParserFactory()

    yield


# pylint:disable=too-many-arguments
def _make_expected_transaction(line_number: int, transaction_datestr: str, amount: int,
                               description: str, misc: dict,
                               currency: Currency = None,
                               payment_method: PaymentMethod = None) -> parsers.Transaction:
    return parsers.Transaction(
        line_number=line_number,
        payment_method=payment_method,
        transaction_date=parse_iso_datestring(transaction_datestr),
        amount=amount,
        currency=currency,
        description=description,
        misc=misc
    )
# pylint:enable=too-many-arguments


@pytest.mark.usefixtures('transactional_db', 'payment_methods', 'parser_factory_setup')
class TestParsers:
    # injected by pytest
    parser_factory = None
    mock_logger = None
    transaction_fixture_dir = None

    def _run_parser(self, filename) -> TRANSACTION_SEQUENCE:  # pylint:disable=redefined-outer-name
        test_parser = self.parser_factory.get_parser(filename)
        results = list(test_parser.parse(os.path.join(self.transaction_fixture_dir, filename)))

        assert not log_contains_message(self.mock_logger, 'Pattern not found', level=logging.ERROR)
        assert test_parser.failures == 0

        return results

    def test_parse_bmo_savings(self):
        expected_payment_method = PaymentMethod.objects.get(name='BMO Savings')

        _T = functools.partial(_make_expected_transaction,  # pylint:disable=invalid-name
                               currency=Currency.CAD, payment_method=expected_payment_method)

        def _m(transaction_code: str) -> dict:
            return {
                'last_4_digits': '0066',
                'transaction_code': transaction_code
            }

        # TODO should transaction_code conversion be in BMO parser?
        assert self._run_parser('bmo_savings_2016-08.csv') == [
            _T(7, '2016-08-02', -1133, 'MTCC 452        FEE/FRA', _m('DS')),
            _T(8, '2016-08-02', 160000, '', _m('CD')),
            _T(9, '2016-08-02', -200839, 'YRCC994         FEE/FRA', _m('DS')),
            _T(10, '2016-08-03', 30890, '', _m('CD')),
            _T(11, '2016-08-03', 45549, 'TF 0317#XXXX-XXX', _m('CW')),
            _T(12, '2016-08-03', 274, 'TF 2070#YYYY-YYY', _m('CW')),
            _T(13, '2016-08-03', -200000, 'TF 000000002244439ZZZZ', _m('CW')),
            _T(14, '2016-08-12', -999, 'MBNA MASTERCARD', _m('CW')),
            _T(15, '2016-08-15', -73300, 'TORONTO TAX     TAX/TAX', _m('DS')),
            _T(16, '2016-08-15', -50000, 'AP    000000002288889ZZZZ', _m('SO')),
            _T(17, '2016-08-23', -3500, 'BMO MASTERCARD', _m('CW')),
            _T(18, '2016-08-31', -2600, 'PREMIUM PLAN', _m('SC')),
            _T(19, '2016-08-31', 2600, 'FULL PLAN FEE REBATE', _m('SC')),
        ]

    def test_parse_bmo_readiline(self):
        expected_payment_method = PaymentMethod.objects.get(name='BMO Readiline')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.CAD, payment_method=expected_payment_method)
        expected_misc = {'last_4_digits': '0067'}
        assert self._run_parser('bmo_readiline_2016-09.csv') == [
            _T(4, '2016-08-15', 50000, 'AUTOMATIC PAYMENT RECEIVED - THANK YOU', expected_misc),
            _T(5, '2016-09-09', -45377, 'INTEREST ADVANCES  @ 02.70000% TO 09SEP', expected_misc),
        ]

    def test_parse_bmo_mastercard(self):
        expected_payment_method = PaymentMethod.objects.get(name='BMO Paypass Mastercard')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.CAD, payment_method=expected_payment_method)
        expected_misc = {'last_4_digits': '0004'}
        assert self._run_parser('bmo_mastercard.csv') == [
            _T(4, '2016-05-10', -150, 'TIM HORTONS #6011 TORONTO ON', expected_misc),
            _T(5, '2016-05-11', -2066, 'YYZ BOCCONE PRONTO MISSISSAUGA ON', expected_misc),
            _T(6, '2016-05-17', 134772, 'PAYMENT RECEIVED - THANK YOU', expected_misc),
            _T(7, '2016-04-13', 129, 'PAYMENT RECEIVED - THANK YOU', expected_misc),
            _T(8, '2016-04-22', -85276, 'AIR CAN 22142161633944 WINNIPEG MB', expected_misc),
            _T(9, '2016-05-07', -961, 'AROMA ESPRESSO BAR TORONTO ON', expected_misc),
            _T(10, '2016-05-07', -13300, 'PIZZERIA LIBRETTO - DA TORONTO ON', expected_misc),
            _T(11, '2016-05-07', -4028, "JOE'S HAMBURGERS RICHMOND HILLON", expected_misc),
            _T(12, '2016-05-08', -6734, 'REAL MO MOS TORONTO ON', expected_misc),
            _T(13, '2016-05-08', -369, 'TIM HORTONS 3021 QTH TORONTO ON', expected_misc),
            _T(14, '2016-05-09', -3295, 'WINE RACK 303 TORONTO ON', expected_misc),
            _T(15, '2016-05-10', -2108, 'PANERA BREAD CAFE# 620 NORTH YORK ON', expected_misc),
            _T(16, '2016-03-14', 4999, 'PAYMENT RECEIVED - THANK YOU', expected_misc),
            _T(17, '2016-03-31', -129, 'APL* ITUNES.COM/BILL 800-676-2775 ON', expected_misc),
            _T(18, '2016-02-12', 16485, 'PAYMENT RECEIVED - THANK YOU', expected_misc),
            _T(19, '2016-02-18', -4999, 'INTUIT CANADA 780-555-8787 AB', expected_misc),
        ]

    def test_mbna_mastercard(self):
        expected_payment_method = PaymentMethod.objects.get(name='MBNA Mastercard')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.CAD, payment_method=expected_payment_method)
        expected_misc = {}
        assert self._run_parser('mbna_mastercard_2016-09.csv') == [
            _T(2, '2016-09-15', 999, 'PAYMENT', expected_misc),
            _T(3, '2016-09-16', -281, 'RELAY 4753 TORONTO ON', expected_misc),
            _T(4, '2016-09-26', -999, 'NETFLIX.COM 866-716-0414 ON', expected_misc),
        ]

    def test_parse_capitalone(self):
        expected_payment_method = PaymentMethod.objects.get(name='CapitalOne Platinum Mastercard')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.USD, payment_method=expected_payment_method)

        def _m(category: str) -> dict:
            return {
                'last_4_digits': '0003',
                'category': category,
            }

        assert self._run_parser('capitalone_2017-09.csv') == [
            _T(2, '2017-09-26', 16072, 'ELECTRONIC PAYMENT', _m('Payment')),
            _T(3, '2017-09-25', -1462, 'SQ *GLAZE TERIYAKI', _m('Dining')),
            _T(4, '2017-09-24', -353, 'BOOKS INC     80700131', _m('Merchandise')),
            _T(5, '2017-09-21', -2474, 'WE BE SUSHI 5', _m('Dining')),
            _T(6, '2017-09-20', -1481, 'LEES DELI - 615 MARKET', _m('Dining')),
            _T(7, '2017-09-17', -3054, 'GRUBHUBYUMYUMHUNAN', _m('Dining')),
            _T(8, '2017-09-09', -2520, 'MARINA SUPERMARKET', _m('Merchandise')),
            _T(9, '2017-09-04', -2600, 'EMBARCADERO CINEMA 224', _m('Entertainment')),
            _T(10, '2017-09-02', -651, 'SAFEWAY  STORE00009670', _m('Merchandise')),
        ]

    def test_chase_visa_parser(self):
        expected_payment_method = PaymentMethod.objects.get(name='Chase Freedom Visa')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.USD, payment_method=expected_payment_method)

        def _m(category: str, chase_type: str) -> dict:
            return {
                'category': category,
                'type': chase_type,
            }

        assert self._run_parser('chase_visa_2019-02.csv') == [
            _T(2, '2019-02-28', 533398, 'Payment Thank You - Bill', _m('', 'Payment')),
            _T(3, '2019-02-27', -2398, 'INTUIT *TURBOTAX', _m('Shopping', 'Sale')),
            _T(4, '2019-02-26', -700, 'GITHUB.COM', _m('Shopping', 'Sale')),
            _T(5, '2019-02-24', -5770, 'MAINLAND MARKET', _m('Groceries', 'Sale')),
            _T(6, '2019-02-24', -4283, 'HODALA RESTAURANT.', _m('Food & Drink', 'Sale')),
            _T(7, '2019-02-03', -800100, 'BANANAREPUBLIC US 8035', _m('Shopping', 'Sale')),
        ]

    def test_wellsfargo_checking(self):
        expected_payment_method = PaymentMethod.objects.get(name='Wells Fargo Checking')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.USD, payment_method=expected_payment_method)

        assert self._run_parser('wellsfargo_checking_2016-08.csv') == [
            _T(1, '2016-08-31', 16636, "GUSTO PAY 666666 555555 6AAAAAA06uq John Doe", {}),
            _T(2, '2016-08-30', -7666, "AUTOINSURANCE PNOT.DED. 555555 333264420000 DOE, JOHN", {}),
            _T(3, '2016-08-30', -214080,
               "BILL PAY CHASE CARD SERVI ON-LINE xxxxxxxxxxx10001 ON 08-30", {}),
            _T(4, '2016-08-29', -23127,
               "ONLINE TRANSFER REF #IBE5SMGBDB TO SECURED CARD XXXXXXXXXXXX0002 ON 08/27/16", {}),
            _T(5, '2016-08-29', 500, "VENMO-0 CASHOUT XXXXX1595 JOHN DOE", {}),
            _T(6, '2016-08-25', -2000,
               "Cash eWithdrawal in Branch/Store 08/25/2016 12:49 PM"
               " 2055 CHESTNUT ST SAN FRANCISCO CA 1710",
               {}),
            _T(7, '2016-08-24', -44620,
               "BILL PAY CAPITAL ONE CRED ON-LINE xxxxxxxxxxx70003 ON 08-24", {}),
            _T(8, '2016-08-19', -32000,
               "CHECK # 136", {}),
            _T(9, '2016-08-18', -5480, "PGANDE WEB ONLINE AUG 16 44444444444444 JOHN DOE", {}),
            _T(10, '2016-08-15', 31, "INTEREST PAYMENT", {}),
            _T(11, '2016-08-16', -10000,
               "ATM WITHDRAWAL AUTHORIZED ON 08/16 2055 CHESTNUT ST SAN FRANCISCO CA"
               " 0009985 ATM ID 0021D CARD 0069", {}),
            _T(12, '2016-08-15', 8035, "GUSTO PAY 555555 666666 6AAAAAAlbri John Doe", {}),
            _T(13, '2016-08-08', -1555, "DEPOSITED OR CASHED CHECK # 131", {}),
            _T(14, '2016-08-01', -2000,
               "BART-CLIPPER POWELL SAN FRANCISCO CA"
               " P00000000000000002 CARD 0069", {'authorized_purchase_on': '07/31'}),
            _T(15, '2016-08-01', -2000,
               "BART-CLIPPER POWELL SAN FRANCISCO CA"
               " P00000000000000008 CARD 0069", {'authorized_purchase_on': '07/31'}),
        ]

    def test_wellsfargo_visa(self):
        expected_payment_method = PaymentMethod.objects.get(name='Wells Fargo Visa Card')
        _T = functools.partial(_make_expected_transaction,    # pylint:disable=invalid-name
                               currency=Currency.USD, payment_method=expected_payment_method)

        assert self._run_parser('wellsfargo_visa_2016-09.csv') == [
            _T(1, '2016-09-27', 19815, "ONLINE PAYMENT", {}),
            _T(2, '2016-09-27', -2172, "WALGREENS #1403 SAN FRANCISCOCA", {}),
            _T(3, '2016-09-16', -714, "CHESTNUT ST COFFEE ROASTESAN FRANCISCOCA", {}),
            _T(4, '2016-09-04', -218, "REDBOX *DVD RENTAL OAKBROOK TER IL", {}),
            _T(5, '2016-09-03', -1469, "CREPEVINE OAKLAND OAKLAND CA", {}),
            _T(6, '2016-09-02', -575, "SQ *HAPPY DUMPLINGS HAYWARD CA", {}),
            _T(7, '2016-09-01', -11900, "CHARIOT TRANSIT INC. 855-444-8111 CA", {}),
            _T(8, '2016-09-01', -2500, "ANNUAL FEE FOR 01/16 THROUGH 12/16", {}),
        ]
