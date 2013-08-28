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
import datetime
from datetime import datetime
import time
from kemas import kemas_extras

class kemas_suspend_collaborator_step1_wizard(osv.osv_memory):
    def do_next(self, cr, uid, ids, context={}):
        wizard = self.read(cr, uid, ids[0])
        if wizard['collaborator_ids'] == []:
            raise osv.except_osv(_('Error!'), _('First select the collaborators.'))
        dict_header={}    
        dict_header['collaborator_ids'] = wizard['collaborator_ids']        
        
        context={'dict_header':dict_header}
        wizard_title = self.pool.get('kemas.func').get_translate(cr, uid, _('Suspend Collaborators'))[0]
        return {                                  
            'context':context,
            'name' : wizard_title,
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'kemas.suspend_collaborator.step2.wizard', 
            'type': 'ir.actions.act_window',
            'target':'new',
            }
        
    _name='kemas.suspend_collaborator.step1.wizard'
    _columns={
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_suspend_collaborator_collaborator_rel',  'collaborator_id',  'suspend_collaborator_id', 'collaborators',help=''),
        'state':fields.selection([
            ('step1','Step 1'),
            ('step2','Step 2'),
        ],    'State', select=True, readonly=True),
        }

    _defaults = {  
        'state':'step1'
        }

class kemas_suspend_collaborator_step2_wizard(osv.osv_memory):
    def get_end_date(self, cr, uid, ids, days, day1, day2, day3, day4, day5, day6, day7, context={}):
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        now = datetime.strptime(kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"),tz), '%Y-%m-%d %H:%M:%S')
        date_today = "%s-%s-%s"%(kemas_extras.completar_cadena(now.year,4),kemas_extras.completar_cadena(now.month),kemas_extras.completar_cadena(now.day))
        
        days_str = {
                    'LUN':True,
                    'MAR':True,
                    'MIE':True,
                    'JUE':True,
                    'VIE':True,
                    'SAB':True,
                    'DOM':True
                    }
        if day1: 
            days_str['LUN'] = True
        else:
            days_str['LUN'] = False
        
        if day2: 
            days_str['MAR'] = True
        else:
            days_str['MAR'] = False
            
        if day3: 
            days_str['MIE'] = True
        else:
            days_str['MIE'] = False
            
        if day4: 
            days_str['JUE'] = True
        else:
            days_str['JUE'] = False
            
        if day5: 
            days_str['VIE'] = True
        else:
            days_str['VIE'] = False
            
        if day6: 
            days_str['SAB'] = True
        else:
            days_str['SAB'] = False
            
        if day7: 
            days_str['DOM'] = True
        else:
            days_str['DOM'] = False
        
        workdays = []
        if days_str['LUN']:workdays.append('LUN')
        if days_str['MAR']:workdays.append('MAR')
        if days_str['MIE']:workdays.append('MIE')
        if days_str['JUE']:workdays.append('JUE')
        if days_str['VIE']:workdays.append('VIE')
        if days_str['SAB']:workdays.append('SAB')
        if days_str['DOM']:workdays.append('DOM')
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        return kemas_extras.get_end_date(date_today, int(days), tz, workdays = tuple(workdays))
        
    def on_change_days(self, cr, uid, ids, days, day1, day2, day3, day4, day5, day6, day7, context={}):
        values = {}
        values['date_end'] = self.get_end_date(cr, uid, ids, days, day1, day2, day3, day4, day5, day6, day7, context)
        return {'value':values}
    
    def validate_points_zero(self,cr,uid,ids):
        wizard = self.read(cr, uid, ids[0],[])
        if wizard['new_points']<=0 and wizard['remove_points']:
            raise osv.except_osv(_('Error!'), _('The points must be greater than zero.'))
        return True
        
    def save(self,cr,uid,ids,context=None):
        wizard = self.read(cr, uid, ids[0],[])
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator_ids = eval(wizard['collaborator_ids'])
        
        days = wizard['days']
        day1 = wizard['day1']
        day2 = wizard['day2']
        day3 = wizard['day3']
        day4 = wizard['day4']
        day5 = wizard['day5']
        day6 = wizard['day6']
        day7 = wizard['day7']
        end_date = self.get_end_date(cr, uid, ids, days, day1, day2, day3, day4, day5, day6, day7, context)
        collaborator_obj.suspend(cr, uid, collaborator_ids, end_date, unicode(wizard['description']))
        if wizard['remove_points']:
            collaborator_obj.add_remove_points(cr, uid, collaborator_ids, int(wizard['new_points']), unicode(u'Suspención: ' + wizard['description']), 'decrease')
        mensaje = _('The registers was saved correctly.')
        return{            
            'context': "{'message':'"+mensaje+"'}",
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'kemas.message.wizard', 
            'type': 'ir.actions.act_window', 
            'target':'new',
            }
        
    def fields_get(self, cr, uid, fields=None, context={}, write_access=True):   
        result = super(kemas_suspend_collaborator_step2_wizard, self).fields_get(cr, uid,fields, context, write_access)
        if context == {}:return result
        dict_def={}
        dict_def.update(context['dict_header'])
        dict_def['collaborator_ids'] = dict_def['collaborator_ids']
        dict_def['day1']=True
        dict_def['day2']=True
        dict_def['day3']=True
        dict_def['day4']=True
        dict_def['day5']=True
        dict_def['day6']=True
        dict_def['day7']=True
        dict_def['days']=30
        dict_def['state']='step2'
        self._defaults=dict_def
        return result
    
    _name='kemas.suspend_collaborator.step2.wizard'
    _columns={
        'logo': fields.binary('img'),
        'collaborator_ids': fields.text('Collaborators'),
        'day1':fields.boolean('Monday', required=False),
        'day2':fields.boolean('Tuesday', required=False),
        'day3':fields.boolean('Wednesday', required=False),
        'day4':fields.boolean('Thursday', required=False),
        'day5':fields.boolean('Friday', required=False),
        'day6':fields.boolean('Saturday', required=False),
        'day7':fields.boolean('Sunday', required=False),
        'days' : fields.char('Days',size=255,required=True,help=""),
        'date_end':fields.datetime('Date end',help=""),
        'remove_points':fields.boolean('Also remove points?', required=False, help="Check the box if you want to also remove points to collaboratords"),
        'new_points' : fields.integer('Points to remove', required=False, help="Points you currently have a collaborator"),
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

