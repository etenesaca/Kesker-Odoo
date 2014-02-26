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

from osv import fields, osv
from tools.translate import _
import addons

class kemas_report_collaborators_list_wizard(osv.osv_memory):
    def on_change_type_collaborators(self, cr, uid, ids, type_collaborators, context={}):
        values={}
        if type_collaborators == 'other' or type_collaborators == 'collaborators':
            values['fl_level'] = False
            values['fl_points'] = False
            values['fl_state'] = False
            values['fl_join_date'] = False
            values['fl_age_in_ministry'] = False
        return {'value':values}
    
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
            'report_name': 'collaborator_list_report',
            'datas': datas,
            }

    _name='kemas.report.collaborators.list.wizard'
    _columns={
        'logo': fields.binary('img'),
        'team_id': fields.many2one('kemas.team','Team',ondelete='cascade'),
        'type_collaborators': fields.selection([
          ('all','All'),
          ('collaborators','Collaborators'),
          ('others','Others'),
         ],    'Type of persons', select=True, readonly=False, required=True),
        'type_collaborators_to_select': fields.selection([
          ('all','All'),
          ('actives','Active'),
          ('inactives','Inactive'),
          ('lockeds','Locked'),
         ],    'State', select=True, readonly=False),
        'name': fields.char('Name',size=64),
        'fl_code': fields.boolean('Code'),
        'fl_name': fields.boolean('Name', readonly=True),
        'fl_mobile': fields.boolean('Mobile'),
        'fl_telef1': fields.boolean('Telephone 1'),
        'fl_telef2': fields.boolean('telephone 2'),
        'fl_birth': fields.boolean('Birth'),
        'fl_age': fields.boolean('Age'),
        'fl_email': fields.boolean('Email'),
        'fl_address': fields.boolean('Address'),
        'fl_state': fields.boolean('State'),
        'fl_team': fields.boolean('Team'),
        'fl_level': fields.boolean('Level'),
        'fl_points': fields.boolean('Points'),
        'fl_join_date': fields.boolean('Join Date in ministry'),
        'fl_age_in_ministry': fields.boolean('Age in Ministry')
        }
    
    def _get_logo(self, cr, uid, context=None):
        photo_path = addons.get_module_resource('kemas','images','report.png')
        return open(photo_path, 'rb').read().encode('base64')
    _defaults = {  
        'logo': _get_logo,
        'fl_name': True,
        'type_collaborators': 'collaborators',
        'type_collaborators_to_select': 'actives'
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

