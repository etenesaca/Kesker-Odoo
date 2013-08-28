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

from osv import fields, osv
from tools.translate import _
import kemas
from kemas import kemas_extras
import time
import pooler
import threading

class kemas_collaborator_notify_incorporation_wizard(osv.osv_memory):
    def send_notification(self,cr, uid, collaborator_ids):
        if not self.pool.get('kemas.func').mailing(cr,uid):
            return False
        
        if len(collaborator_ids) == 1:
            collaborator_id = collaborator_ids[0]
            config_obj = self.pool.get('kemas.config')
            collaborator_obj = self.pool.get('kemas.collaborator')
            if config_obj.send_email_incoporation(cr, uid, collaborator_id):
                vals={'notified':'notified'}
                super(kemas.kemas.kemas_collaborator, collaborator_obj).write(cr,uid,[collaborator_id],vals)
            else:
                vals={'notified':'no_notified'}
                super(kemas.kemas.kemas_collaborator, collaborator_obj).write(cr,uid,[collaborator_id],vals)
        else:
            threaded_sending = threading.Thread(target=self._send_notification, args=(cr.dbname , uid, collaborator_ids))
            threaded_sending.start()
    
    def _send_notification(self,db_name, uid, collaborator_ids):
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        count = 0
        for collaborator_id in collaborator_ids:
            count += 1
            self.pool.get('kemas.collaborator').send_notification(cr, uid, collaborator_id, context={})
        print """\n
                 -------------------------------------------------------------------------------------------------------------------------
                 ***********************************************[%d] Join Notifications was sended****************************************
                 -------------------------------------------------------------------------------------------------------------------------\n"""%(count)
        cr.commit()
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False, submenu=False):
        result = {}
        ok_str = self.pool.get('kemas.func').get_translate(cr, uid, _('Ok'))[0]
        or_str = self.pool.get('kemas.func').get_translate(cr, uid, _('or'))[0]
        buttons = """
        <button string="%s" name="save" type="object" class="oe_highlight"/>
        %s
        <button string="%s" class="oe_link" special="cancel"/>
        """%(ok_str,or_str, _('Cancel'))
        if len(context['active_ids']) > 1:
            m1 = self.pool.get('kemas.func').get_translate(cr,uid,_('Are you sure to send notification of user Account Creation to these'))[0]
            m2 = self.pool.get('kemas.func').get_translate(cr,uid,_('Collaborators'))[0]
            message = "%s %d %s?"%(m1,len(context['active_ids']),m2)
        else:
            collaborator_obj = self.pool.get('kemas.collaborator')
            if not self.pool.get('kemas.func').mailing(cr,uid):
                message = self.pool.get('kemas.func').get_translate(cr,uid,_('The email notifications are disabled!'))[0]
                buttons = """
                <button string="%s" class="oe_link" special="cancel"/>
                """%(ok_str)
            elif not collaborator_obj.read(cr,uid,context['active_id'],['user_id'])['user_id']:
                message = self.pool.get('kemas.func').get_translate(cr,uid,_('This Collaborator no has a User Account assigned'))[0]
                buttons = """
                <button string="%s" class="oe_link" special="cancel"/>
                """%(ok_str)
            else:
                message = self.pool.get('kemas.func').get_translate(cr,uid,_('Are you sure to send notification of user Account Creation this Collaborator?'))[0] 
        xml = """
                <form string="" version="7.0">
                    <div align="center">
                        <b><label string="%s"/></b>
                    </div>
                    <footer>
                       %s
                    </footer>
                </form>
                """%(message,buttons)
        result['fields'] = self.fields_get(cr, uid, None, context)
        result['arch'] = xml
        return result
    
    def save(self,cr,uid,ids,context={}):        
        collaborator_obj = self.pool.get('kemas.collaborator')
        groups_obj=self.pool.get('res.groups')
        args = []
        args.append(('id','in',context['active_ids']))
        args.append(('state','in',['Active']))
        args.append(('type','in',['Collaborator']))
        args.append(('user_id','!=',False))
        collaborator_ids = collaborator_obj.search(cr, uid, args)
        self.send_notification(cr, uid, collaborator_ids)
        return {}

    _name='kemas.notify.incorporation.wizard'
    _columns={
        'collaborator_id':fields.many2one('kemas.collaborator','Collaborator',ondelete='cascade',help='Collaborator name, which you want to activate.'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

