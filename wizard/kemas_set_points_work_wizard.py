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
from lxml import etree
from tools.translate import _
import addons

class kemas_set_points_task_wizard(osv.osv_memory):
    def validate_collaborators(self,cr,uid,ids):
        wizard = self.read(cr, uid, ids[0],['collaborator_ids'])
        if wizard['collaborator_ids']==[]:
            raise osv.except_osv(_('Error!'), _('First you have to select collaborators!!'))
        return True
    
    def save(self,cr,uid,ids,context=None):
        wizard = self.read(cr, uid, ids[0],[])
        collaborator_obj = self.pool.get('kemas.collaborator')
        task_obj = self.pool.get('kemas.task')
        task = task_obj.read(cr,uid,wizard['task_id'][0],['points','description'])
        collaborator_obj.add_remove_points(cr, uid, wizard['collaborator_ids'], int(task['points']), unicode(task['description']), 'increase')
        return True
    
    _name='kemas.set.points.task.wizard'
    _columns={
        'task_id': fields.many2one('kemas.task','Task', required=True,ondelete='cascade', help='Task to be reclaiming the collaborators'),
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_add_points_task_collaborator_rel',  'collaborator_id',  'wizard_id', 'Collaborators'),
        }
    
    _constraints=[
        (validate_collaborators,'First you have to select collaborators!',['Collaborator_ids']),
        ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

