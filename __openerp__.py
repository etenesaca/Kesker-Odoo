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
{
    'name': 'Control de Asistencias, Tareas y Personal',
    'description': """Management Kemas Ministry that covers:
    Register Collaborators
    Recording Registry
    Calendar System
    Attendance record
    Repository.""",
    'version':'1.0',
    'author': 'Attempy Systems',
    'website': 'www.attempt.sys.com',
    'depends': [
        'base_setup',
        'board',
        'mail',
        'resource',
        'web_kanban',
    ],
    'category':'Accounting & Finance',
    'init_xml': [],
    'data': [
        'data/res.country.state.csv',
        'data/kemas_data.xml',
        'data/planned_actions.xml',
        'security/kemas_security.xml',
        'security/ir.model.access.csv',
        #'report/reports.xml',
        'kemas_view.xml',
        'controllers/kemas_sequence.xml',
        # 'kemas_installer.xml',
        'wizard/kemas_collaborator_send_notifications_wizard_view.xml',
        'wizard/kemas_set_points_wizard_view.xml',
        'wizard/kemas_set_points_work_wizard_view.xml',
        'wizard/kemas_send_notification_event_wizard_view.xml',
        'wizard/kemas_close_past_events_wizard_view.xml',
        'wizard/kemas_suspend_collaborator_wizard_view.xml',
        'wizard/kemas_event_replace_collaborator_wizard_view.xml',
        # Reportes
        'wizard/kemas_report_collaborators_list_wizard_view.xml',
        'wizard/kemas_report_events_list_wizard_view.xml',
        'wizard/kemas_report_attendance_statistics_wizard_view.xml',
        ],
    'installable': True,
    'application': True,
    'css': [],
    'js': ['static/src/js/kemas.js'],
    "css": [ 
            'static/src/css/project.css',
            'static/src/css/hr.css',
            'static/src/css/event.css',
            'static/src/css/ke.css',
            'static/src/css/event.css',
           ],
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

