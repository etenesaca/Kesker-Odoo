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
from openerp.addons.kemas import kemas_extras

class kemas_report_attendance_statistics_wizard(osv.osv_memory):
    def create(self, cr, uid, vals, context={}):
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        if vals['date_type'] == 'today':
            range_dates = kemas_extras.get_dates_range_today(tz)
        elif vals['date_type'] == 'this_week':
            range_dates = kemas_extras.get_dates_range_this_week(tz)
        elif vals['date_type'] == 'this_month':
            range_dates = kemas_extras.get_dates_range_this_month(tz)
        else:
            range_dates = {
                           'date_start' : vals['date_start'] + " 00:00:00",
                           'date_stop' : vals['date_end'] + " 23:59:59",
                           }
        vals['date_start'] = kemas_extras.convert_to_tz(range_dates['date_start'], tz)
        vals['date_end'] = kemas_extras.convert_to_tz(range_dates['date_stop'], tz)
        return super(osv.osv_memory, self).create(cr, uid, vals, context)
    
    def call_report(self, cr, uid, ids, context=None):
        datas = {}     
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [])[0]
        datas = {
            'ids': ids,
            'model': 'ir.ui.menu',
            'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'attendance_statistics_report',
            'datas': datas,
            }

    _name = 'kemas.attendance.statistics.wizard'
    _columns = {
        'date_type': fields.selection([
            ('today', 'Hoy'),
            ('this_week', 'Esta semana'),
            ('this_month', 'Este mes'),
            ('other', 'Entre fechas'),
             ], 'Fecha', required=True),
        'date_start': fields.date('Desde'),
        'date_end': fields.date('Hasta'),
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_report_attendance_statistics_wizard_collaborator_rel', 'report_attendance_statistics_wizard_id', 'collaborator_id', 'Colaboradores', help='Collaboradores de los Cuales se va obtener el reporte'),
        'place_id': fields.many2one('kemas.place', 'Lugar', ondelete='cascade', help=''),
        'service_id': fields.many2one('kemas.service', 'Servicio', ondelete='cascade', help=''),
        'detailed': fields.boolean('Reporte detallado?', required=False),
        }
    
    _defaults = {  
        'date_type': 'this_month',
        }
    
    def validate_dates(self, cr, uid, ids):
        wizard = self.read(cr, uid, ids[0], ['date_start', 'date_end'])
        if wizard['date_start'] > wizard['date_end']:
            raise osv.except_osv(u'¡Operación no válida!', _('The date from which to search for events can not be higher than the deadline.'))
        else:
            return True
            
    _constraints = [
        (validate_dates, 'The date from which to search for events can not be higher than the deadline.', ['date_start'])
        ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

