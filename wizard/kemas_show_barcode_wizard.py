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
from lxml import etree

class kemas_show_barcode_wizard(osv.osv_memory):
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=True, submenu=False):       
        res = {}
        xml='''
        <form string="Codigo de Barras" version="7.0">
            <field name="barcode_file_name" invisible="1"/>
            <div align="center">
                <field name="barcode" widget="image" readonly="1" class="without_border"/>
                <br/><br/>
                <field name="barcode_download" readonly="1" filename="barcode_file_name"/>
            </div>
            <footer>
                <button string="Cerrar" class="oe_link" special="cancel"/>
            </footer>
        </form>
        '''
        doc = etree.fromstring(xml.encode('utf8'))
        xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
        res['arch'] = xarch
        res['fields'] = xfields
        return res
    
    def fields_get(self, cr, uid, fields={}, context={}, write_access=True): 
        result = super(kemas_show_barcode_wizard, self).fields_get(cr, uid,fields, context, write_access)
        if not context is None and type(context).__name__=='dict' and context.get('active_ids',False):
            def_dic = {}
            barcode = self.pool.get('kemas.collaborator').read(cr,uid,context['active_ids'][0],['bar_code'])['bar_code']
            def_dic['barcode'] = barcode
            def_dic['barcode_download'] = barcode
            def_dic['barcode_file_name'] = 'barcode.jpg'
            self._defaults = def_dic
        return result
    
    _name='kemas.show.barcode.wizard'
    _columns={
        'barcode': fields.binary('Codigo de Barras'),
        'barcode_download': fields.binary('Codigo de Barras'),
        'barcode_file_name': fields.char('Nombre del archivo',size=255),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: