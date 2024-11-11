# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Invoice Payment Report",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Accounting",
    "summary": """Invoice Payment Report, sales person bills report app, filter different payment type, salesperson amount report, invoice report module odoo""",
    "description": """Easily filter salesperson wise payment and print report in PDF or Excel sheet.
Invoice Payment Report, sales person bills report app, filter different payment type, salesperson amount report, invoice report module odoo
 Payment Information In Invoice, Bill, Debit Note, Credit Note Odoo
 See Payment Detail In Invoice Module, View Payment Information in Bill, Get Payment Status In Credit Note, See Payment Detail In Debit Note, See Payment Information In Invoice Report, Watch Payment Status In Bill Report Odoo.
 Invoice Payment Detail Module, Payment Information in Bill, Payment Status In Credit Note App, Payment In Debit Note, Invoice Report Payment Information, Payment Bill Report Odoo.""",
    "version": "16.0.4",
    "depends": [
        "sale_management",
        "account"
    ],
    "application": True,
    "data": [
        "security/payment_report_security.xml",
        "security/ir.model.access.csv",
        "wizard/payment_report_wizard_views.xml",
        "report/payment_report_views.xml",
        "views/sh_payment_report_views.xml",
    ],
    "images": ["static/description/background.png", ],
    "license": "OPL-1",
    "auto_install": False,
    "installable": True,
    "price": 30,
    "currency": "EUR"
}
