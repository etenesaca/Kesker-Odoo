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
            'rows_data':self.rows,
            'rows_collaboration':self.rows_collaboration,
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
        
        attedance_obj = self.pool.get('kemas.attendance')
        history_points_obj = self.pool.get('kemas.history.points')
        connection_obj = self.pool.get('kemas.collaborator.logbook.login')
        collaborator_obj = self.pool.get('kemas.collaborator')
        
        args_attendance = []
        args_connections = []
        args_history_points = []
        
        if wizard.collaborator_ids:
            collaborator_ids = []
            for collaborator in wizard.collaborator_ids:
                collaborator_ids.append(collaborator.id)
        else:
            collaborator_ids = collaborator_obj.search(cr, uid, [('state', '=', 'Active'), ('type', '=', 'Collaborator')])
        
        args_attendance.append(('collaborator_id', 'in', collaborator_ids))
        args_connections.append(('collaborator_id', 'in', collaborator_ids))
        args_history_points.append(('collaborator_id', 'in', collaborator_ids))
            
        if wizard.service_id:
            args_attendance.append(('event_id.service_id', '=', wizard.service_id.id))
        
        if wizard.place_id:
            args_attendance.append(('event_id.service_id', '=', wizard.place_id.id))
        
        # RANGO DE CONSULTA
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        range_dates = {
                       'date_start' : kemas_extras.convert_to_UTC_tz(wizard.date_start + " 00:00:00", tz),
                       'date_stop' : kemas_extras.convert_to_UTC_tz(wizard.date_end + " 23:59:59", tz)
                       }
        # Para registros de asistencia
        args_attendance.append(('date', '>=', range_dates['date_start']))
        args_attendance.append(('date', '<=', range_dates['date_stop']))
        # Para registros de asistencia
        args_connections.append(('datetime', '>=', range_dates['date_start']))
        args_connections.append(('datetime', '<=', range_dates['date_stop']))
        # Para registros de asistencia
        args_history_points.append(('date', '>=', range_dates['date_start']))
        args_history_points.append(('date', '<=', range_dates['date_stop']))  
            
        # REGISTRO DE ASISTENCIA
        attendance_ids = attedance_obj.search(cr, uid, args_attendance)
        attendances = attedance_obj.read(cr, uid, attendance_ids, ['type', 'collaborator_id'])
        attendance_dict = {}
        for attendance in attendances:
            collaborator_id = attendance['collaborator_id'][0]
            if not attendance_dict.has_key(collaborator_id):
                attendance_dict[collaborator_id] = {'just_time' : 0, 'late' : 0, 'absence' : 0, 'colaboraciones' : 0}
            attendance_dict[collaborator_id][attendance['type']] += 1
            attendance_dict[collaborator_id]['colaboraciones'] += 1
        
        # CONEXIONES
        connection_ids = connection_obj.search(cr, uid, args_connections)
        connections = connection_obj.read(cr, uid, connection_ids, ['collaborator_id'])
        connection_dict = {}
        for connection in connections:
            if not connection_dict.has_key(connection['collaborator_id'][0]):
                connection_dict[connection['collaborator_id'][0]] = 0
            connection_dict[connection['collaborator_id'][0]] += 1
        
        # HISTORIAL DE PUNTOS
        history_points_ids = history_points_obj.search(cr, uid, args_history_points)
        history_points = history_points_obj.read(cr, uid, history_points_ids, ['type', 'points', 'collaborator_id'])
        history_points_dict = {}
        for history_point in history_points:
            collaborator_id = history_point['collaborator_id'][0]
            if not history_points_dict.has_key(collaborator_id):
                history_points_dict[collaborator_id] = {'p_perdidos' : 0, 'p_ganados' : 0}
            if history_point['type'] == 'decrease':
                history_points_dict[collaborator_id]['p_perdidos'] += abs(history_point['points'])
            elif history_point['type'] == 'increase':
                history_points_dict[collaborator_id]['p_ganados'] += abs(history_point['points'])
        
        # Listado de Colaboradores por colaboración
        collaboration_list = {}
        
        # Armar el dicionarios de los datos
        collaborator_dict = {}
        collaborators = collaborator_obj.read(cr, uid, collaborator_ids, ['name_with_nick_name'])
        for collaborator in collaborators:
            collaborator['connections'] = connection_dict.get(collaborator['id'], 0)
            collaborator['attendances'] = attendance_dict.get(collaborator['id'], {'just_time' : 0, 'late' : 0, 'absence' : 0, 'colaboraciones' : 0})
            collaborator['history_points'] = history_points_dict.get(collaborator['id'], {'p_perdidos' : 0, 'p_ganados' : 0})
            collaborator_dict[(collaborator['history_points']['p_ganados'], collaborator['id'])] = collaborator
            collaboration_list[(collaborator['attendances']['colaboraciones'], collaborator['id'])] = collaborator

        # Ordenas los diccionario
        collaborator_dict = sorted(collaborator_dict.items(), key=lambda x:x[0], reverse=True)
        
        global datas
        datas = []
        count = 0
        for item in collaborator_dict:
            count += 1
            num = kemas_extras.completar_cadena(str(count), len(str(len(collaborator_dict))))
            collaborator = item[1]
            attendances = collaborator['attendances']
            history_points = collaborator['history_points']
            
            if attendances['colaboraciones'] > 0:
                porcentual_just_time = float(float((attendances['just_time'] * 100)) / attendances['colaboraciones'])
                porcentual_just_time = str(kemas_extras.round_value(porcentual_just_time, 1)) + '%'
                porcentual_late = float(float((attendances['late'] * 100)) / attendances['colaboraciones'])
                porcentual_late = str(kemas_extras.round_value(porcentual_late, 1)) + '%'
                porcentual_absence = float(float((attendances['absence'] * 100)) / attendances['colaboraciones'])
                porcentual_absence = str(kemas_extras.round_value(porcentual_absence, 1)) + '%'
            else:
                attendances['just_time'] = '---'
                porcentual_just_time = "---"
                attendances['late'] = '---'
                porcentual_late = "---"
                attendances['absence'] = '---'
                porcentual_absence = "---"
                attendances['colaboraciones'] = "---" 
            
            row = {
                   'num' : num,
                   'name' : collaborator['name_with_nick_name'],
                   # 'photo' : item[1]['collaborator']['photo_small'],
                   'just_time' : attendances['just_time'],
                   'porcentual_just_time' : porcentual_just_time,
                   'late' : attendances['late'],
                   'porcentual_late' : porcentual_late,
                   'absence' : attendances['absence'],
                   'porcentual_absence' : porcentual_absence,
                   'colaboraciones' :attendances['colaboraciones'],
                   'puntos_perdidos' : history_points['p_perdidos'],
                   'puntos_ganados' : history_points['p_ganados'],
                   'puntos' : history_points['p_ganados'] - history_points['p_perdidos'],
                   'conexiones' : collaborator['connections']
                   }
            datas.append(row)
        
        # Ordenas los diccionario
        collaboration_list = sorted(collaboration_list.items(), key=lambda x:x[0], reverse=True)
        
        global datas_collaboration
        datas_collaboration = []
        count = 0
        for item in collaboration_list:
            count += 1
            num = kemas_extras.completar_cadena(str(count), len(str(len(collaborator_dict))))
            collaborator = item[1]
            attendances = collaborator['attendances']
            
            row = {
                   'num' : num,
                   'name' : collaborator['name_with_nick_name'],
                   'just_time' : attendances['just_time'],
                   'late' : attendances['late'],
                   'absence' : attendances['absence'],
                   'colaboraciones' :attendances['colaboraciones'],
                   }
            datas_collaboration.append(row)
            
        return None

    def rows(self):      
        global datas
        return datas
    
    def rows_collaboration(self):      
        global datas_collaboration
        return datas_collaboration

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
