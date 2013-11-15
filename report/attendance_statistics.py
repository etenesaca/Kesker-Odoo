# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import re
from report import report_sxw
from osv import osv
from tools.translate import _
import time 
import tools
import kemas
from kemas import kemas_extras

from mx import DateTime
from datetime import datetime
from datetime import *
from dateutil import tz
import time

datas = []

class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):       
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({             
            'time_d': self._get_time,
            'build_report':self.build_report,
            'config':self.get_config,
            'cols_title':self.cols,
            'rows_data':self.rows,
        })
    
    def _get_time(self):
        import datetime
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        tz = self.pool.get('kemas.func').get_tz_by_uid(self.cr, self.uid)
        now = kemas_extras.convert_to_tz(now, tz)
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        return tools.ustr(now.strftime('%A %d de %B de %Y'))
    
    def get_config(self):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(self.cr, self.uid)
        if config_id:
            return config_obj.browse(self.cr, self.uid, config_id)
        else:
            raise osv.except_osv(_('Error!'), _('No settings available. Please create a setting.'))

    def build_report(self, wizard):
        cr = self.cr
        uid = self.uid
        
        # Buscar los registros de asistencia
        attedance_obj = self.pool.get('kemas.attendance')
        history_points_obj = self.pool.get('kemas.history.points')
        connection_obj = self.pool.get('kemas.collaborator.logbook.login')
        args = []
        args_connections = []
        
        if wizard.collaborator_id:
            args.append(('collaborator_id', '=', wizard.collaborator_id.id))
        if wizard.service_id:
            args.append(('event_id.service_id', '=', wizard.service_id.id))
        
        if wizard.place_id:
            args.append(('event_id.service_id', '=', wizard.place_id.id))
        
        if wizard.date_start:
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            date_start = kemas_extras.convert_to_UTC_tz(wizard.date_start + " 00:00:00", tz)
            date_end = kemas_extras.convert_to_UTC_tz(wizard.date_end + " 23:59:59", tz)
            args.append(('date', '>=', date_start))
            args.append(('date', '<=', date_end))
            
            args_connections.append(('datetime', '>=', date_start))
            args_connections.append(('datetime', '<=', date_end))
            
        attendance_ids = attedance_obj.search(cr, uid, args)
        attendance_dict = {}
        attendances = attedance_obj.read(cr, uid, attendance_ids, ['type', 'collaborator_id'])
        
        for attendance in attendances:
            collaborator_id = attendance['collaborator_id'][0]
            if not attendance_dict.has_key(collaborator_id):
                attendance_dict[collaborator_id] = {'just_time' : 0, 'late' : 0, 'absence' : 0, 'colaboraciones' : 0, 'p_perdidos' : 0, 'p_ganados' : 0}
            attendance_dict[collaborator_id][attendance['type']] += 1
            attendance_dict[collaborator_id]['colaboraciones'] += 1
            history_points_ids = history_points_obj.search(cr, uid, [('attendance_id', '=', attendance['id'])])
            if history_points_ids:
                history_point = history_points_obj.read(cr, uid, history_points_ids[0], ['type', 'points'])
                if history_point['type'] == 'decrease':
                    attendance_dict[collaborator_id]['p_perdidos'] += abs(history_point['points'])
                else:
                    attendance_dict[collaborator_id]['p_ganados'] += abs(history_point['points'])
        
        args_connections.append(('collaborator_id', 'in', attendance_dict.keys()))
        connection_ids = connection_obj.search(cr, uid, args_connections)
        connections = connection_obj.read(cr, uid, connection_ids, ['collaborator_id'])
        connection_dict = {}
        for connection in connections:
            if not connection_dict.has_key(connection['collaborator_id'][0]):
                connection_dict[connection['collaborator_id'][0]] = 0
            connection_dict[connection['collaborator_id'][0]] += 1
        
        collaborator_dict = {}
        collaborators = self.pool.get('kemas.collaborator').read(cr, uid, attendance_dict.keys(), ['name_with_nick_name', 'photo_small'])
        for collaborator in collaborators:
            collaborator['conexiones'] = connection_dict.get(collaborator['id'], 0)
            item = attendance_dict[collaborator['id']]
            item['collaborator'] = collaborator
            collaborator_dict[(item['p_ganados'], collaborator['id'])] = item
        
        collaborator_dict = sorted(collaborator_dict.items(), key=lambda x:x[0])
        global datas
        datas = []
        count = 0
        for item in collaborator_dict:
            count += 1
            num = kemas_extras.completar_cadena(str(count), len(str(len(collaborator_dict))))
            
            porcentual_just_time = float(float((item[1]['just_time'] * 100)) / item[1]['colaboraciones'])
            porcentual_just_time = str(kemas_extras.round_value(porcentual_just_time, 1)) + '%'
            porcentual_late = float(float((item[1]['late'] * 100)) / item[1]['colaboraciones'])
            porcentual_late = str(kemas_extras.round_value(porcentual_late, 1)) + '%'
            porcentual_absence = float(float((item[1]['absence'] * 100)) / item[1]['colaboraciones'])
            porcentual_absence = str(kemas_extras.round_value(porcentual_absence, 1)) + '%'
            row = {
                   'num' : num,
                   'name' : item[1]['collaborator']['name_with_nick_name'],
                   # 'photo' : item[1]['collaborator']['photo_small'],
                   'just_time' : item[1]['just_time'],
                   'porcentual_just_time' : porcentual_just_time,
                   'late' : item[1]['late'],
                   'porcentual_late' : porcentual_late,
                   'absence' : item[1]['absence'],
                   'porcentual_absence' : porcentual_absence,
                   'colaboraciones' : item[1]['colaboraciones'],
                   'puntos_perdidos' : item[1]['p_perdidos'],
                   'puntos_ganados' : item[1]['p_ganados'],
                   'puntos' : item[1]['p_ganados'] - item[1]['p_perdidos'],
                   'conexiones' : item[1]['collaborator']['conexiones']
                   }
            datas.append(row)
        return None

    def cols(self):
        global headers
        return headers

    def rows(self):      
        global datas
        return datas

