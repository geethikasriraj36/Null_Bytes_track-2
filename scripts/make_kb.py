"""Writes the fictional OurCompany knowledge base to data/docs/ (the documents search_docs searches).
Run: python -m scripts.make_kb      (idempotent; existing faq.md, refund_policy.md and demo_*.md are kept)
Everything here is invented for the demo. Paragraphs are separated by blank lines (one search chunk each)."""
from pathlib import Path

KB = {
"hr_policy.md": """# HR policy

Every full-time employee gets 24 days of paid annual leave per calendar year. Up to 6 unused days can be carried over to the next year.

Sick leave is unlimited within reason, but a doctor's note is required after 3 consecutive sick days.

Parental leave is 26 weeks at full pay for the primary carer and 6 weeks for the secondary carer.

Payroll is processed on the 28th of every month. If the 28th is a weekend or holiday, salaries are paid on the previous working day.

The notice period is 60 days for permanent staff and 15 days during probation. Probation lasts 3 months.

Performance reviews happen twice a year, in April and October.""",

"it_security.md": """# IT and security policy

Passwords must be at least 14 characters long and are rotated every 90 days. Reusing any of your last 5 passwords is blocked.

Multi-factor authentication (MFA) is mandatory for email, the HR portal and all internal dashboards.

Lock your laptop whenever you leave your desk. Laptops auto-lock after 5 minutes of inactivity.

The VPN is required to reach internal dashboards from outside the office network.

Suspected phishing must be reported with the "Report phishing" button in the mail client within 24 hours. Never forward the suspicious email.

Company data may only be stored on company-managed laptops and the approved cloud drive. Personal USB drives are not allowed.""",

"travel_policy.md": """# Travel and expenses policy

Domestic flights must be booked at least 14 days in advance through the travel desk. Economy class only for flights under 6 hours.

The daily meal allowance is 1500 rupees for domestic travel and 60 US dollars for international travel.

Hotel stays above 6000 rupees per night need written approval from your manager.

Expense claims must be filed within 30 days of the trip, with itemised receipts. Claims are reimbursed with the next payroll.

Local cab rides for work are reimbursed in full; personal detours are not.""",

"shipping.md": """# Shipping and delivery

Standard delivery to Mumbai, Delhi and Bengaluru takes 3 business days.

Standard delivery to Chennai and Hyderabad takes 4 business days; to Pune it takes 4 business days since the last vendor update.

Express delivery is available to all metro cities for 250 rupees extra and arrives the next business day if ordered before 2 pm.

Orders above 2000 rupees ship free. Below that, standard shipping costs 99 rupees.

Orders can be tracked from the "My orders" page using the order number in the confirmation email.

We do not ship outside India at the moment.""",

"products.md": """# Product catalogue (2026)

Aegis Desk Lamp: 1499 rupees, adjustable warm and cool light, 2-year warranty.

Ergo Mesh Chair: 8999 rupees, lumbar support and 4D armrests, 5-year warranty on the frame and 2 years on the mesh.

Focus Noise-Cancelling Headphones: 6499 rupees, 30 hours of battery life, 1-year warranty.

Standing Desk Pro: 21999 rupees, dual motor, height from 62 to 127 cm, 5-year warranty.

Warranty claims are handled by the support team and require the original order number.""",

"offices.md": """# Offices

Headquarters: Bengaluru, Indiranagar. Open Monday to Friday, 9:30 to 18:00.

Pune office: Baner. Open Monday to Friday, 9:30 to 18:00. Home of the logistics team.

Chennai office: Guindy. Open Monday to Saturday, 10:00 to 17:00 on Saturdays. Home of customer support.

Visitors must be registered at reception by their host at least one day in advance and carry a photo ID.

Office parking is free for employees; visitor parking must be booked through reception.""",

"holidays_2026.md": """# Company holidays 2026

Fixed holidays: Republic Day (26 January), Holi (4 March), Independence Day (15 August), Gandhi Jayanti (2 October), Diwali (8 November) and Christmas (25 December).

Every employee also gets 2 floating holidays per year, to be used for any festival of their choice.

If a fixed holiday falls on a weekend, it is not moved to a weekday.""",

"support.md": """# Customer support

Support is open Monday to Saturday, 8:00 to 20:00 IST, by chat and phone.

Normal tickets get a first reply within one business day. Priority tickets (orders over 20000 rupees or broken items) get a reply within 4 hours.

Damaged items must be reported within 48 hours of delivery with photos.

Support agents can issue store credit up to 2000 rupees without manager approval.""",

"onboarding.md": """# New joiner onboarding

On your first day, collect your laptop and ID card from IT at the reception desk at 10:00.

Every new joiner is paired with an onboarding buddy for their first 30 days.

Mandatory trainings in week one: information security, code of conduct and data privacy. All three must be completed within 7 days.

Your first one-to-one with your manager is scheduled in the first week; your 90-day probation review is booked automatically.""",
}

if __name__ == "__main__":
    docs = Path("data/docs")
    docs.mkdir(parents=True, exist_ok=True)
    for name, text in KB.items():
        (docs / name).write_text(text + "\n", encoding="utf-8")
    print(f"wrote {len(KB)} documents to {docs}/")
