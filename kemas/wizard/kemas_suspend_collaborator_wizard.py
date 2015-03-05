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


class kemas_suspend_collaborator_step1_wizard(osv.osv_memory):
    def do_next(self, cr, uid, ids, context={}):
        wizard = self.read(cr, uid, ids[0])
        if wizard['collaborator_ids'] == []:
            raise osv.except_osv(u'¡Operación no válida!', 'Primeero seleccione los colaboradores a suspender')
        
        step_obj = self.pool['kemas.suspend_collaborator.step2.wizard']
        vals = {
                'collaborator_ids': [(6, 0, wizard['collaborator_ids'])],
                'state': 'step2',
                'day1': True,
                'day2': True,
                'day3': True,
                'day4': True,
                'day5': True,
                'day6': True,
                'day7': True,
                }
        res_id = step_obj.create(cr, uid, vals)
        return {                                  
            'context': context,
            'res_id': res_id,
            'name' : 'Suspender Colaboradores',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': step_obj._name,
            'type': 'ir.actions.act_window',
            'target':'new',
            }
        
    _name = 'kemas.suspend_collaborator.step1.wizard'
    _columns = {
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_suspend_collaborator_collaborator_rel', 'collaborator_id', 'suspend_collaborator_id', 'collaborators', help=''),
        'state': fields.selection([
            ('step1', 'Step 1'),
            ('step2', 'Step 2'),
        ], 'State', select=True, readonly=True),
        }

    _defaults = {  
        'state':'step1'
        }

class kemas_suspend_collaborator_step2_wizard(osv.osv_memory):
    def on_change_days(self, cr, uid, ids, days, day1, day2, day3, day4, day5, day6, day7, context={}):
        values = {}
        if days > 0:
            values['date_end'] = self.pool.get('kemas.suspension').get_end_date(cr, uid, days, day1, day2, day3, day4, day5, day6, day7, context)
        return {'value':values}
    
    def validate_points_zero(self, cr, uid, ids):
        wizard = self.read(cr, uid, ids[0], [])
        if wizard['new_points'] <= 0 and wizard['remove_points']:
            raise osv.except_osv(u'¡Operación no válida!', _('The points must be greater than zero.'))
        return True
        
    def save(self, cr, uid, ids, context=None):
        wizard = self.read(cr, uid, ids[0], [])
        if not wizard['days'] or wizard['days'] == 0:
            raise osv.except_osv(u'¡Operación no válida!', u"Primero ingrese el número de días de suspensión.") 
        
        collaborator_obj = self.pool.get('kemas.collaborator')
        suspension_obj = self.pool.get('kemas.suspension')
        
        collaborator_ids = wizard['collaborator_ids']
        
        days = wizard['days']
        day1 = wizard['day1']
        day2 = wizard['day2']
        day3 = wizard['day3']
        day4 = wizard['day4']
        day5 = wizard['day5']
        day6 = wizard['day6']
        day7 = wizard['day7']
        end_date = suspension_obj.get_end_date(cr, uid, days, day1, day2, day3, day4, day5, day6, day7, context)
        collaborator_obj.suspend(cr, uid, collaborator_ids, end_date, unicode(wizard['description']))
        if wizard['remove_points']:
            collaborator_obj.add_remove_points(cr, uid, collaborator_ids, int(wizard['new_points']), unicode(u'Suspención: ' + wizard['description']), 'decrease')
        mensaje = _('The registers was saved correctly.')
        return{            
            'context': "{'message':'" + mensaje + "'}",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kemas.message.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
            }
        
    _name = 'kemas.suspend_collaborator.step2.wizard'
    _columns = {
        'logo': fields.binary('img'),
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_suspend_collaborator_step2_collaborator_rel', 'wizard_id', 'collaborator_id', 'Colaboradores'),
        'day1': fields.boolean('Monday', required=False),
        'day2': fields.boolean('Tuesday', required=False),
        'day3': fields.boolean('Wednesday', required=False),
        'day4': fields.boolean('Thursday', required=False),
        'day5': fields.boolean('Friday', required=False),
        'day6': fields.boolean('Saturday', required=False),
        'day7': fields.boolean('Sunday', required=False),
        'days': fields.integer(u'Días'),
        'date_end': fields.datetime('Date end', help=""),
        'remove_points': fields.boolean('Also remove points?', required=False, help="Check the box if you want to also remove points to collaboratords"),
        'new_points': fields.integer('Points to remove', required=False, help="Points you currently have a collaborator"),
        'description': fields.text('Description', required=False),
        'state': fields.selection([
            ('step1', 'Step 1'),
            ('step2', 'Step 2'),
        ], 'State', select=True, readonly=True),
        'by_days':fields.boolean('Por días', required=False, help="Permite indicar que días de la semana se va suspende a los colaboradores"),
        }
    _constraints = [
        (validate_points_zero, 'The points must be greater than zero.', ['new_points']),
        ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

