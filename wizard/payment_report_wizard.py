# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, ValidationError
import xlwt
import base64
import io
from io import BytesIO


class ShPaymentReportWizard(models.TransientModel):
    _name = "sh.payment.report.wizard"
    _description = 'invoice payment report wizard Model'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    date_start = fields.Date(
        string="Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date(
        string="End Date", required=True, default=fields.Date.today)

    state = fields.Selection([
        ('all', 'All'),
        ('open', 'Open'),
        ('paid', 'Paid'),
    ], string='Status', default='all')

    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='rel_sh_payment_report_wizard_res_user',
        string='Salesperson')

    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)

    @api.model
    def default_get(self, fields):
        rec = super(ShPaymentReportWizard, self).default_get(fields)

        search_users = self.env["res.users"].search([
            ('id', '=', self.env.user.id),
        ], limit=1)
        if self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            rec.update({
                "user_ids": [(6, 0, search_users.ids)],
            })
        else:
            rec.update({
                "user_ids": [(6, 0, [self.env.user.id])],
            })
        return rec

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]

        return self.env.ref('sh_payment_report.sh_payment_report_action').report_action([], data=datas)

    def display_report(self):
        datas = self.read()[0]
        report = self.env['report.sh_payment_report.sh_payment_report_doc']
        data_values = report._get_report_values(
            docids=None, data=datas).get('user_data_dic')
        self.env['sh.payment.report'].search([]).unlink()
        vals = list(data_values.values())
        for val in vals:
            dict_val = list(val.values())
            if len(val) > 0:
                for v in dict_val[0]:
                    bank = v.get('Bank', 0)
                    cash = v.get('Cash', 0)
                    self.env['sh.payment.report'].create({
                        'name': v['Invoice'],
                        'invoice_date': v['Invoice Date'],
                        'invoice_user_id': v['salesperson_id'],
                        'sh_partner_id': v['customer_id'],
                        'bank': bank,
                        'cash': cash,
                        'total': v['Total'],
                    })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Payment Report',
            'view_mode': 'tree',
            'res_model': 'sh.payment.report',
            'context': "{'create': False,'search_default_group_sales_person': 1}"
        }

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        total_bold = xlwt.easyxf('font:bold True')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet('Invoice Payment Report', bold_center)
        worksheet.write_merge(
            0, 1, 0, 7, 'Invoice Payment Report', heading_format)
        worksheet.write_merge(2, 2, 0, 7, str(
            self.date_start) + " to " + str(self.date_end), bold)
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]
        
        # Updated this to find payment Between Dates
        payment_domain=[]
        payment_domain.append(('date', '>=', self.date_start))
        payment_domain.append(('date', '<=', self.date_end))
        
        all_payments=account_payment_obj.sudo().search(payment_domain) #find Payment Between Dates
        move_ids=[]
        if all_payments:
            move_ids=all_payments.reconciled_invoice_ids.ids
        else:
            raise UserError('There is no Data Found between these dates...')
        
        # Updated this to find payment Between Dates
        
        currency = False
        j_refund = 0.0
        data = {}
        grand_journal_dic = {}
        user_data_dic = {}
        search_user = self.env['res.users'].sudo().search(
            [('id', 'in', self.user_ids.ids)])
        journal_domain = [('type', 'in', ['bank', 'cash'])]
        if self.company_ids:
            journal_domain.append(("company_id", "in", self.company_ids.ids))
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
        for user_id in search_user:
            invoice_pay_dic = {}
            invoice_domain = [
                ('invoice_user_id', '=', user_id.id)
            ]
            if self.state:
                state = self.state
                if state == 'all':
                    invoice_domain.append(
                        ('state', 'not in', ['draft', 'cancel']))
                elif state == 'open':
                    invoice_domain.append(('payment_state', '=', 'partial'))
                    invoice_domain.append(('amount_residual', '!=', 0.0))
                elif state == 'paid':
                    invoice_domain.append(('payment_state', '=', 'paid'))
                    invoice_domain.append(('amount_residual', '=', 0.0))
            # invoice_domain.append(
            #     ('invoice_date', '>=', self.date_start))
            # invoice_domain.append(('invoice_date', '<=', self.date_end))
            if self.company_ids:
                invoice_domain.append(
                    ("company_id", "in", self.company_ids.ids))
            # journal wise payment first we total all bank, cash etc etc.
            invoice_ids = self.env['account.move'].sudo().search(
                invoice_domain)
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
                                                                           "Invoice Date": str(invoice.invoice_date), "Salesperson": invoice.invoice_user_id.name if invoice.invoice_user_id else "", "style": ''}})
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
                                                                           "Invoice Date": str(invoice.invoice_date), "Salesperson": invoice.invoice_user_id.name if invoice.invoice_user_id else "", "style": 'font:color red'}})
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
            search_user = self.env['res.users'].search([
                ('id', '=', user_id.id)
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
                'columns': final_col_list,
                'user_data_dic': user_data_dic,
                'grand_journal_dic': grand_journal_dic,
            })
        else:
            raise UserError('There is no Data Found between these dates...')
        row = 3
        col = 0
        for user in user_data_dic.keys():
            pay_list = []
            pay_list.append(user_data_dic.get(user).get('pay', []))
            row = row + 2
            worksheet.write_merge(
                row, row, 0, 7, "Sales Person: " + user, bold_center)
            row = row + 2
            col = 0
            for column in data.get('columns'):
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column, bold)
                col = col + 1
            for p in pay_list:
                row = row + 1
                col = 0
                for dic in p:
                    row = row + 1
                    col = 0
                    for column in data.get('columns'):
                        style = xlwt.easyxf(dic.get('style', ''))
                        worksheet.write(row, col, dic.get(column, 0), style)
                        col = col + 1
            row = row + 1
            col = 3
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Total", total_bold)
            col = col + 1
            if user_data_dic.get(user, False):
                grand_total = user_data_dic.get(user).get('grand_total', {})
                if grand_total:
                    for column in data.get('columns'):
                        if column not in ['Invoice', 'Invoice Date', 'Salesperson', 'Customer']:
                            worksheet.write(row, col, grand_total.get(
                                column, 0), total_bold)
                            col = col + 1
        row = row + 2
        worksheet.write_merge(row, row, 0, 1, "Payment Method", bold)
        row = row + 1
        worksheet.write(row, 0, "Name", bold)
        worksheet.write(row, 1, "Total", bold)
        for column in data.get('columns'):
            col = 0
            if column not in ["Invoice", "Invoice Date", "Salesperson", "Customer"]:
                row = row + 1
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column)
                col = col + 1
                worksheet.write(row, col, grand_journal_dic.get(column, 0))
        if grand_journal_dic.get('Refund', False):
            row = row + 1
            col = 0
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Refund")
            worksheet.write(row, col + 1, grand_journal_dic.get('Refund', 0.0))

        filename = ('Invoice Payment Report' + '.xls')
        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": filename,
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', filename),
                                          ('type', '=', 'binary'),
                                          ('res_model', '=', 'ir.ui.view')],
                                         limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError('There is no attachments...')

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
