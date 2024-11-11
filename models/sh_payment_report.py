# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields


class SalesPaymentReport(models.Model):
    _name = 'sh.payment.report'
    _description = 'Payment Report'

    name = fields.Char(string='Invoice')
    invoice_date = fields.Date(string='Invoice Date', index=True,)
    invoice_user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True,)
    sh_partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True)
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                  self: self.env.user.company_id.currency_id.id)
    bank = fields.Monetary(string='Bank',)
    cash = fields.Monetary(string='Cash',)
    total = fields.Monetary(string='Total',)
