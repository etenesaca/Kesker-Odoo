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

from kemas import kemas_extras
import kemas
from openerp.tools.translate import _
from osv import osv
from report import report_sxw


headers = []
datas = []

class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):       
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({             
            'build_report':self.build_report,
            'config':self.get_config,
            'cols_title':self.cols,
            'rows_data':self.rows,
        })
    
    def get_config(self):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(self.cr, self.uid)
        if config_id:
            return config_obj.browse(self.cr, self.uid, config_id)
        else:
            raise osv.except_osv(u'¡Operación no válida!', _('No settings available. Please create a setting.'))

    def build_report(self, wizard):
        global headers
        global datas
        headers = []
        datas = []
        
        cr = self.cr
        uid = self.uid
        
        #---Cargar campos que se van a poner en el reporte
        fields = ['id']
        if wizard.fl_code: fields.append('code')
        if wizard.fl_name: fields.append('name')
        if wizard.fl_mobile: fields.append('mobile')
        if wizard.fl_phone: fields.append('phone')
        if wizard.fl_birth: fields.append('birth')
        if wizard.fl_age: fields.append('age')
        if wizard.fl_address: fields.append('address')
        if wizard.fl_email: fields.append('email')
        if wizard.fl_join_date: fields.append('join_date')
        if wizard.fl_age_in_ministry: fields.append('age_in_ministry')
        if wizard.fl_points: fields.append('points')
        if wizard.fl_team: fields.append('team_id')
        if wizard.fl_level: fields.append('level_id')
        if wizard.fl_state: fields.append('state')
        #-------------------------------------------------
        search_args = []
        if wizard.type_collaborators_to_select == 'actives':
            search_args.append(('state', '=', 'Active'))
        elif wizard.type_collaborators_to_select == 'inactives':
            search_args.append(('state', '=', 'Inactive'))
        elif wizard.type_collaborators_to_select == 'lockeds':
            search_args.append(('state', '=', 'Locked'))
        if wizard.team_id:
            search_args.append(('team_id', '=', 'wizard.team_id.id'))
        
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator_ids = collaborator_obj.search(cr, uid, search_args)
        collaborators = collaborator_obj.read(cr, uid, collaborator_ids, fields)
        
        global headers
        global datas
        
        count = 0
        for collaborator in collaborators:
            data = []
            count += 1
            data.append(kemas_extras.completar_cadena(str(count), len(str(len(collaborator_ids)))))
            for field in fields:
                if field == 'join_date':
                    data.append(kemas_extras.convert_date_to_dmy(collaborator[field]))
                elif field == 'birth':
                     data.append(kemas_extras.convert_date_to_dmy(collaborator[field]))
                elif field == 'team_id':
                    try:
                        data.append(collaborator[field][1])
                    except: 
                        data.append("")
                elif field == 'level_id':
                    try:
                        data.append(collaborator[field][1])
                    except: 
                        data.append("")
                elif field == 'state':
                    if collaborator[field] == "Active": 
                        data.append("Activo")
                    elif collaborator[field] == "Inactive":
                        data.append("Activo")
                    elif collaborator[field] == "Active":
                        data.append("Activo")
                elif field == 'age':
                    birth = collaborator_obj.read(cr, uid, collaborator['id'], ['birth'])['birth']
                    data.append(kemas_extras.calcular_edad(birth))
                else:
                    if field != 'id':
                        data.append(collaborator[field])
            datas.append(data)
        
        headers.append(u'#')
        for field in fields:
            if field == 'code': headers.append(u'CÓDIGO')
            if field == 'name': headers.append(u'NOMBRE')
            if field == 'mobile': headers.append(u'CELULAR')
            if field == 'phone': headers.append(u'TELÉFONO 1')
            if field == 'birth': headers.append(u'FECHA DE NAC')
            if field == 'age': headers.append(u'EDAD')
            if field == 'email': headers.append(u'CORREO ELECTRÓNICO')
            if field == 'address': headers.append(u'DIRECCIÓN')
            if field == 'join_date': headers.append(u'FECHA DE INGRESO AL MINISTERIO')
            if field == 'age_in_ministry': headers.append(u'EDAD EN EL MINISTERIO')
            if field == 'points': headers.append(u'PUNTOS')
            if field == 'team_id': headers.append(u'EQUIPO')
            if field == 'level_id': headers.append(u'NIVEL')
            if field == 'state': headers.append(u'ESTADO')
        return None

    def cols(self):
        global headers
        return headers

    def rows(self):      
        global datas
        return datas

