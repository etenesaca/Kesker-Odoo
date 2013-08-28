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
    collabortors_list = []
    
    def __init__(self, cr, uid, name, context):       
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({             
            'time_d': self._get_time,
            'config':self.get_config,
            'build_report':self.buid_report,
            'collaborators':self.collaborators,
        })
    
    def _get_time(self):
        return tools.ustr(time.strftime('%A %d de %B de %Y'))
    
    def get_collaborator_birth(self, collaborator_id):
        cr = self.cr
        uid = self.uid
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['birth'])
        res = kemas_extras.convert_date_to_dmy(collaborator['birth'])
        return res
    
    def collaborators(self):
        return self.collabortors_list
        
    def buid_report(self, wizard):
        cr = self.cr
        uid = self.uid
        collaborator_obj = self.pool.get('kemas.collaborator')
        team_obj = self.pool.get('kemas.team')
        collaborator_ids = team_obj.read(cr, uid, wizard.id, ['collaborator_ids'])['collaborator_ids']
        collaborators = collaborator_obj.read(cr, uid, collaborator_ids, ['name'])
        count = 0
        res = []
        for collaborator in collaborators:
            count += 1
            num = kemas_extras.completar_cadena(str(count),len(str(len(collaborator_ids))))
            collaborator_item = {
                                 'num' : count,
                                 'name': collaborator['name']
                                 }
            res.append(collaborator_item)
        self.collabortors_list = res
        return None
            
    def get_config(self):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(self.cr, self.uid)
        if config_id:
            return config_obj.browse(self.cr, self.uid, config_id)
        else:
            raise osv.except_osv(_('Error!'), _('No settings available. Please create a setting.'))