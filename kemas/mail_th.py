# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv


class mail_th(osv.AbstractModel):
    _name = 'mail.th'
    
    def log_change_state(self, cr, uid, record_id, model, title, type_operation, old_state, new_state, context={}):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        body = u'''
        <div>
            <span>
                %s
                <div>     • <b>%s</b>: %s → %s</div>
            </span>
        </div>
        ''' % (title, type_operation, old_state, new_state)
        context['notify_all_followers'] = True
        return self.log_write(cr, uid, record_id, model, body, context=context)
    
    def log_create(self, cr, uid, record_id, model, body, context={}):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        if not body:
            body = u'''
            <div>
                <span>
                    <b>CREACIÓN</b> del registro
                </span>
            </div>
            '''
        if context.get('delete_uid_followers', False):
            # Quitar el partner del usuario que crear el estudiante de los seguidores
            user = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])
            self.pool.get(model).write(cr, uid, [record_id], {'message_follower_ids': [(3, user['partner_id'][0])]}, context)
        return self.log_write(cr, uid, record_id, model, body, context=context)
    
    def log_write(self, cr, uid, record_id, model, body, notify_partner_ids=[], context={}):
        user_obj = self.pool.get('res.users')
        message_obj = self.pool.get('mail.message')
        notification_obj = self.pool.get('mail.notification')
        
        obj = self.pool.get(model)
        record_name = obj.name_get(cr, uid, [record_id])[0][1]
        partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        vals_message = {
                        'body' : body,
                        'model' : model,
                        'record_name' : record_name,
                        'res_id' : record_id,
                        'type' : 'notification',
                        'author_id' : partner_id,
                        }
        message_id = message_obj.create(cr, uid, vals_message, context)
        if context.get('notify_all_followers'):
            notify_partner_ids = super(osv.osv, obj).read(cr, uid, record_id, ['message_follower_ids'])['message_follower_ids']
        
        for notify_partner_id in notify_partner_ids:
            vals_notication = {
                               'message_id' : message_id,
                               'partner_id' : notify_partner_id,
                               }
            notification_obj.create(cr, uid, vals_notication, context)
        return message_id
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
