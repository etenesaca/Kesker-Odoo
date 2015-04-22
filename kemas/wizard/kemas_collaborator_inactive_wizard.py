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


class kemas_collaborator_inactives_wizard(osv.osv_memory):
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False, submenu=False):
        result = {}
        ok_str = u'Aceptar'
        or_str = u' ó '
        buttons = """
        <button string="%s" name="save" type="object" class="oe_highlight"/>
        %s
        <button string="%s" class="oe_link" special="cancel"/>
        """ % (ok_str, or_str, _('Cancelar'))
        if len(context['active_ids']) > 1:
            m1 = self.pool.get('kemas.func').get_translate(cr, uid, _('Are you sure to Inactivate these'))[0]
            m2 = self.pool.get('kemas.func').get_translate(cr, uid, _('Collaborators'))[0]
            message = u"¿%s %d %s?" % (m1, len(context['active_ids']), m2)
        else:
            collaborator_obj = self.pool.get('kemas.collaborator')
            if collaborator_obj.read(cr, uid, context['active_id'], ['state'])['state'] == 'Inactive':
                message = self.pool.get('kemas.func').get_translate(cr, uid, _('This Collaborator already in Inactive state!'))[0]
                buttons = """
                <button string="%s" class="oe_link" special="cancel"/>
                """ % (ok_str)
            else:
                message = self.pool.get('kemas.func').get_translate(cr, uid, _('Are you sure to Inactivate this Collaborator?'))[0] 
        xml = """
                <form string="" version="7.0">
                    <div align="center">
                        <b><label string="%s"/></b>
                    </div>
                    <footer>
                       %s
                    </footer>
                </form>
                """ % (message, buttons)
        result['fields'] = self.fields_get(cr, uid, None, context)
        result['arch'] = xml
        return result
    
    def save(self, cr, uid, ids, context={}):
        self.pool.get('kemas.collaborator').do_inactivate(cr, uid, context['active_ids'], context)
        return {}

    _name = 'kemas.collaborator.inactive.wizard'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', ondelete='cascade', help='Collaborator name, which you want to activate.'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

