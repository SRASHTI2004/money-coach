import os

from app import parsing

S = os.path.join(os.path.dirname(__file__), "..", "..", "samples")


def test_amounts_indian_format():
    assert parsing.parse_amount("1,23,456.78") == 123456.78
    assert parsing.parse_amount("(500.00)") == -500
    assert parsing.parse_amount("750 Dr") == -750
    assert parsing.parse_amount("Rs. 2,000") == 2000
    assert parsing.parse_amount("") is None


def test_dates_many_formats():
    for s in ["05/09/2026", "05-09-26", "5 Sep 2026", "05-Sep-26", "2026-09-05", "05Sep26"]:
        assert parsing.parse_date(s) == "2026-09-05", s


def test_csv_with_preamble_and_split_columns():
    rows = parsing.parse_csv(open(os.path.join(S, "hdfc_aug_sep_2026.csv"), encoding="utf-8").read())
    assert len(rows) == 86
    assert rows[0]["amount"] == 85000 and rows[1]["amount"] < 0


def test_csv_single_amount_with_drcr():
    txt = "Txn Date,Description,Amount,Dr/Cr\n01/10/2026,Zomato,350.00,DR\n02/10/2026,Salary,50000,CR\n"
    r = parsing.parse_csv(txt)
    assert [x["amount"] for x in r] == [-350, 50000]


def test_pdf_balance_inference():
    rows, _ = parsing.parse_pdf_bytes(open(os.path.join(S, "icici_oct_2026_statement.pdf"), "rb").read())
    assert len(rows) == 43
    assert rows[0]["amount"] == 85000 and rows[1]["amount"] < 0


def test_pdf_text_direction_from_running_balance():
    txt = "01/10/2026 SOME CREDIT 1,000.00 11,000.00\n02/10/2026 SOME DEBIT 500.00 10,500.00"
    r = parsing.parse_pdf_text(txt)
    assert [x["amount"] for x in r] == [1000, -500]


def test_sms_formats_and_noise():
    msgs = """Rs.1,250.00 debited from A/c XX4821 on 03-11-26 to VPA lic@sbi (LIC) Ref 123456.

INR 640.00 spent on HDFC Bank Card XX9034 at Myntra on 05-Nov-26. Avl limit INR 1,00,000.00

Rs.85,000.00 credited to A/c XX4821 on 01-11-26 by NEFT-ACME. Avl Bal Rs.90,000.

Your OTP is 123456. Do not share it.

Rs.1,179.00 will be debited on 08-12-26 for Airtel. Maintain sufficient balance."""
    rows, failed = parsing.parse_sms(msgs)
    assert [r["amount"] for r in rows] == [-1250, -640, 85000]
    assert failed == []
    assert "Myntra" in rows[1]["description"]
