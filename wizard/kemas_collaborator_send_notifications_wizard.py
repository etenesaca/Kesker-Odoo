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
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import pooler
#import pooler
import threading
from openerp import addons
# import kemas
from lxml import etree

class kemas_collaborator_send_notifications_wizard(osv.osv_memory):
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=True, submenu=False):
        def mailing():
            config_obj = self.pool.get('kemas.config')
            config_id = config_obj.get_correct_config(cr, uid)
            if config_id:
                config = config_obj.read(cr, uid, config_id,['mailing','use_message_incorporation'])
                if config['mailing'] and config['use_message_incorporation']:
                    return True
                else:
                    return False
            else:
                return False
        #-----------------------------------------------------------------------------------------------------------------
        res = super(kemas_collaborator_send_notifications_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=False, submenu=False)
        if mailing():
            form = '''
                   <field name="state" invisible="1"/>    
                   <button name="load_form" type="object" string="%s" icon="STOCK_EXECUTE" colspan="4" states="loading"/>
                   <group colspan="4" expand="1" col="4" states="loaded">
                       <button name="load_form" type="object" string="%s" icon="STOCK_REFRESH" colspan="4"/>
                       <notebook colspan="4">
                        <page string="%s">    
                          <group colspan="4" expand="1">
                            <field name="line_ids" colspan="4" nolabel="1" readonly="1"/>             
                          </group>
                        </page>
                    </notebook>
                    <separator string="" colspan="4"/>
                       <group colspan="4" expand="1" col="8">
                           <group colspan="4" expand="1" col="4"></group>
                           <button name="send_notifications" type="object" string="%s" attrs="{'invisible':[('line_ids','=',False)]}"  confirm="%s" icon="terp-mail-message-new"/>
                           <button special="cancel" string="%s" icon="gtk-cancel"/>
                       </group>
                   </group>'''%(_('Load Collaborators not notified'), _('Reload Collaborators not notified'),_('Collaborators to notify'),_('Send Emails'),_('Are you sure you want to send notifications now?'),_('Cancel'))
        else:
            form = '''<label string="%s" colspan="4" align="10.10"/>'''%(_("Email notifications are disabled."))
        xml='''<form string="%s">
               %s
               </form>'''%(_('Send welcome notifications failed'),form)
        
        doc = etree.fromstring(xml.encode('utf8'))
        xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
        res['arch'] = xarch
        res['fields'] = xfields
        return res
    
    def load_form(self,cr,uid,ids,context=None):
        self.write(cr, uid, ids,{'state':'loaded'})
        self.load_collaborators(cr, uid, ids, context)
    
    def send_notifications(self,cr,uid,ids,context=None):
        collaborator_obj = self.pool.get('kemas.collaborator')
        wizard_line_obj = self.pool.get('kemas.collaborator.send.notifications.line.wizard')
        #---------------------------------------------------------------------------------------------------------
        line_ids = self.read(cr, uid, ids[0],['line_ids'])['line_ids']
        if len(line_ids)==0:
            raise osv.except_osv(_('Error!'), _('No staff to send notifications.'))
        collaborator_obj.send_join_notification(cr, uid)
        mensaje = _('Sending mails notification has begun..')
        return{            
            'context': "{'message':'"+mensaje+"'}",
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'kemas.message.wizard', 
            'type': 'ir.actions.act_window', 
            'target':'new',
            }

    def _send_notifications(self,db_name, uid, ids):
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        #---------------------------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        collaborator_obj = self.pool.get('kemas.collaborator')
        wizard_line_obj = self.pool.get('kemas.collaborator.send.notifications.line.wizard')
        #---------------------------------------------------------------------------------------------------------
        line_ids = self.read(cr, uid, ids[0],['line_ids'])['line_ids']
        lines = wizard_line_obj.read(cr, uid, line_ids,['collaborator_id'])
        for line in lines:
            if config_obj.send_email_incoporation(cr, uid, line['collaborator_id'][0]):
                super(kemas.kemas.kemas_collaborator, collaborator_obj).write(cr,uid,[line['collaborator_id'][0]],{'notified':'notified'})
            else:
                super(kemas.kemas.kemas_collaborator, collaborator_obj).write(cr,uid,[line['collaborator_id'][0]],{'notified':'no_notified'})
        cr.commit()
        
    def load_collaborators(self,cr,uid,ids,context=None):
        wizard_line_obj = self.pool.get('kemas.collaborator.send.notifications.line.wizard')
        #----------------------------------------------------------------------------------------------------------
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator_ids = collaborator_obj.search(cr,uid,[('type','=','Collaborator'),('state','=','Active'),('notified','=','no_notified')])
        #Eliminar las lineas que ya se hayan agregado--------------------------------------------------------------
        lines = self.read(cr, uid, ids[0],['line_ids'])['line_ids']
        wizard_line_obj.unlink(cr, uid, lines)
        #----------------------------------------------------------------------------------------------------------
        for collaborator_id in collaborator_ids:
            sql = '''SELECT create_date 
                     FROM kemas_collaborator 
                     WHERE id = %d
                  '''%collaborator_id
            cr.execute(sql)
            result_query = cr.fetchall()
            cr.commit()
            wizard_line_obj.create(cr, uid, {
                  'wizard_id': ids[0],
                  'date_create':result_query[0][0],
                  'collaborator_id': collaborator_id,
                 })
            
    _name='kemas.collaborator.send.notifications.wizard'
    _columns={
        'line_ids': fields.one2many('kemas.collaborator.send.notifications.line.wizard', 'wizard_id', 'Collaborators'),
        'state': fields.selection([
            ('loading','Loading'),
            ('loaded','Loaded'),
            ],    'State'),
        }
    _defaults = {  
        'state': 'loading'
        }

class kemas_collaborator_send_notifications_line_wizard(osv.osv_memory):
    _name='kemas.collaborator.send.notifications.line.wizard'
    _columns={
        'wizard_id': fields.many2one('kemas.collaborator.send.notifications.wizard','wizard_id',ondelete='cascade', required=True),
        'date_create': fields.datetime('Date create', help='Date the record was created from this Collaborator.'),
        'collaborator_id': fields.many2one('kemas.collaborator','Collaborator',ondelete='cascade', help='Contributor to which to send the notification mail.'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

