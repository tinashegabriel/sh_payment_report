# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, models, fields
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class PaymentReport(models.AbstractModel):
    _name = 'report.sh_payment_report.sh_payment_report_doc'
    _description = 'invoice payment report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]
        
        # Updated this to find payment Between Dates
        payment_domain=[]
        payment_domain.append(('date', '>=', data['date_start']))
        payment_domain.append(('date', '<=', data['date_end']))
        
        all_payments=account_payment_obj.sudo().search(payment_domain) #find Payment Between Dates
        
        move_ids=[]
        if all_payments:
            move_ids=all_payments.reconciled_invoice_ids.ids
        else:
            raise UserError('There is no Data Found between these dates...')

        # Updated this to find payment Between Dates

        journal_domain = [('type', 'in', ['bank', 'cash'])]
        if data.get('company_ids', False):
            journal_domain.append(
                ("company_id", "in", data.get('company_ids', False)))
        search_journals = account_journal_obj.sudo().search(journal_domain)

        final_col_list = ["Invoice", "Invoice Date", "Salesperson", "Customer"]
        final_total_col_list = []
        for journal in search_journals:
            if journal.name not in final_col_list:
                final_col_list.append(journal.name)
            if journal.name not in final_total_col_list:
                final_total_col_list.append(journal.name)

        final_col_list.append("Total")
        final_total_col_list.append("Total")

        currency = False
        grand_journal_dic = {}
        j_refund = 0.0
        user_data_dic = {}
        if data.get("user_ids", False):
            for user_id in data.get("user_ids"):
                invoice_pay_dic = {}
                invoice_domain = [
                    ('invoice_user_id', '=', user_id)
                ]
                if data.get("state", False):
                    state = data.get("state")
                    if state == 'all':
                        invoice_domain.append(
                            ('state', 'in', ['posted', 'draft']))
                    elif state == 'open':
                        invoice_domain.append(
                            ('payment_state', '=', 'partial'))
                        invoice_domain.append(('amount_residual', '!=', 0.0))
                    elif state == 'paid':
                        invoice_domain.append(('payment_state', '=', 'paid'))
                        invoice_domain.append(('amount_residual', '=', 0.0))
                # invoice_domain.append(
                #     ('invoice_date', '>=', data['date_start']))
                # invoice_domain.append(('invoice_date', '<=', data['date_end']))
                if data.get('company_ids', False):
                    invoice_domain.append(
                        ("company_id", "in", data.get('company_ids', False)))
                # journal wise payment first we total all bank, cash etc etc.
                invoice_ids = self.env['account.move'].sudo().search(
                    invoice_domain)
                print(f"\n\n\n==>> invoice_ids: {invoice_ids}")
                if invoice_ids:
                    for invoice in invoice_ids.filtered(lambda l: l.id in move_ids):
                        pay_term_line_ids = invoice.line_ids.filtered(
                            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
                        partials = pay_term_line_ids.mapped(
                            'matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
                        if partials:
                            # journal wise payment first we total all bank, cash etc etc.

                            for partial in partials:
                                counterpart_lines = partial.debit_move_id + partial.credit_move_id
                                counterpart_line = counterpart_lines.filtered(
                                    lambda line: line.id not in invoice.line_ids.ids)
                                foreign_currency = invoice.currency_id if invoice.currency_id != self.env.company.currency_id else False
                                if foreign_currency and partial.credit_currency_id == foreign_currency:
                                    payment_amount = partial.amount
                                else:
                                    payment_amount = partial.company_currency_id._convert(
                                        partial.amount, invoice.currency_id, self.env.company, fields.Date.today())

                                if float_is_zero(payment_amount, precision_rounding=invoice.currency_id.rounding):
                                    continue
                                if not currency:
                                    currency = invoice.currency_id
                                if invoice.move_type == "out_invoice":
                                    print("\n\n\n\n\n\n92 counterpart_line",counterpart_line)
                                    print(f"\n\n\n==>> invoice_pay_dic: {invoice_pay_dic}")
                                    if invoice_pay_dic.get(invoice.name, False):
                                        pay_dic = invoice_pay_dic.get(
                                            invoice.name)
                                        total = pay_dic.get("Total")
                                        if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                            amount = pay_dic.get(
                                                counterpart_line.payment_id.journal_id.name)
                                            total += payment_amount
                                            amount += payment_amount
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                        else:
                                            total += payment_amount
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": total})

                                        invoice_pay_dic.update(
                                            {invoice.name: pay_dic})
                                    else:
                                        invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": payment_amount, "Invoice": invoice.name, "Customer": invoice.partner_id.name,
                                                                               "customer_id": invoice.partner_id.id,
                                                                               "Invoice Date": invoice.invoice_date, "Salesperson": invoice.invoice_user_id.name if invoice.invoice_user_id else "",
                                                                               "salesperson_id": invoice.invoice_user_id.id if invoice.invoice_user_id else "",
                                                                               "style": 'border: 1px solid black;'}})
                                
                                if invoice.move_type == "out_refund":
                                    j_refund += payment_amount
                                    if invoice_pay_dic.get(invoice.name, False):
                                        pay_dic = invoice_pay_dic.get(
                                            invoice.name)
                                        total = pay_dic.get("Total")
                                        if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                            amount = pay_dic.get(
                                                counterpart_line.payment_id.journal_id.name)
                                            total -= payment_amount
                                            amount -= payment_amount
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                        else:
                                            total -= invoice.amount_total_signed
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": total})

                                        invoice_pay_dic.update(
                                            {invoice.name: pay_dic})

                                    else:
                                        invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": -1 * (payment_amount), "Invoice": invoice.name, "Customer": invoice.partner_id.name,
                                                                               "customer_id": invoice.partner_id.id,
                                                                               "Invoice Date": invoice.invoice_date, "Salesperson": invoice.invoice_user_id.name if invoice.invoice_user_id else "",
                                                                               "salesperson_id": invoice.invoice_user_id.id if invoice.invoice_user_id else "",
                                                                               "style": 'border: 1px solid black;color:red'}})

                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for key, value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value.get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})

                        else:
                            total_journal_amount.update(
                                {col_name: value.get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user and final_list and total_journal_amount:
                    user_data_dic.update({
                        search_user.name: {'pay': final_list,
                                           'grand_total': total_journal_amount}
                    })

                for col_name in final_total_col_list:
                    j_total = 0.0
                    j_total = total_journal_amount.get(col_name, 0.0)
                    j_total += grand_journal_dic.get(col_name, 0.0)
                    grand_journal_dic.update({col_name: j_total})
            j_refund = j_refund * -1
            grand_journal_dic.update({'Refund': j_refund})

        if user_data_dic:
            data.update({
                'date_start': data['date_start'],
                'date_end': data['date_end'],
                'columns': final_col_list,
                'user_data_dic': user_data_dic,
                'currency': currency,
                'grand_journal_dic': grand_journal_dic,
            })
            return data
        else:
            raise UserError('There is no Data Found between these dates...')
