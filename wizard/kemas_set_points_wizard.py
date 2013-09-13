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

class kemas_set_points_step1_wizard(osv.osv_memory):
    def do_next(self, cr, uid, ids, context={}):
        wizard = self.read(cr, uid, ids[0])
        if wizard['collaborator_ids'] == []:
            raise osv.except_osv(_('Error!'), _('First select the collaborators.'))
        dict_header={}    
        dict_header['type'] = wizard['type']
        dict_header['collaborator_ids'] = wizard['collaborator_ids']        
        
        context={'dict_header':dict_header}
        if wizard['type'] == 'increase':
            wizard_title = self.pool.get('kemas.func').get_translate(cr, uid, _('Increase Points'))[0]
        else:
            wizard_title = self.pool.get('kemas.func').get_translate(cr, uid, _('Decrease Points'))[0]
        return {                                  
            'context':context,
            'view_type': 'form',
            'name': wizard_title, 
            'view_mode': 'form', 
            'res_model': 'kemas.set.points.step2.wizard', 
            'type': 'ir.actions.act_window',
            'target':'new',
            }
        
    _name='kemas.set.points.step1.wizard'
    _columns={
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_set_points_collaborator_rel',  'collaborator_id',  'set_points_id', 'collaborators',help='Collaborators who are going to modify the points'),
        'type':fields.selection([('increase','Increase'),('decrease','Decrease')],'Type',required=True),
        'state':fields.selection([
            ('step1','Step 1'),
            ('step2','Step 2'),
        ],    'State', select=True, readonly=True),
        }
    _defaults={
        'type' : 'increase',
        'state':'step1'
        }

class kemas_set_points_step2_wizard(osv.osv_memory):
    def validate_points_zero(self,cr,uid,ids):
        level = self.read(cr, uid, ids[0],[])
        if level['new_points']<=0:
            raise osv.except_osv(_('Error!'), _('The points must be greater than zero.'))
        return True
    
    def save(self,cr,uid,ids,context=None):
        wizard = self.read(cr, uid, ids[0],[])
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator_ids = eval(wizard['collaborator_ids'])
        collaborator_obj.add_remove_points(cr, uid, collaborator_ids, int(wizard['new_points']), unicode(wizard['description']), unicode(wizard['type']))
        return True
        
    def fields_get(self, cr, uid, fields=None, context={}, write_access=True):   
        result = super(kemas_set_points_step2_wizard, self).fields_get(cr, uid,fields, context, write_access)
        if context is None or not context or type(context).__name__!="dict" or not context.has_key('dict_header'):
            return result
        
        dict_def={}
        dict_def.update(context['dict_header'])
        dict_def['type'] = dict_def['type']
        dict_def['state'] = 'step2'
        dict_def['collaborator_ids'] = dict_def['collaborator_ids']
        self._defaults = dict_def
        return result
    
    _name='kemas.set.points.step2.wizard'
    _columns={
        'collaborator_ids': fields.text('Collaborators'),
        'type':fields.selection([('increase','Increase'),('decrease','Decrease')],'Type'),
        'new_points' : fields.integer('Points', required=True, help=""),
        'description': fields.text('Description', required=True),
        'state':fields.selection([
            ('step1','Step 1'),
            ('step2','Step 2'),
        ],    'State', select=True, readonly=True),
        }

    _constraints=[
        (validate_points_zero,'The points must be greater than zero.',['new_points']),
        ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

