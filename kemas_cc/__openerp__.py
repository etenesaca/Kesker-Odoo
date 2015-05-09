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
    'name': u'Kesker - Centro Cristiano',
    'description': """
    Este modulo contiene todas las personalizacion que se han hecho especificamente para el Centro Cristiano de Cuenca
    """,
    'version':'1.0',
    'author': 'EdgarSoft',
    'website': '',
    'depends': [
        'kemas',
    ],
    'category':'Accounting & Finance',
    'init_xml': [],
    'data': [
        'security/ir.model.access.csv',
        'kemas_cc_view.xml',
        # Objetos de bajo nivel para poder exportarlos
        #'low_level_objects.xml',
        ],
    'installable': True,
    'application': True,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

