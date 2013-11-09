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
        now = kemas_extras.convert_to_tz(now,tz)
        now = datetime.datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
        return tools.ustr(now.strftime('%A %d de %B de %Y'))
    
    def get_config(self):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(self.cr, self.uid)
        if config_id:
            return config_obj.browse(self.cr, self.uid, config_id)
        else:
            raise osv.except_osv(_('Error!'), _('No settings available. Please create a setting.'))

    def build_report(self,wizard):
        cr = self.cr
        uid = self.uid
        
       
        event_obj = self.pool.get('kemas.event')
        args = []
        
        if wizard.collaborator_id:
            line_obj = self.pool.get('kemas.event.collaborator.line')
            line_ids = line_obj.search(cr, uid, [('collaborator_id','=',wizard.collaborator_id.id)])
            event_ids = event_obj.search(cr, uid, [('event_collaborator_line_ids','in',line_ids)])
            args.append(('id','in',event_ids))
            
        if wizard.service_id:
            args.append(('service_id','=',wizard.service_id.id))
        
        if wizard.place_id:
            args.append(('place_id','=',wizard.place_id.id))
        
        if wizard.state:
            if wizard.state != 'all':
                args.append(('state','=',wizard.state))
        
        if wizard.date_start:
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr,uid)
            date_start = kemas_extras.convert_to_UTC_tz(wizard.date_start + " 00:00:00",tz)
            date_end = kemas_extras.convert_to_UTC_tz(wizard.date_end + " 23:59:59",tz)
            args.append(('date_start', '>=', date_start))
            args.append(('date_start', '<=', date_end))
            
        event_ids = event_obj.search(cr, uid, args)
        fields = ['id','service_id','date_start','time_entry','time_start','time_end','place_id','state']
        events = event_obj.read(cr, uid, event_ids, fields)
        
        global datas
        datas = []
        count = 0
        for event in events:
            row = {}
            count += 1
            num = kemas_extras.completar_cadena(str(count),len(str(len(event_ids))))
            
            row['num'] = num
            row['service'] = event['service_id'][1]
            row['date'] = kemas_extras.convert_date_to_dmy(event['date_start'])
            row['time_entry'] = kemas_extras.convert_float_to_hour_format(event['time_entry'])
            row['time_start'] = kemas_extras.convert_float_to_hour_format(event['time_start'])
            row['time_end'] = kemas_extras.convert_float_to_hour_format(event['time_end'])
            row['place'] = event['place_id'][1]
            
            if event['state'] == 'draft':
                row['state'] = 'Borrador'
            elif event['state'] == 'on_going':
                row['state'] = 'En curso'
            elif event['state'] == 'closed':
                row['state'] = 'Cerrado'
            elif event['state'] == 'canceled':
                row['state'] = 'Cancelado'
            
            datas.append(row)
        return None

    def cols(self):
        global headers
        return headers

    def rows(self):      
        global datas
        return datas

