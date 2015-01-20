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
import base64
import calendar
from datetime import *
from datetime import datetime
from datetime import timedelta
import datetime 
from dateutil.parser import  *
import logging
from lxml import etree
import math
from mx import DateTime
from mx import DateTime
import random
import threading
import time
import unicodedata

import addons
from kemas import kemas_extras
from openerp import SUPERUSER_ID
import openerp
from osv import fields, osv
import pooler
import tools
from tools.translate import _


_logger = logging.getLogger(__name__)

class kemas_expositor(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def _person_age(self, cr, uid, ids, name, arg, context={}):
        result = {}
        collaborators = super(osv.osv, self).read(cr, uid, ids, ['id', 'birth'], context=context)
        for collaborator in collaborators:
            result[collaborator['id']] = kemas_extras.calcular_edad(collaborator['birth'], 3)
        return result
    
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_expositor, self).write(cr, uid, ids, vals, context)
        for id in ids:
            if vals.get('photo', False):
                path = addons.__path__[0] + '/web/static/src/img/photo' + 'expositor'
                vals_write = {}
                vals_write['photo_large'] = kemas_extras.crop_image(vals['photo'], path, 128)
                vals_write['photo_medium'] = kemas_extras.crop_image(vals['photo'], path, 64)
                vals_write['photo_small'] = kemas_extras.crop_image(vals['photo'], path, 48)
                super(kemas_expositor, self).write(cr, uid, [id], vals_write, context)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('photo', False):
            path = addons.__path__[0] + '/web/static/src/img/photo' + 'expositor'
            vals['photo_large'] = kemas_extras.crop_image(vals['photo'], path, 128)
            vals['photo_medium'] = kemas_extras.crop_image(vals['photo'], path, 64)
            vals['photo_small'] = kemas_extras.crop_image(vals['photo'], path, 48)
        return super(kemas_expositor, self).create(cr, uid, vals, context)
    
    def on_change_photo(self, cr, uid, ids, photo):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        values = {} 
        if kemas_extras.restrict_size(photo, preferences['max_size_photos']):
            return {'value':{}}
        else:
            return {'value':{'image': False}, 'warning':{'title':_('Error!'), 'message':_('The size of the photo can not be greater than %s KB..!!') % str(preferences['max_size_photos'])}}

    def on_change_birth(self, cr, uid, ids, birth, context={}):
        values = {}
        if birth:
            values['age'] = kemas_extras.calcular_edad(birth, 3)
        return {'value':values}
    
    def on_change_email(self, cr, uid, ids, email):
        if email:
            if kemas_extras.validate_mail(email):
                return {'value':{}}
            else:
                msg = self.pool.get('kemas.func').get_translate(cr, uid, _('E-mail format invalid..!!'))[0]
                return {'value':{'email':''}, 'warning':{'title':'Error', 'message':msg}}
        else:
            return True
    
    def _ff_age(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id', 'birth'])
        for record in records:
            result[record['id']] = kemas_extras.calcular_edad(record['birth'], 3)
        return result
    
    _order = 'name'
    _name = 'kemas.expositor'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='The name of the expositor'),
        'email': fields.char('Email', size=64),
        'active': fields.boolean(u'¿Activo?', required=False),
        'photo': fields.binary("Photo", help="This field holds the image used as avatar for the expositor, limited to 1024x1024px"),
        'photo_large': fields.binary('Large Photo'),
        'photo_medium': fields.binary('Medium Photo'),
        'photo_small': fields.binary('Small Photo'),
        'birth': fields.date('Fecha de Nacimiento'),
        'age': fields.function(_ff_age, type='char', string='Edad'),
        'telef1': fields.char(u'Teléfono 1', size=10, help=u"Numero telefónico. Example: 072878563"),
        'telef2': fields.char(u'Teléfono 2', size=10, help=u"Numero telefónico. Example: 072878563"),
        'kemas_mobile': fields.char('Celular', size=10, help=u"Número de celular. Example: 088729345"),
        'address': fields.text(u'Dirección'),
        'details': fields.text('Details'),
        }
    
    _sql_constraints = [
        ('expositor_cname', 'unique (name)', 'This Name already exist!'),
        ]
    
    def _get_default_image(self, cr, uid, is_company, context=None, colorize=False):
        if is_company:
            image = open(openerp.modules.get_module_resource('base', 'static/src/img', 'company_image.png')).read()
        else:
            image = tools.image_colorize(open(openerp.modules.get_module_resource('base', 'static/src/img', 'avatar.png')).read())
        return tools.image_resize_image_big(image.encode('base64')
                                            )
    _defaults = {
        'photo': lambda self, cr, uid, ctx: self._get_default_image(cr, uid, ctx.get('default_is_company', False), ctx),
        'active': True,
    }

class kemas_recording_type(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    _order = 'name'
    _name = 'kemas.recording.type'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='The name of the recording type'),
        'active': fields.boolean(u'¿Activo?', required=False),
        'sequence_id': fields.many2one('ir.sequence', 'Sequence', required=True),
        'prefix': fields.related('sequence_id', 'prefix', type='char', string='Prefix', readonly=1, store=False, help="Prefix that appears with the code of each recording"),
        'number_next_actual': fields.related('sequence_id', 'number_next_actual', type='char', string=u'Número siguiente', readonly=1, store=False),
        }
    _sql_constraints = [
        ('recording_type_name', 'unique (name)', 'This Name already exist!'),
        ]
    
    _defaults = {  
        'active': True,
        }

class kemas_recording_series(osv.osv):
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_recording_series, self).write(cr, uid, ids, vals, context)
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'recording_series'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_recording_series, self).write(cr, uid, [id], vals_write, context)
        return result
    
    def create(self, cr, uid, vals, *args, **kwargs):
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Series'), ])[0]
        vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'recording_series'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
        return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
    
    def on_change_logo(self, cr, uid, ids, photo):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        values = {} 
        if kemas_extras.restrict_size(photo, preferences['max_size_logos']):
            return {'value':{}}
        else:
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('The size of the logo can not be greater than'))[0]
            msg = "%s %s KB..!!" % (msg, str(preferences['max_size_logos']))
            return {'value':{'logo': False}, 'warning':{'title':_('Error!'), 'message':msg}}

    _order = 'name'
    _name = 'kemas.recording.series'
    _columns = {
        'code': fields.char('Code', size=32, help="Code that is assigned to each series."),
        'logo': fields.binary('Logo', help='The Logo of the serie'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='The name of the recording type'),
        'recording_ids': fields.one2many('kemas.recording', 'series_id', 'recordings', readonly=False),
        'details': fields.text('Details'),
        }
    _sql_constraints = [
        ('uname', 'unique (name)', 'This Name already exist!'),
        ('ucode', 'unique (code)', 'This Name already exist!'),
        ]
    
class kemas_recording(osv.osv):
    def write_log_draft(self, cr, uid, record_id):
        body = u'''
        <div>
            <span>
                Grabación regresada a <b>BORRADOR</b>
                <div>     • <b>%s</b>: %s → %s</div>
            </span>
        </div>
        ''' % (_('Estado'), _('Confirmado'), _('Borrador'))
        # Obtener los seguidores para notificar
        message_follower_ids = self.read(cr, uid, record_id, ['message_follower_ids'])['message_follower_ids']
        return self._write_log_update(cr, uid, record_id, body, message_follower_ids)
    
    def write_log_done(self, cr, uid, record_id):
        body = u'''
        <div>
            <span>
                Grabación <b>CONFIRMADA</b>
                <div>     • <b>%s</b>: %s → %s</div>
            </span>
        </div>
        ''' % (_('Estado'), _('Borrador'), _('Confirmado'))
        # Obtener los seguidores para notificar
        message_follower_ids = self.read(cr, uid, record_id, ['message_follower_ids'])['message_follower_ids']
        return self._write_log_update(cr, uid, record_id, body, message_follower_ids)
    
    def write_log_create(self, cr, uid, record_id):
        body = u'''
        <div>
            <span>
                Grabación <b>CREADA</b>
            </span>
        </div>
        '''
        # Borrar los logs que creados por defectos
        self.pool.get('mail.message').unlink(cr, SUPERUSER_ID, self.pool.get('mail.message').search(cr, uid, [('res_id', '=', record_id)]))
        return self._write_log_update(cr, uid, record_id, body)
    
    def _write_log_update(self, cr, uid, record_id, body, notify_partner_ids=[]):
        # --Escribir un mensaje con un registro de que se paso Estado en Curso
        record_name = self.name_get(cr, uid, [record_id])[0][1]
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        vals_message = {
                        'body' : body,
                        'model' : 'kemas.recording',
                        'record_name' : record_name,
                        'res_id' : record_id,
                        'partner_id' : partner_id,
                        'type' : 'notification',
                        'author_id' : partner_id,
                        }
        message_id = self.pool.get('mail.message').create(cr, uid, vals_message)
        for notify_partner_id in notify_partner_ids:
            vals_notication = {
                               'message_id' : message_id,
                               'partner_id' : notify_partner_id,
                               'read': False,
                               'starred': False,
                               }
            self.pool.get('mail.notification').create(cr, uid, vals_notication)
        return message_id
    
    def done(self, cr, uid, ids, context={}):
        if type(ids).__name__ in ['int', 'long']:
            ids = list(ids)
            
        records = self.read(cr, uid, ids, ['recording_type_id', 'code'])
        for record in records:  
            vals = {'state': 'done'}
            if not record['code']:
                type_obj = self.pool.get('kemas.recording.type')
                sequence_id = type_obj.read(cr, uid, record['recording_type_id'][0], ['sequence_id'])['sequence_id'][0]
                code = str(self.pool.get('ir.sequence').get_id(cr, uid, sequence_id))
                vals['code'] = code
            self.write(cr, uid, [record['id']], vals)
            # Escribir log
            self.write_log_done(cr, uid, record['id'])
        return True
    
    def draft(self, cr, uid, ids, context={}):
        if type(ids).__name__ in ['int', 'long']:
            ids = list(ids)
        records = self.read(cr, uid, ids, ['state'])
        for record in records:
            self.write(cr, uid, [record['id']], {'state': 'draft'})
            # Escribir log
            self.write_log_draft(cr, uid, record['id'])
        return True
    
    def on_change_event_id(self, cr, uid, ids, event_id, context={}):
        values = {}
        if event_id:
            event = self.pool.get('kemas.event').read(cr, uid, event_id, ['collaborator_ids', 'place_id'])
            values['collaborator_ids'] = event['collaborator_ids']
            values['place_id'] = event['place_id'][0]
        else:
            values['collaborator_ids'] = False
            values['place_id'] = False
        return {'value' : values}
    
    def unlink(self, cr, uid, ids, context={}):
        records = self.read(cr, uid, ids, ['code'])
        for record in records:
            if record['code']:
                raise osv.except_osv(_(u'¡Error!'), _(u'!No se puede borrar esta grabación porque ya tiene un CÓDIGO asignado¡'))
        return super(kemas_recording, self).unlink(cr, uid, ids, context)
    
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_recording, self).write(cr, uid, ids, vals, context)
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'recording'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                vals_write['logo_landscape'] = kemas_extras.crop_image_with_size(vals['logo'], path, 112, 64)
                super(kemas_recording, self).write(cr, uid, [id], vals_write, context)
        return result
    
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['registration_date'] = time.strftime("%Y-%m-%d %H:%M:%S")
        vals['create_user_id'] = uid
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'recording'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
            vals['logo_landscape'] = kemas_extras.crop_image_with_size(vals['logo'], path, 112, 64)
        res_id = super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
        # Escribir log
        self.write_log_create(cr, uid, res_id)
        return res_id
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False):
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_recording, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby)
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def on_change_url(self, cr, uid, ids, url, context={}):
        values = {}
        youtube_thumbnail = kemas_extras.get_thumbnail_youtube_video(url)
        if youtube_thumbnail:
            values['logo'] = youtube_thumbnail
        return {'value': values}
    
    _order = 'date DESC, recording_type_id'
    _rec_name = 'theme'
    _name = 'kemas.recording'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _columns = {
        'logo': fields.binary('Portada', help='Portada de la grabación.'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'logo_landscape': fields.binary('Logo apaisado'),
        'theme': fields.char('Theme', size=64, help='The theme of the recording', required=True, states={'done':[('readonly', True)]}),
        'date': fields.datetime('Date', help="Date on which the recording was done", states={'done':[('readonly', True)]}),
        'state': fields.selection([
            ('draft', 'Borrador'),
            ('done', 'Confirmado'),
             ], 'Estado', required=True),
        'registration_date': fields.datetime('Registration date', readonly=True, help="Date on which this recording was entered into the system"),
        'create_user_id': fields.many2one('res.users', 'Registrado por', readonly=True, help='Nombre del usuario que creo el registro'),
        'code': fields.char('Code', size=32, readonly=True, help="unique code that is assigned to each recording"),
        'duration': fields.float('Duration', required=True, help='Duration recording', states={'done':[('readonly', True)]}),
        'details': fields.text('Details', states={'done':[('readonly', True)]}),
        'url': fields.char('URL', size=255, help='Dirección en la que se encuentra almacenado el archivo', states={'done':[('readonly', True)]}),
        'expositor_ids': fields.many2many('kemas.expositor', 'kemas_recording_expositor_rel', 'recording_id', 'expositor_id', 'Expositores', states={'done':[('readonly', True)]}),
        # One to Many Relations
        'event_id': fields.many2one('kemas.event', 'Evento', help='Servicio en el cual se realizó ésta grabación', states={'done':[('readonly', True)]}),
        'recording_type_id': fields.many2one('kemas.recording.type', 'recording type', required=True, ondelete="restrict", states={'done':[('readonly', True)]}),
        'place_id': fields.many2one('kemas.place', 'Place', help='Place where the recording was done', ondelete="restrict", states={'done':[('readonly', True)]}),
        'series_id': fields.many2one('kemas.recording.series', 'Series', help='Name of the series of which this recording', ondelete="restrict", states={'done':[('readonly', True)]}),
        # Many to One Relations
        'tag_ids': fields.many2many('kemas.recording.tag', 'kemas_recording_tag_rel', 'recording_id', 'tag_id', 'Etiquetas', states={'done':[('readonly', True)]}),
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_recording_collaborator_rel', 'recording_id', 'collaborator_id', 'collaborators', help='Collaborators who participated in the recording', states={'done':[('readonly', True)]}),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
    
    _defaults = {  
        'state': 'draft'
        }
    
    _sql_constraints = [
        ('ucode', 'unique (code)', 'This Code already exist!'),
        ('utheme_type', 'unique (theme,recording_type_id)', 'Already registered this with this type of recording!'),
        ]

class kemas_recording_tag(osv.osv):
    _order = 'name'
    _name = 'kemas.recording.tag'
    _columns = {
        'name': fields.char('Nombre', size=64, required=True),
        'description': fields.text('Description'),
        }
    _sql_constraints = [
        ('recording_tag_name', 'unique (name)', u'¡Esta etiqueta ya existe!'),
        ]
        
# vim:expandtab:smartind:tabstop=4:softtabstop=4:shiftwidth=4:
