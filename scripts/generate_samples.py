"""Generates deterministic demo data: Aug+Sep 2026 as HDFC-style CSV, Oct 2026 as a PDF statement,
1-21 Nov 2026 as ~25 bank SMS. Run: python scripts/generate_samples.py"""
import calendar
import os
import random
from datetime import date

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")
rng = random.Random(7)


def r(lo, hi, step=1):
    return float(rng.randrange(lo, hi + 1, step))


def month_events(y, m, last_day=None):
    """-> list of (date, narration, amount) for a month. Negative = debit."""
    nd = last_day or calendar.monthrange(y, m)[1]
    D = lambda d: date(y, m, min(d, nd))
    ev = []
    add = lambda d, n, a: ev.append((D(d), n, a)) if d <= nd else None
    add(1, "NEFT-ACME TECHNOLOGIES SALARY", 85000.0)
    add(5, "UPI-RAMESH KUMAR-RENT-ramesh.k@okhdfcbank-5521", -22000.0)
    add(6, "UPI-BESCOM-ELECTRICITY BILL-bescom@paytm", -r(1700, 2400, 10))
    add(8, "UPI-AIRTEL BROADBAND-airtelbb@icici", -1179.0)
    add(9, "UPI-JIO PREPAID RECHARGE-jio@ybl", -399.0)
    add(10, "NACH-BAJAJ FINSERV EMI-LAPTOP LOAN", -3500.0)
    add(2, "UPI-LIC PREMIUM-lic@sbi", -1250.0)
    add(3, "SIP-GROWW MUTUAL FUND-NACH", -5000.0)
    add(5, "UPI-NETFLIX-netflix@icici", -(649.0 if m < 11 else 799.0))
    add(7, "UPI-SPOTIFY INDIA-spotify@axis", -119.0)
    add(7, "UPI-HOTSTAR-hotstar@ybl", -299.0)
    add(12, "UPI-CULT.FIT GYM MEMBERSHIP-cultfit@hdfc", -1499.0)
    add(11, "UPI-APPLE ICLOUD-icloud@apple", -75.0)
    dining_n = 14 if m == 11 else 8
    dining_names = ["UPI-SWIGGY-swiggy.order@axisbank", "UPI-ZOMATO-zomato@icici", "POS-STARBUCKS COFFEE",
                    "UPI-KAMAT UPAHAR-kamat@okaxis", "UPI-SWIGGY-swiggy.order@axisbank", "POS-DOMINOS PIZZA"]
    for i in range(dining_n):
        add(rng.randint(1, nd), rng.choice(dining_names), -r(180, 780 if m != 11 else 950, 10))
    for i in range(9):
        add(rng.randint(1, nd), rng.choice(["UPI-BIGBASKET-bigbasket@icici", "UPI-BLINKIT-blinkit@ybl",
                                           "POS-DMART AVENUE SUPERMARKET", "UPI-SRI GANESH PROVISION STORE-sgstores@ybl"]),
            -r(220, 1500, 10))
    for i in range(7):
        add(rng.randint(1, nd), rng.choice(["UPI-UBER INDIA-uber@axis", "UPI-OLA CABS-ola@ybl", "UPI-RAPIDO-rapido@ybl",
                                           "POS-INDIAN OIL PETROL PUMP"]), -r(90, 700, 10))
    for i in range(2):
        add(rng.randint(1, nd), rng.choice(["POS-AMAZON PAY INDIA", "UPI-MYNTRA-myntra@icici", "POS-FLIPKART"]),
            -r(600, 2400, 10))
    add(rng.randint(10, 25), "UPI-APOLLO PHARMACY-apollo@ybl", -r(250, 900, 10))
    add(rng.randint(14, 27), "UPI-URBAN COMPANY HOME SERVICES-urbancompany@hdfcbank", -r(400, 900, 50))
    add(rng.randint(14, 27), "ATM-CASH WDL-HSR LAYOUT", -2000.0)
    add(rng.randint(14, 27), "POS-BOOKMYSHOW", -r(300, 700, 10))
    return sorted(ev, key=lambda e: e[0])


def fmt_inr(v):
    s = f"{abs(v):.2f}"
    ip, fp = s.split(".")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        ip = ",".join(parts) + "," + tail
    return f"{ip}.{fp}"


def with_balance(events, opening):
    bal, out = opening, []
    for d, n, a in events:
        bal += a
        out.append((d, n, a, bal))
    return out, bal


def write_csv(rows):
    p = os.path.join(OUT, "hdfc_aug_sep_2026.csv")
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write("HDFC BANK LTD,Statement of account,,,,,\n")
        f.write("Account No: XXXXXX4821,Period: 01/08/2026 to 30/09/2026,,,,,\n,,,,,,\n")
        f.write("Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance\n")
        for d, n, a, b in rows:
            ds = d.strftime("%d/%m/%y")
            f.write(f'{ds},"{n}",{rng.randint(10**11, 10**12 - 1)},{ds},'
                    f'{"" if a > 0 else f"{abs(a):.2f}"},{"" if a < 0 else f"{a:.2f}"},{b:.2f}\n')


def write_pdf(rows):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    p = os.path.join(OUT, "icici_oct_2026_statement.pdf")
    c = canvas.Canvas(p, pagesize=A4)
    w, h = A4

    def header(y):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "ICICI BANK - Statement of Account (Savings)")
        c.setFont("Helvetica", 8)
        c.drawString(40, y - 14, "Account XXXX4821 | 01 Oct 2026 to 31 Oct 2026")
        c.setFont("Helvetica-Bold", 8)
        c.drawString(40, y - 34, "Date")
        c.drawString(100, y - 34, "Transaction Details")
        c.drawString(380, y - 34, "Amount (INR)")
        c.drawString(470, y - 34, "Balance (INR)")
        return y - 48

    y = header(h - 50)
    c.setFont("Helvetica", 8)
    for d, n, a, b in rows:
        if y < 50:
            c.showPage()
            y = header(h - 50)
            c.setFont("Helvetica", 8)
        c.drawString(40, y, d.strftime("%d/%m/%Y"))
        c.drawString(100, y, n[:48])
        c.drawRightString(440, y, fmt_inr(a))
        c.drawRightString(540, y, fmt_inr(b))
        y -= 13
    c.save()


def sms_lines(events):
    """Mix of bank SMS formats (HDFC / SBI / ICICI / Axis style), plus noise."""
    out = []
    for d, n, a in events:
        amt = fmt_inr(a)
        nm = n.split("-")
        label = nm[1] if len(nm) > 1 else n
        handle = n.split("-")[2] if n.count("-") >= 2 and "@" in n else None
        style = rng.randint(0, 3)
        if a > 0:
            out.append(f"Rs.{amt} credited to A/c XX4821 on {d.strftime('%d-%m-%y')} by NEFT-{label.title()}. "
                       f"Avl Bal Rs.{fmt_inr(60000)}. -HDFC Bank")
            continue
        if n.startswith("UPI-") and handle:
            vpa = handle
            if style == 0:
                out.append(f"Rs.{amt} debited from A/c XX4821 on {d.strftime('%d-%m-%y')} to VPA {vpa} "
                           f"({label.title()}) Ref {rng.randint(10**11, 10**12 - 1)}. -HDFC Bank")
            elif style == 1:
                out.append(f"Sent Rs.{amt} from HDFC Bank A/c *4821 to {label.title()} on {d.strftime('%d%b%y')} "
                           f"UPI Ref {rng.randint(10**11, 10**12 - 1)}")
            elif style == 2:
                out.append(f"INR {amt} debited from a/c XX4821 on {d.strftime('%d-%b-%Y')}. Info: UPI/{label.title()}/"
                           f"{rng.randint(10**8, 10**9)}. Avl Bal INR 41,220.00 - ICICI Bank")
            else:
                out.append(f"Your A/c XX4821 is debited by Rs {amt} on {d.strftime('%d/%m/%Y')} VPA {vpa}. -Axis Bank")
        elif n.startswith("POS-"):
            out.append(f"INR {amt} spent on HDFC Bank Card XX9034 at {n[4:].title()} on {d.strftime('%d-%b-%y')}. "
                       f"Avl limit INR 1,12,300.00")
        elif n.startswith("ATM"):
            out.append(f"Rs.{amt} withdrawn from A/c XX4821 at ATM HSR LAYOUT on {d.strftime('%d-%m-%y')}. "
                       f"Avl Bal Rs.38,000.00 -SBI")
        else:
            out.append(f"Rs.{amt} debited from A/c XX4821 on {d.strftime('%d-%m-%y')} for {label.title()}. -HDFC Bank")
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    aug = month_events(2026, 8)
    sep = month_events(2026, 9)
    csv_rows, bal = with_balance(aug + sep, 62000.0)
    write_csv(csv_rows)
    octe = month_events(2026, 10)
    pdf_rows, bal = with_balance(octe, bal)
    write_pdf(pdf_rows)
    nov = month_events(2026, 11, last_day=21)
    lines = sms_lines(nov)
    lines.insert(3, "Your OTP for transaction is 482913. Do not share it with anyone. -HDFC Bank")
    lines.insert(9, "Rs.1,179.00 will be debited on 08-12-26 for Airtel Broadband. Maintain sufficient balance.")
    lines.insert(15, "Dear customer, get 5% cashback on your next Swiggy order! T&C apply.")
    with open(os.path.join(OUT, "sms_nov_2026.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines) + "\n")
    print("rows:", len(csv_rows), len(pdf_rows), "sms:", len(lines))


if __name__ == "__main__":
    main()
