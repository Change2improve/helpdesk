from odoo import models, api, fields, _
from odoo.tools.safe_eval import safe_eval


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _inherit = ['helpdesk.ticket', 'rating.mixin']

    positive_rate_percentage = fields.Integer(
        string='Positive Rates Percentage',
        compute="_compute_percentage",
        store=True,
        default=-1)

    rating_status = fields.Selection(
        [('stage_change', 'Rating when changing stage'),
         ('no_rate', 'No rating')],
        string='Customer Rating', default="stage_change", require=True)

    @api.depends('rating_ids.rating')
    def _compute_percentage(self):
        for ticket in self:
            activity = ticket.rating_get_grades()
            ticket.positive_rate_percentage = activity['great'] * 100 / \
                sum(activity.values()) if sum(activity.values()) else -1

    @api.multi
    def write(self, vals):
        res = super(HelpdeskTicket, self).write(vals)
        if 'stage_id' in vals and vals.get('stage_id'):
            stage = self.env['helpdesk.ticket.stage'].search([
                ('id', '=', vals.get('stage_id'))])
            if(stage.rating_mail_template_id):
                self._send_ticket_rating_mail(force_send=False)
        return res

    def _send_ticket_rating_mail(self, force_send=False):
        # for ticket in self:
        if self.rating_status == 'stage_change':
            survey_template = self.stage_id.rating_mail_template_id
            if survey_template:
                self.rating_send_request(survey_template,
                                         lang=self.partner_id.lang,
                                         force_send=force_send)

    @api.multi
    def rating_apply(self, rate, token=None, feedback=None, subtype=None):
        return super(HelpdeskTicket, self).rating_apply(
            rate,
            token=token,
            feedback=feedback,
            subtype="helpdesk_mgmt_rating.mt_ticket_rating")

    def rating_get_partner_id(self):
        res = super(HelpdeskTicket, self).rating_get_partner_id()
        if not res and self.partner_id:
            return self.partner_id
        return res

    def rating_get_parent_model_name(self, vals):
        return 'helpdesk.ticket'

    def rating_get_ticket_id(self):
        return self.id

    @api.multi
    def action_view_ticket_rating(self):
        action = self.env['ir.actions.act_window'].for_xml_id(
            'helpdesk_mgmt_rating', 'helpdesk_ticket_rating_action')
        action['name'] = _('Ticket Rating')
        action_context = safe_eval(action['context']) \
            if action['context'] else {}
        action_context.update(self._context)
        action_context.pop('group_by', None)
        return dict(action, context=action_context)
