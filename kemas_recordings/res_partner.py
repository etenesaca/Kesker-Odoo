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

from openerp.osv import osv


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        res = super(res_partner, self).default_get(cr, uid, fields, context=context)
        if context.has_key('is_expositor'):
            cat_id = self.pool['kemas.func'].get_id_by_ext_id(cr, uid, 'res_partner_category_expositor')
            res.update({'category_id': [(6, 0, [cat_id])]})
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
