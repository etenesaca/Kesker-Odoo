# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import threading
import time

from openerp import addons
from openerp import pooler
from openerp.addons.kemas import kemas_extras
from openerp.api import Environment
from openerp.osv import fields, osv
from openerp.tools.translate import _


class kemas_send_notification_event_wizard(osv.osv_memory):
    timeout_send_email = 150
    collaborator_ids_send_email = {}
    
    def refresh(self, cr, uid, ids, context=None):
        this = self.read(cr, uid, ids[0])
        event_obj = self.pool.get('kemas.event')
        event_id = this['event_id']
        event_line_ids = event_obj.read(cr, uid, event_id, ['event_collaborator_line_ids'])['event_collaborator_line_ids']
        sending_emails = event_obj.read(cr, uid, event_id, ['sending_emails'])['sending_emails']
        collaborator_ids_send_email = event_obj.read(cr, uid, event_id, ['collaborator_ids_send_email'])['collaborator_ids_send_email']
        
        # --Crear el Wizard de Envio de Correos
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        wizard_obj = self.pool.get('kemas.send.notification.event.wizard')
        wizard_line_obj = self.pool.get('kemas.send.notification.event.line.wizard')
        collaborator_obj = self.pool.get('kemas.collaborator')     
        
        for event_line_id in event_line_ids:
            event_line = event_line_obj.read(cr, uid, event_line_id, [])
            collaborator = collaborator_obj.read(cr, uid, event_line['collaborator_id'][0], ['id', 'email'])
            if event_line['send_email_state'] == 'Sent':
                send_email = False
                if sending_emails:
                    state = 'Successful'
                else:
                    state = 'Sent'
            elif event_line['send_email_state'] == 'Waiting':
                send_email = True
                state = 'Waiting'
            elif event_line['send_email_state'] == 'Error':
                send_email = True
                state = 'Error'
            elif event_line['send_email_state'] == 'Timeout':
                send_email = True
                state = 'Timeout'
                
            wizard_line_obj.create(cr, uid, {
                        'wizard_id': ids[0],
                        'collaborator_id': collaborator['id'],
                        'email': collaborator['email'],
                        'state': state,
                        'send_email': send_email,
                        'event_line_id':event_line_id,
                        })
        
    def stop(self, cr, uid, ids, context=None):
        event_obj = self.pool.get('kemas.event')
        event_id = self.read(cr, uid, ids[0], ['event_id'])['event_id']
        vals = {'sending_emails': False}
        super(addons.kemas.kemas.kemas_event, event_obj).write(cr, uid, [event_id], vals)
        sql = """DELETE FROM kemas_send_notification_event_line_wizard where wizard_id = %d""" % ids[0]
        cr.execute(sql)
        cr.commit()
        self.refresh(cr, uid, ids, context)
        self.write(cr, uid, ids, vals)
        return{       
                'res_id' : ids[0],
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'kemas.send.notification.event.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
                }
        
    def reset(self, cr, uid, ids, context={}):
        wizard_line_obj = self.pool.get('kemas.send.notification.event.line.wizard')
        line_ids = self.read(cr, uid, ids[0], ['send_notification_event_line_wizard_ids'])['send_notification_event_line_wizard_ids']
        for line_id in line_ids:
            wizard_line_obj.write(cr, uid, [line_id], {
                                            'state':'Waiting',
                                            'send_email':True,
                                            'sent_date': False
                                            })
        return{       
                'res_id' : ids[0],
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'kemas.send.notification.event.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
                }
    
    def send_email(self, cr, uid, ids, context={}):
        this = self.read(cr, uid, ids[0])
        wizard_line_obj = self.pool.get('kemas.send.notification.event.line.wizard')
        line_ids = self.read(cr, uid, ids[0], ['send_notification_event_line_wizard_ids'])['send_notification_event_line_wizard_ids']
        lines = wizard_line_obj.read(cr, uid, line_ids)
        _lines = []
        collaborator_ids_send_email = []
        for line in lines:
            if line['send_email']:
                _lines.append(line)
                collaborator_ids_send_email.append(line['collaborator_id'][0])
        event_obj = self.pool.get('kemas.event')
        vals = {
                'collaborator_ids_send_email' : [(6, 0, collaborator_ids_send_email)]
                }
        super(addons.kemas.kemas.kemas_event, event_obj).write(cr, uid, this['event_id'], vals)
        if len(_lines) == 0:
            raise osv.except_osv(u'¡Operación no válida!', _('No staff to send notifications.'))
        
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['work_in_background_event']:
            threaded_sending = threading.Thread(target=self._send_email_thr, args=(cr.dbname , uid, ids[0], context))
            threaded_sending.start()
            return{       
                'res_id' : this['event_id'],
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'kemas.event',
                'type': 'ir.actions.act_window',
                }
        else:
            self._send_email(cr, uid, ids, context)
            
    def _send_email_thr(self, db_name, uid, ids, context={}):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        self._send_email(cr, uid, ids, context)
        
    def _send_email(self, cr, uid, ids, context={}):
        def send():
            try:
                res = config_obj.send_email_event(cr, uid, int(line['event_line_id']), context)
                if not res:
                    return 'Error'
                else:
                    return 'Successful'
            except:
                return 'Error'
        
        with Environment.manage():    
            config_obj = self.pool.get('kemas.config')
            wizard_line_obj = self.pool.get('kemas.send.notification.event.line.wizard')
            line_obj = self.pool.get('kemas.event.collaborator.line') 
            event_obj = self.pool.get('kemas.event')
            #-------------------------------------------------------------------------------------------------------------
            if type(ids).__name__ == 'list':
                wizard_id = ids[0]
            else:
                wizard_id = ids
            
            event_id = self.read(cr, uid, wizard_id, ['event_id'])['event_id']
            super(kemas_send_notification_event_wizard, self).write(cr, uid, wizard_id, {'sending_emails':True})
            cr.commit()
            super(addons.kemas.kemas.kemas_event, event_obj).write(cr, uid, event_id, {'sending_emails':True})
            cr.commit()
    
            line_ids = self.read(cr, uid, wizard_id, ['send_notification_event_line_wizard_ids'])['send_notification_event_line_wizard_ids']
            lines = wizard_line_obj.read(cr, uid, line_ids)
            _lines = []
            for line in lines:
                if line['send_email']:
                    _lines.append(line)
            
            if len(_lines) == 0:
                raise osv.except_osv(u'¡Operación no válida!', _('No staff to send notifications.'))
            
            if not self.collaborator_ids_send_email.has_key(event_id):
                self.collaborator_ids_send_email[event_id] = []
            for line in _lines:
                self.collaborator_ids_send_email[event_id].append(line['collaborator_id'][0])
                line_obj.write(cr, uid, [long(line['event_line_id'])], {
                                            'send_email_state':'Waiting',
                                            })
            cr.commit()
            for line in _lines:
                cr.commit()
                sending_emails = event_obj.read(cr, uid, event_id, ['sending_emails'])['sending_emails']
                if sending_emails == False: break
                res_email = kemas_extras.timeout(send, timeout_duration=self.timeout_send_email, default='Timeout')
                if res_email == 'Successful':
                    wizard_line_obj.write(cr, uid, [line['id']], {
                                        'state':'Successful',
                                        'send_email': False,
                                        'sent_date' : time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                    line_obj.write(cr, uid, [long(line['event_line_id'])], {
                                        'send_email_state':'Sent',
                                        'sent_date' : time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                elif res_email == 'Error':
                    wizard_line_obj.write(cr, uid, [line['id']], {
                                        'state':'Error',
                                        'send_email':True,
                                        'sent_date' : time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                    line_obj.write(cr, uid, [long(line['event_line_id'])], {
                                        'send_email_state':'Error',
                                        'sent_date' : time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                elif res_email == 'Timeout':
                    wizard_line_obj.write(cr, uid, [line['id']], {
                                        'state':'Timeout',
                                        'send_email':True,
                                        'sent_date' : time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                    line_obj.write(cr, uid, [long(line['event_line_id'])], {
                                        'send_email_state':'Timeout',
                                        'sent_date' : time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                cr.commit()
            cr.commit()
            super(kemas_send_notification_event_wizard, self).write(cr, uid, wizard_id, {'sending_emails': False})
            super(addons.kemas.kemas.kemas_event, event_obj).write(cr, uid, event_id, {'sending_emails': False})
            try:
                del self.collaborator_ids_send_email[event_id]
            except:None
            cr.commit()

    _name = 'kemas.send.notification.event.wizard'
    _rec_name = 'state'
    _columns = {
        'send_notification_event_line_wizard_ids': fields.one2many('kemas.send.notification.event.line.wizard', 'wizard_id', 'lines', help='description'),
        'state': fields.char('State', size=15),
        'sending_emails': fields.boolean('Sending emails?'),
        'sending_sel': fields.selection([
            ('sending', 'Sending e-mails...'),
        ], 'State', select=True, readonly=True),
        'event_id': fields.integer('event_id'),
        }
    _defaults = {
        'state':'init',
        'sending_sel':'sending'
    }
class kemas_send_notification_event_line_wizard(osv.osv_memory):
    def on_change_send_email(self, cr, uid, ids, event_line_id, send_email):
        values = {}
        if send_email:
            values['state'] = 'Waiting'
        else:
            event_line_obj = self.pool.get('kemas.event.collaborator.line')
            send_email_state = event_line_obj.read(cr, uid, int(event_line_id), ['send_email_state'])['send_email_state']
            if send_email_state == 'Sent':
                values['state'] = 'Sent'
            else:
                values['state'] = 'Ignored'
        return {'value':values}

    def on_change_email(self, cr, uid, ids, email):
        values = {}
        if not kemas_extras.validate_mail(email):
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('E-mail format invalid..!!'))[0]
            return {'value':{'email': False}, 'warning':{'title':'Error', 'message':msg}}
        return {'value':values}
        
    _name = 'kemas.send.notification.event.line.wizard'
    _rec_name = 'collaborator_id'
    _columns = {
        'wizard_id': fields.many2one('kemas.send.notification.event.wizard', 'wizard_parent', ondelete='cascade', required=True, help='description'),
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', ondelete='cascade', required=True),
        'email': fields.char('email', size=255, required=True),
        'state': fields.selection([
            ('Sent', 'Sent'),
            ('Waiting', 'Waiting'),
            ('Error', 'Error'),
            ('Timeout', 'Timeout'),
            ('Successful', 'Successful'),
            ('Ignored', 'Ignored'),
            ], 'State'),
        'event_line_id': fields.char('event_line', size=15, required=True),
        'send_email': fields.boolean('Send?'),
        'sent_date': fields.datetime('Fecha'),
        }
class kemas_message_sending_begun_wizard(osv.osv_memory):
    _name = 'kemas.message.sending.begun.wizard'
    _columns = {
        'name': fields.char('Name', size=5, readonly=True),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

