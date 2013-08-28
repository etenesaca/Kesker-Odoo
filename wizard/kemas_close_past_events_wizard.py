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

import time
from osv import fields, osv
from tools.translate import _

class kemas_close_past_event_wizard(osv.osv_memory):
    def load_form(self,cr,uid,ids,context={}):
        self.write(cr, uid, ids,{'state':'loaded'})
        self.load_events(cr, uid, ids, context)
        wizard_title = self.pool.get('kemas.func').get_translate(cr, uid, _('Close past events'))[0]
        return {                      
            'context':context,
            'res_id' : ids[0],
            'view_type': 'form',
            'name': wizard_title, 
            'view_mode': 'form', 
            'res_model': 'kemas.close.past.event.wizard', 
            'type': 'ir.actions.act_window',
            'target':'new',
            }
        
    def load_events(self,cr,uid,ids,context=None):
        wizard_line_obj = self.pool.get('kemas.close.past.event.line.wizard')
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        #----------------------------------------------------------------------------------------------------------
        event_obj = self.pool.get('kemas.event')
        event_ids = event_obj.get_past_events(cr, uid)
        #Eliminar las lineas que ya se hayan agregado--------------------------------------------------------------
        lines = self.read(cr, uid, ids[0],['line_ids'])['line_ids']
        wizard_line_obj.unlink(cr, uid, lines)
        #----------------------------------------------------------------------------------------------------------
        for event_id in event_ids:
            wizard_line_obj.create(cr, uid, {
                        'wizard_id': ids[0],
                        'event_id': event_id,
                        })
        wizard_title = self.pool.get('kemas.func').get_translate(cr, uid, _('Close past events'))[0]
        return {                                  
            'context':context,
            'res_id' : ids[0],
            'view_type': 'form',
            'name': wizard_title, 
            'view_mode': 'form', 
            'res_model': 'kemas.close.past.event.wizard', 
            'type': 'ir.actions.act_window',
            'target':'new',
            }
        
    def close_events(self,cr,uid,ids,context=None):
        wizard_line_obj = self.pool.get('kemas.close.past.event.line.wizard')
        event_obj = self.pool.get('kemas.event')
        #----------------------------------------------------------------------------------------------------------
        lines = self.read(cr, uid, ids[0],['line_ids'])['line_ids']
        if len(lines) == 0:
             raise osv.except_osv(_('Warning!'), _('There are no events to close.'))
        else:
            event_obj.close_past_events(cr, uid)
            context['message'] = self.pool.get('kemas.func').get_translate(cr, uid, _('Closing of events has begun...'))[0]            
            return{            
                'context': context,
                'name' : 'Close of past events',
                'view_type': 'form', 
                'view_mode': 'form', 
                'res_model': 'kemas.message.wizard', 
                'type': 'ir.actions.act_window', 
                'target':'new',
                }

    _name='kemas.close.past.event.wizard'
    _columns={
        'line_ids': fields.one2many('kemas.close.past.event.line.wizard', 'wizard_id', 'Events'),
        'state':fields.selection([
            ('loading','Loading'),
            ('loaded','Loaded'),
            ],    'State'),
        }
    _defaults = {  
        'state': 'loading'
        }

class kemas_close_past_event_line_wizard(osv.osv_memory):
    _name='kemas.close.past.event.line.wizard'
    _columns={
        'wizard_id':fields.many2one('kemas.close.past.event.wizard','wizard_id',ondelete='cascade', required=True),
        'event_id':fields.many2one('kemas.event','Event',ondelete='cascade',required=True),
        #--Realted Fields------------------------------------------------------------------------------------
        'code': fields.related('event_id', 'code', type='char', string='Code', store=True),
        'service_id': fields.related('event_id','service_id',type="many2one",relation="kemas.service",string="Service",store=True),
        'date_start': fields.related('event_id', 'date_start', type='datetime', string='Date start', store=True),
        'date_end': fields.related('event_id', 'date_stop', type='datetime', string='Date end', store=True),
        'date_create': fields.related('event_id', 'date_create', type='datetime', string='Date Create', store=True),
        'state': fields.related('event_id', 'state', type='selection', selection=[
                                                                            ('draft','Draft'),
                                                                            ('on_going','On Going'),
                                                                            ('closed','Closed'),
                                                                            ('canceled','Canceled'),
                                                                            ],  string='State', store=True),
        }
class kemas_message_closign_begun_wizard(osv.osv_memory):
    _name = 'kemas.message.closing.begun.wizard'
    _columns = {
        'name' : fields.char('Name',size=5, readonly=True),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

