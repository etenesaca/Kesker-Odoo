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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import addons
#import kemas

class kemas_collaborator_assing_code_wizard(osv.osv_memory):
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
            m1 = self.pool.get('kemas.func').get_translate(cr,uid,_('Are you sure to assign a Code to these'))[0]
            m2 = self.pool.get('kemas.func').get_translate(cr,uid,_('Collaborators'))[0]
            message = "%s %d %s?"%(m1,len(context['active_ids']),m2)
        else:
            collaborator_obj = self.pool.get('kemas.collaborator')
            if collaborator_obj.read(cr,uid,context['active_id'],['code'])['code']:
                message = self.pool.get('kemas.func').get_translate(cr,uid,_('This Collaborator already has a Code assigned!'))[0]
                buttons = """
                <button string="%s" class="oe_link" special="cancel"/>
                """%(ok_str)
            else:
                message = self.pool.get('kemas.func').get_translate(cr,uid,_('Are you sure to assign a Code to this Collaborator?'))[0] 
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
        args = []
        args.append(('id','in',context['active_ids']))
        args.append(('state','in',['Active']))
        args.append(('code','=',False))
        collaborator_ids = collaborator_obj.search(cr, uid, args)
        seq_id = self.pool.get('ir.sequence').search(cr,uid,[('name','=','Kemas Collaborator'),])[0]
        for collaborator_id in collaborator_ids:
            vals = {
                    'code': str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
                    }
            super(addons.kemas.kemas.kemas_collaborator, collaborator_obj).write(cr,uid,[collaborator_id],vals)
        return {}

    _name='kemas.collaborator.assing.code.wizard'
    _columns={
        'collaborator_id': fields.many2one('kemas.collaborator','Collaborator',ondelete='cascade',help='Collaborator name, which you want to activate.'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

