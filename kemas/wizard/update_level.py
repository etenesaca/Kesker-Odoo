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


class kemas_collaborator_update_level_wizard(osv.osv_memory):
    def process(self, cr, uid, ids, context=None):
        self.pool.get('kemas.collaborator')._update_collaborators_level(cr.dbname , uid)
        return {}
    _name = 'kemas.collaborator.update.level.wizard'
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

