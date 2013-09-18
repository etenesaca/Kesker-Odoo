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

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):       
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({             
            'time_d': self._get_time,
            'config':self.get_config,
            'state':self.get_state,
            'telef1':self.get_telef1,
            'telef2':self.get_telef2,
            'mobile':self.get_mobile,
            'team':self.get_team,
            'birth':self.get_collaborator_birth,
            'age':self.get_collaborator_age,
            'join_date':self.get_collaborator_join_date,
            'areas':self.get_collaborator_areas,
        })
    
    def _get_time(self):
        import datetime
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        tz = self.pool.get('kemas.func').get_tz_by_uid(self.cr, self.uid)
        now = kemas_extras.convert_to_tz(now,tz)
        now = datetime.datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
        return tools.ustr(now.strftime('%A %d de %B de %Y'))
    
    def get_collaborator_birth(self, collaborator_id):
        cr = self.cr
        uid = self.uid
        collaborator = self.pool.get('kemas.collaborator').read(cr, uid, collaborator_id, ['birth'])
        res = kemas_extras.convert_date_to_dmy(collaborator['birth'])
        return res
    
    def get_state(self, collaborator_id):
        collaborator = self.pool.get('kemas.collaborator').read(self.cr, self.uid, collaborator_id, ['state'])
        selection_dict = eval('dict(%s)'%[
            ('creating','Creando'),
            ('Inactive','Inactivo'),
            ('Locked','Bloqueado'),
            ('Active','Activo'),
            ('Suspended','Suspendido'),])
        state = selection_dict.get(collaborator['state'])
        return state
    
    def get_telef1(self, collaborator_id):
        res = self.pool.get('kemas.collaborator').read(self.cr, self.uid, collaborator_id, ['telef1'])['telef1']
        if not res or res == '':
            return ' ---'
        return res
    
    def get_telef2(self, collaborator_id):
        res = self.pool.get('kemas.collaborator').read(self.cr, self.uid, collaborator_id, ['telef2'])['telef2']
        if not res or res == '':
            return ' ---'
        return res
    
    def get_mobile(self, collaborator_id):
        res = self.pool.get('kemas.collaborator').read(self.cr, self.uid, collaborator_id, ['mobile'])['mobile']
        if not res or res == '':
            return ' ---'
        return res
    
    def get_team(self, collaborator_id):
        res = self.pool.get('kemas.collaborator').read(self.cr, self.uid, collaborator_id, ['team_id'])['team_id']
        if not res or res == '':
            return ' ---'
        return res[1]
    
    def get_collaborator_age(self, collaborator_id):
        cr = self.cr
        uid = self.uid
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['birth'])
        res = kemas_extras.calcular_edad(collaborator['birth'])
        return res
        
    def get_collaborator_join_date(self, collaborator_id):
        cr = self.cr
        uid = self.uid
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['join_date'])
        res = kemas_extras.convert_date_to_dmy(collaborator['join_date'])
        return res
    
    def get_collaborator_areas(self, collaborator_id):
        cr = self.cr
        uid = self.uid
        area_obj = self.pool.get('kemas.area')
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['area_ids'])
        areas = area_obj.read(cr, uid, collaborator['area_ids'],['name'])
        res = ''
        for area in areas:
            res += """* %s \n"""%(area['name'])
        
        if not res or res == '':
            return ' ---'
        return res
    
    def get_config(self):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(self.cr, self.uid)
        if config_id:
            return config_obj.browse(self.cr, self.uid, config_id)
        else:
            raise osv.except_osv(_('Error!'), _('No settings available. Please create a setting.'))