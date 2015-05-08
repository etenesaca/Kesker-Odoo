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

from openerp.addons.kemas import kemas_extras as extras
from openerp.osv import osv


class res_partner(osv.osv):
    def name_search(self, cr, uid, name, args=[], operator='ilike', context={}, limit=100):
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        res_ids = super(res_partner, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        if context.get('no_relation_with_collaborator'):
            res_tpl = res_ids and len(res_ids) == 1 and '(%d)' % res_ids[0] or res_ids and str(tuple(res_ids)) or '(0)'
            sql = """
                select partner_id from kemas_collaborator 
                where partner_id in %s
                """ % res_tpl
            cr.execute(sql)
            result_query = cr.fetchall()
            foo = extras.convert_result_query_to_list(result_query)
            res_ids = list(set(res_ids) - set(foo))
        return res_ids
    
    def create(self, cr, uid, vals, context={}):
        try:
            vals['image'] = extras.crop_image(vals['image'], 256)
        except:
            None
        vals['name'] = extras.elimina_tildes(vals['name'])
        return super(res_partner, self).create(cr, uid, vals, context)
    
    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('name'):
            vals['name'] = extras.elimina_tildes(vals['name'])
        
        if vals.get('image') and 1 not in ids:
            try:
                vals['image'] = extras.crop_image(vals['image'], 256)
            except:
                None
        return super(res_partner, self).write(cr, uid, ids, vals, context) 
    
    _inherit = 'res.partner'
    
    def _validate_partner_name(self, cr, uid, ids):
        """
        Esta funcion verifica: Que no se repitan los nombres de los los partners.
        @return: Si la validacion es correcta devuelve True caso contrario False y se revierte el proceso de Guardado.
        """
        def validate_name(record):
            name = extras.elimina_tildes(record['name'])
            search_args = [('name', 'ilike', name)]
            if record['parent_id']:
                # Si el parter se que quiere registra es un contacto verifico que no se creen dos contactos iguales de la misma empresa
                search_args.append(('parent_id', '=', record['parent_id'][0]))
            else:
                # Si le partner no es un contacto la busqueda para controlar repetidos solo se la hace entre partners que no son contacto
                search_args.append(('parent_id', '=', False))
            record_ids = self.search(cr, uid, search_args)
            if len(record_ids) > 1:
                # Si la búsqueda de partners repetidos nos da que hay mas de uno repetido revisamos que efectivamente coincidan
                # ya que por usar el ilike nos puede dar positivos Falsos como por ejemplo: buscamos 'loja' y nos encuenta 'José Lojano' 
                count = 0
                repetidos = self.read(cr, uid, record_ids, ['name'])
                for repetido in repetidos:
                    repetido_name = extras.elimina_tildes(repetido['name'])
                    if repetido_name and name.lower() == repetido_name.lower():
                        count += 1
                if count > 1:
                    return False
            return True
            
        records = self.read(cr, uid, ids, ['name', 'parent_id'])
        for record in records:
            if not validate_name(record):
                return False
        return True
    
    _constraints = [(_validate_partner_name, u'\n\n' + 'Ya hay una persona persona creada con este nombre..', [u'name']), ]
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
