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
import logging

from openerp.osv import fields, osv
from openerp import addons
from openerp.addons.kemas import kemas_extras


_logger = logging.getLogger(__name__)

class kemas_config(osv.osv):
    _inherit = 'kemas.config'
    def crop_photo(self, cr, uid, ids, context={}):
        result = super(kemas_config, self).crop_photo(cr, uid, ids, context)
        field_name = "logo"
        # Ministerios
        obj = self.pool.get('kemas.ministry')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
                
        # Cursos de Especializacion
        obj = self.pool.get('kemas.specialization.course')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
        return result

class kemas_collaborator(osv.osv):
    _inherit = 'kemas.collaborator' 
    _columns = {
        'vision': fields.text('Vision', help="The collaborator vision."),
        'mission': fields.text('Mission', help="The collaborator mission."),
        'ministry_ids': fields.many2many('kemas.ministry', 'kemas_ministry_collaborator_rel', 'collaborator_id', 'ministry_id', 'Ministerios'),
        'specialization_course_ids': fields.one2many('kemas.specialization.course.line', 'collaborator_id', 'Coursos de especializacion'),
    }

class kemas_ministry(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_ministry, self).write(cr, uid, ids, vals, context)
        for record_id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'ministry'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_ministry, self).write(cr, uid, [record_id], vals_write, context)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'ministry'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
        return super(kemas_ministry, self).create(cr, uid, vals, context)
    
    _order = 'name'
    _name = 'kemas.ministry'
    _columns = {
        'logo': fields.binary('Logo', help='Logo del Ministerio.'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'active': fields.boolean('Activo?', required=False),
        'name': fields.char('Nombre', size=64, required=True, help='Nombre del minsterio'),
        'description': fields.text('Description', help='Una descripcion breve'),
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_ministry_collaborator_rel', 'ministry_id', 'collaborator_id', 'Colaboradores'),
        }
    
    _sql_constraints = [
        ('uname', 'unique(name)', "Este Ministerio ya existe!"),
        ]
    
    def _get_logo(self, cr, uid, context={}):
        photo_path = addons.get_module_resource('kemas', 'images', 'ministry.png')
        return open(photo_path, 'rb').read().encode('base64')

    _defaults = {
        'logo': _get_logo,
        'active': True
    }
    
class kemas_specialization_course(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_specialization_course, self).write(cr, uid, ids, vals, context)
        for record_id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'specialization_course'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_specialization_course, self).write(cr, uid, [record_id], vals_write, context)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'specialization_course'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
        return super(kemas_specialization_course, self).create(cr, uid, vals, context)
    
    _order = 'name'
    _name = 'kemas.specialization.course'
    _columns = {
        'logo': fields.binary('Logo', help='Logo del Curso.'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'active': fields.boolean('Activo?', required=False),
        'name': fields.char('Name', size=64, required=True, help='Nombre del curso'),
        'description': fields.text('Description', help='Una descripcion breve'),
        'level_ids': fields.one2many('kemas.specialization.course.level', 'course_id', 'Niveles'),
        }
    _sql_constraints = [
        ('uname', 'unique(name)', "Este Curso ya existe!"),
        ]
    
    def _get_logo(self, cr, uid, context={}):
        photo_path = addons.get_module_resource('kemas', 'images', 'ministry.png')
        return open(photo_path, 'rb').read().encode('base64')

    _defaults = {
        'logo': _get_logo,
        'active': True
    }
    
class kemas_specialization_course_level(osv.osv):
    _order = 'name'
    _name = 'kemas.specialization.course.level'
    _columns = {
        'name': fields.char('Nombre', size=64, required=True, help='Nombre del Nivel'),
        'course_id': fields.many2one('kemas.specialization.course', 'Curso', required=True),
        'line_ids': fields.one2many('kemas.specialization.course.line', 'course_id', 'Colaboradores'),
        }
    _sql_constraints = [
        ('ulevel', 'unique(name,course_id)', "ya agregaste este nivel a este curso!"),
        ]
    
class kemas_specialization_course_line(osv.osv):
    _name = 'kemas.specialization.course.line'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Colaborador', required=True),
        'course_id': fields.many2one('kemas.specialization.course', 'Curso', required=True),
        'level_id': fields.many2one('kemas.specialization.course.level', 'Nivel', required=True),
        }
    _sql_constraints = [
        ('ucourse', 'unique(collaborator_id,course_id)', "Este colaborador ya esta registrado en este curso!"),
        ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
