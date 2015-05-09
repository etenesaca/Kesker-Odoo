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
from datetime import datetime, timedelta
import datetime 
from dateutil.parser import  *
import logging  
from lxml import etree
from mx import DateTime
import random
import threading
import time
import unicodedata

from openerp import addons, tools, pooler, SUPERUSER_ID
import openerp
from openerp.addons.kemas import kemas_extras as extras
from openerp.api import Environment
from openerp.osv import fields, osv
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)
    
class kemas_collaborator_logbook_login(osv.osv):
    def name_get(self, cr, uid, ids, context={}):
        records = self.read(cr, uid, ids, ['id', 'collaborator_id', 'datetime'])
        res = []
        for record in records:
            name = "%s - %s" % (record['collaborator_id'][1], record['datetime'])
            res.append((record['id'], name))  
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('datetime', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('datetime', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def create(self, cr, uid, vals, context={}):
        vals['datetime'] = vals.get('datetime', time.strftime("%Y-%m-%d %H:%M:%S"))
        return super(osv.osv, self).create(cr, uid, vals, context)
    
    _order = 'datetime DESC'
    _name = 'kemas.collaborator.logbook.login'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Colaborador'),
        'datetime': fields.datetime('Fecha y hora'),
        'remote_address': fields.char('Conectado desde', size=255, required=False, readonly=False),
        'base_location': fields.char('Conectado a', size=255, required=False, readonly=False),
        'count': fields.integer('count', required=True),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
    
    _defaults = {  
        'count': 1,
        }
    
class kemas_func(osv.AbstractModel):
    def get_id_by_ext_id(self, cr, uid, ext_id):
        result = False
        md_obj = self.pool['ir.model.data']
        md_ids = md_obj.search(cr, uid, [('name', '=', ext_id)])
        if md_ids:
            result = md_obj.read(cr, uid, md_ids[0], ['res_id'])['res_id']
        return result
        
    def is_in_this_groups(self, cr, uid, group_ext_ids, user_id=False):
        user_obj = self.pool['res.users']
        md_obj = self.pool['ir.model.data']
        
        # Llegan un entero en luigar de lista
        if type(group_ext_ids).__name__ in ['str', 'unicode']:
            group_ext_ids = [group_ext_ids]
            
        # Si no se manda el usuario en los parametros se entiende que es el usuario que consulta
        if not user_id:
            user_id = uid
        
        md_ids = md_obj.search(cr, uid, [('name', 'in', group_ext_ids)])
        mds = md_obj.read(cr, uid, md_ids, ['res_id'])
        
        group_ids = []        
        for md in mds:
            group_ids.append(md['res_id'])
        
        groups_user_ids = user_obj.read(cr, uid, user_id, ['groups_id'])['groups_id']
        result = bool(set(group_ids) & set(groups_user_ids))
        return result
    
    def module_installed(self, cr, uid, module_name):
        sql = """
            SELECT mdl.id FROM ir_module_module AS mdl
            WHERE mdl.state = 'installed' AND name = '%s'
            LIMIT 1 
            """ % module_name
        cr.execute(sql)
        return bool(cr.fetchall())
    
    def mailing(self, cr, uid):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        if config_id:
            config = config_obj.read(cr, uid, config_id, ['mailing', 'use_message_incorporation'])
            if config['mailing'] and config['use_message_incorporation']:
                return True
            else:
                return False
        else:
            return False
            
    def get_tz_by_uid(self, cr, uid, user_id=False):    
        try:
            if not user_id:
                user_id = uid
            tz = self.pool.get('res.users').read(cr, uid, user_id, ['tz'])['tz']
        except:
            tz = self.pool.get('res.users').read(cr, uid, 1, ['tz'])['tz']
        if not tz:
            tz = self.pool.get('res.users').read(cr, uid, 1, ['tz'])['tz']
        if not tz:
            tz = 'America/Guayaquil'
        return tz
        
    def get_translate(self, cr, uid, text, lang=False):
        if not lang:
            sql = """SELECT p.lang from res_users r
                   JOIN res_partner p on p.id = r.partner_id        
                   WHERE r.id = %d""" % (uid)
            cr.execute(sql)
            result_query = cr.fetchall()
            if result_query:
                lang = result_query[0][0]
        sql = """SELECT value FROM ir_translation 
                 WHERE lang = '%s' AND src = '%s'""" % (lang, text)
        cr.execute(sql)
        result_query = cr.fetchall()
        if result_query == []:
            sql = """SELECT value FROM ir_translation 
                     WHERE lang = '%s' AND src ilike '%s'""" % (lang, text)
            cr.execute(sql)
            result_query = cr.fetchall()
        res = []
        for tpl in result_query:
            res.append(tpl[0])
        if res == []:
            res.append(text)
        return list(set(res))
    
    def get_image(self, value, width, height, hr, code='QR'):
        """ genrating image for barcode """
        options = {}
        if width:options['width'] = width
        if height:options['height'] = height
        if hr:options['humanReadable'] = hr
        try:
            # ret_val = createBarcodeDrawing(code, value=str(value), **options)
            ret_val = None
        except Exception, e:
            raise osv.except_osv('Error', e)
            
        return base64.encodestring(ret_val.asString('jpg'))
    
    # --Verficar permisos de Usuario
    def is_in_grups(self, cr, uid, groups_list):
        user_obj = self.pool.get('res.users')
        #-----------------------------------------------------------------------------------------------------------------
        user_id = user_obj.search(cr, uid, [('id', '=', uid), ])
        groups_ids = user_obj.read(cr, uid, user_id, ['groups_id'])[0]['groups_id']
        res = list(set(groups_ids) & set(groups_list))
        if res:
            return True
        else:
            return False
    
    def is_register_attedance_login(self, cr, uid):
        group_obj = self.pool.get('res.groups')
        groups_list = []
        groups_list.append(1)
        groups_list.append(group_obj.search(cr, uid, [('name', '=', 'Kemas / Register Attendance'), ])[0])
        return self.is_in_grups(cr, uid, groups_list)
    
    def is_consultant_login(self, cr, uid):
        group_obj = self.pool.get('res.groups')
        groups_list = []
        groups_list.append(1)
        groups_list.append(group_obj.search(cr, uid, [('name', '=', 'Kemas / Consultant'), ])[0])
        return self.is_in_grups(cr, uid, groups_list)
    
    def verify_permissions(self, cr, uid, ids, context={}):
        vals = {}
        vals['state'] = 'on_going'
        stage_obj = self.pool.get('kemas.event.stage')
        stage_ids = stage_obj.search(cr, uid, [('sequence', '=', 2)])
        if stage_ids:
            vals['stage_id'] = stage_ids[0]
        super(osv.osv, self).write(cr, uid, ids, vals)
        
    def build_username(self, cr, uid, name):       
        def eliminar_tildes(cad):
            return ''.join((c for c in unicodedata.normalize('NFD', cad) if unicodedata.category(c) != 'Mn'))
        name = extras.elimina_tildes(name)
        username = ''
        try:
            username = extras.buid_username(name)
        except: None
        '''----------------------------Verificar si el username generado ya existe, entonces le genra otro con un numero aleatorio al final'''
        user_obj = self.pool.get('res.users')
        repetido = True
        while repetido:
            user_ids = user_obj.search(cr, uid, [('login', '=', username), ])
            if user_ids:
                username = username + str(random.randint(1, 20))
            else:
                repetido = False
        return eliminar_tildes(username)

    def create_user(self, cr, uid, name, email, password, group, photo=False, partner_id=False):
        username = self.build_username(cr, uid, name)
        user_obj = self.pool.get('res.users')
        groups_obj = self.pool.get('res.groups')
        vals = {
                'login': username,
                'company_id': 1,
                'password': unicode(password).lower(),
                'partner_id': partner_id,
                }
        if not partner_id:
            vals['image'] = photo
            vals['name'] = name
            vals['email'] = email
            vals['tz'] = self.get_tz_by_uid(cr, uid)
        user_id = user_obj.create(cr, uid, vals, {'mail_create_nolog': True}) 
        
        #--Borrar los grupos---------------------------
        groups_ids = groups_obj.search(cr, uid, [])
        vals_01 = {'groups_id':[(5, groups_ids)]}
        # --Asginar Roles correspondientes
        
        user_obj.write(cr, uid, [user_id], vals_01)
        list_groups = [group]
        groups_obj = self.pool.get('res.groups')
        user_groups_ids = groups_obj.search(cr, uid, [('name', '=', 'Employee'), ])
        if user_groups_ids:
            list_groups.append(user_groups_ids[0])
        vals_02 = {'groups_id':[(6, 0, list_groups)]}
        user_obj.write(cr, uid, [user_id], vals_02)
        return {'user_id' : user_id, 'username' : username, 'password' : password}
    _name = 'kemas.func'

class kemas_massive_email_line(osv.osv):
    def on_change_email(self, cr, uid, ids, email):
        if email:
            if extras.validate_mail(email):
                return {'value':{}}
            else:
                msg = self.pool.get('kemas.func').get_translate(cr, uid, _('E-mail format invalid..!!'))[0]
                return {'value':{'email': False}, 'warning':{'title':'Error', 'message':msg}}
        else:
            return True
        
    _rec_name = 'email'
    _name = 'kemas.massive.email.line'
    _columns = {
        'email': fields.char('Email', size=64, required=True),
        'massive_email_id': fields.many2one('kemas.massive.email', 'massive_mail'),
        }

class kemas_massive_email(osv.osv):
    def load_collaborators(self, cr, uid, ids, context={}):
        mail = self.read(cr, uid, ids[0], ['team_id'])
        collaborator_obj = self.pool.get('kemas.collaborator')
        args = []
        if mail['team_id']:
            args.append(('team_id', '=', mail['team_id'][0]))
        
        collaborator_ids = collaborator_obj.search(cr, uid, args, context=context)
        vals = {}
        vals['collaborator_ids'] = [(6, 0, collaborator_ids)]
        self.write(cr, uid, ids, vals, context)    
        
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['state'] = 'draft'
        vals['date_create'] = time.strftime("%Y-%m-%d %H:%M:%S")
        return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
    
    def _send_email(self, db_name, uid, message_id, email_list, collaborator_ids, message, subject, context={}):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        
        #--------------------------------------------------------------------------------------------
        server_obj = self.pool.get('ir.mail_server')
        config_obj = self.pool.get('kemas.config')
        #--------------------------------------------------------------------------------------------
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #--------------------------------------------------------------------------------------------
        if self.read(cr, uid, message_id, ['use_header_message'])['use_header_message']:
            header = config_obj.build_header_footer_string(cr, uid, preferences['header_email'])
            footer = config_obj.build_header_footer_string(cr, uid, preferences['footer_email'])
            if header: 
                body = header 
            else: 
                body = ''
            body += unicode(u'''%s''') % message
            if footer:
                body += footer
        else:
            body = unicode(u'''%s''') % message
        
        #---Agregar Archivos Adjuntos--------------------------------------------------------
        attachments = []
        message = self.browse(cr, uid, message_id)
        attachment_obj = self.pool.get('ir.attachment')
        attachment_ids = attachment_obj.search(cr, uid, [('res_model', '=', 'kemas.massive.email'), ('res_id', '=', message_id)])
        atts = attachment_obj.read(cr, uid, attachment_ids, ['datas_fname', 'datas'])
        for attach in atts:
            att = (attach['datas_fname'], base64.b64decode(attach['datas']))
            attachments.append(att)  
        #------------------------------------------------------------------------------------
        for email in email_list:
            message = server_obj.build_email(preferences['reply_email'], [], subject, body, [email], None, preferences['reply_email'], attachments, None, None, False, 'html')
            try:
                if server_obj.send_email(cr, uid, message): 
                    _logger.info('Massive email successfully sent to: %s', email)
                else:
                    _logger.warning('Massive email Failed to send email to: %s', email)
            except:
                _logger.warning('Massive email Failed to send email to: %s', email)
        
    def send_email(self, cr, uid, ids, context={}):
        line_obj = self.pool.get('kemas.massive.email.line')
        collaborator_obj = self.pool.get('kemas.collaborator')
        val = {
             'state':'sent',
             'date_sent': time.strftime("%Y-%m-%d %H:%M:%S")
             }
        super(osv.osv, self).write(cr, uid, ids, val)
        #---Enviar los correos--------------------------------------------------------------------------
        massive_email = self.read(cr, uid, ids[0], [])
        email_list = []
        for collaborator_id in massive_email['collaborator_ids']:
            email_list.append(collaborator_obj.read(cr, uid, collaborator_id, ['email'])['email'])
        for line_id in massive_email['line_ids']:
            email_list.append(line_obj.read(cr, uid, line_id, ['email'])['email'])
            
        if email_list == []:
            raise osv.except_osv(u'¡Operación no válida!', _('No recipients to send mail.'))
        threaded_sending = threading.Thread(target=self._send_email, args=(cr.dbname , uid, ids[0], email_list, massive_email['collaborator_ids'], massive_email['message'], massive_email['subject'], context))
        threaded_sending.start()
        context['message'] = self.pool.get('kemas.func').get_translate(cr, uid, _('The sending email has begun...'))[0]            
        return{            
            'context': context,
            'name' : 'Close of past events',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kemas.message.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
            }
    
    def draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state': 'draft'})

    def fields_get(self, cr, uid, fields={}, context={}, write_access=True): 
        result = super(kemas_massive_email, self).fields_get(cr, uid, fields, context, write_access)
        if not context is None and context and type(context).__name__ == "dict":
            def_dic = {}
            config_obj = self.pool.get('kemas.config')
            config_id = config_obj.get_correct_config(cr, uid)
            if config_id:
                try:
                    preferences = config_obj.read(cr, uid, config_id, [])
                    def_dic['use_header_message'] = preferences['massive_mail_use_header']
                    def_dic['message'] = preferences['massive_mail_body_default']
                except:
                    raise osv.except_osv(u'¡Operación no válida!', _('No hay ninguna configuracion del Sistema definida.'))
                def_dic['state'] = 'draft'
                self._defaults = def_dic
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
                
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_create', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date_create', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    _order = 'date_sent'
    _rec_name = 'subject'
    _name = 'kemas.massive.email'
    _columns = {
        'message': fields.text('Message', required=True, help='It is the body of the e-mail, can be written in HTML structure.', states={'sent':[('readonly', True)]}),
        'use_header_message': fields.boolean('Use system header and footer?', help='Uncheck this box if you do not want to use email header and footer configured in the system for this email in the system'),
        'subject': fields.char('Subject', size=64, required=True, help='It is a subject of the email.', states={'sent':[('readonly', True)]}),
        'date_create': fields.datetime('Date Create', help='Date on which this email was created.'),
        'date_sent': fields.datetime('Date last sent', help='Last date you sent this email.'),
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        'state': fields.selection([
            ('creating', 'Creating'),
            ('draft', 'Draft'),
            ('sent', 'Sent'),
             ], 'State', select=True, help='State in which this email.'),
        'team_id': fields.many2one('kemas.team', 'Team', help='Team who is going to send emails', states={'sent':[('readonly', True)]}),
        'line_ids': fields.one2many('kemas.massive.email.line', 'massive_email_id', 'Other recipients', states={'sent':[('readonly', True)]}),
        #Many to Many Relations----------------------------------------------------------------------------------------------
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_collaborator_massive_email_rel', 'email_id', 'collaborator_id', 'Recipients', help='Collaborators who will receive this email', states={'sent':[('readonly', True)]}),
        }
    
class kemas_config(osv.osv):
    def crop_photo(self, cr, uid, ids, context={}):
        # Colaboradores
        field_name = "photo"
        obj = self.pool.get('kemas.collaborator')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
            
        # Expositores
        obj = self.pool.get('kemas.expositor')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
                
        # Areas
        field_name = "logo"
        obj = self.pool.get('kemas.area')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
    
        # Equipos
        field_name = "logo"
        obj = self.pool.get('kemas.team')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
    
        # Series
        obj = self.pool.get('kemas.recording.series')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
    
        # Niveles
        obj = self.pool.get('kemas.level')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
        
        # Sition Web
        obj = self.pool.get('kemas.web.site')
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
        
        # Procesar grabaciones
        obj = self.pool.get('kemas.recording')
        """
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name, 'url'])
        for record in records:
            youtube_thumbnail = extras.get_thumbnail_youtube_video(record['url'])
            if youtube_thumbnail and not record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: youtube_thumbnail})
            elif record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
        """
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name])
        for record in records:
            if record[field_name]:
                obj.write(cr, uid, [record['id']], {field_name: record[field_name]})
        return True
    
    def build_header_footer_string(self, cr, uid, string):
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        string = string.replace('%hs', unicode(preferences['url_system']))
        string = string.replace('%re', unicode(preferences['reply_email']))
        string = string.replace('%se', unicode(preferences['system_email']).lower())
        string = string.replace('%ns', unicode(preferences['name_submitting']))
        
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        string = string.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        string = string.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        string = string.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        return string
    
    def build_add_remove_points_string(self, cr, uid, message, collaborator_id, description, points):
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'name', 'nick_name', 'gender', 'points', 'level_name'])
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%cl', unicode(extras.get_standard_names(collaborator['name'])))
        message = message.replace('%pt', unicode(collaborator['points']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        message = message.replace('%em', unicode(collaborator['email']).lower())
        
        message = message.replace('%na', unicode(preferences['name_system']))
        message = message.replace('%se', unicode(preferences['system_email']).lower())
        message = message.replace('%hs', unicode(preferences['url_system']))
        message = message.replace('%na', unicode(preferences['name_submitting']))
        if collaborator['gender'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        
        try:
            description = description.replace('\n', '<br/>')
            try:message = message.replace('%ds', unicode(description, 'utf8'))
            except:message = message.replace('%ds', unicode(description))
        except:None
        
        message = message.replace('%mp', unicode(points))
        
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        return message
    
    def send_email_add_remove_points(self, cr, uid, collaborator_id, description, points, type, context={}):
        def send_email():
            if preferences['use_message_add_remove_points'] == False:return None 
            if type == 'add' or type == 'increase':
                body_message = self.build_add_remove_points_string(cr, uid, preferences['Message_add_points'], collaborator_id, description, points)
            else:
                body_message = self.build_add_remove_points_string(cr, uid, preferences['Message_remove_points'], collaborator_id, description, points)
            #------------------------------------------------------------------------------------
            if preferences['use_header_message_add_remove_points']:
                header = self.build_header_footer_string(cr, uid, preferences['header_email'])
                footer = self.build_header_footer_string(cr, uid, preferences['footer_email'])
                if header: 
                    body = header 
                else: 
                    body = ''
                body += unicode(u'''%s''') % body_message
                if footer:
                    body += footer
            else:
                body = unicode(u'''%s''') % body_message
            server_obj = self.pool.get('ir.mail_server')
            address = collaborator['email']
            message = server_obj.build_email(preferences['reply_email'], [address], subject, body, [], None, preferences['reply_email'], attachments, None, None, False, 'html')
            try:
                if server_obj.send_email(cr, uid, message): 
                    _logger.info('Manual change points Notify mail successfully sent to: %s', address)
                    return True
                else:
                    _logger.warning('Manual change points Notify Failed to send email to: %s', address)
                    return False
            except:
                _logger.warning('Manual change points Notify Failed to send email to: %s', address)
                return False

        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email'])
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['mailing'] == False:
            return False
        #---Agregar Archivos Adjuntos--------------------------------------------------------
        attachments = []
        #------------------------------------------------------------------------------------
        subject = self.build_incorporation_string(cr, uid, preferences['Message_add_remove_points_subject'], collaborator_id)
        res_send_email = send_email()
        return res_send_email
    
    def build_incorporation_string(self, cr, uid, message, collaborator_id):
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'name', 'nick_name', 'gender', 'code', 'points', 'level_name', 'username', 'password'])
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        message = message
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%cl', unicode(extras.get_standard_names(collaborator['name'])))
        message = message.replace('%cd', unicode(collaborator['code']))
        message = message.replace('%pt', unicode(collaborator['points']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        message = message.replace('%us', unicode(collaborator['username']))
        message = message.replace('%ps', unicode(collaborator['password']))
        message = message.replace('%em', unicode(collaborator['email']).lower())
        message = message.replace('%hs', unicode(preferences['url_system']))
        message = message.replace('%re', unicode(preferences['reply_email']))
        message = message.replace('%se', unicode(preferences['system_email']).lower())
        message = message.replace('%sd', unicode(cr.dbname))
        message = message.replace('%ns', unicode(preferences['name_submitting']))
        message = message.replace('%na', unicode(preferences['name_system']))
        if collaborator['gender'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        return message
    
    def send_email_incoporation(self, cr, uid, collaborator_id, context={}):
        def send_email():
            if preferences['use_message_incorporation'] == False:return None 
            body_message = self.build_incorporation_string(cr, uid, preferences['Message_information_incorporation'], collaborator_id)
            #------------------------------------------------------------------------------------
            if preferences['use_header_message_incorporation']:
                header = self.build_header_footer_string(cr, uid, preferences['header_email'])
                footer = self.build_header_footer_string(cr, uid, preferences['footer_email'])
                if header: 
                    body = header 
                else: 
                    body = ''
                body += unicode(u'''%s''') % body_message
                if footer:
                    body += footer
            else:
                body = unicode(u'''%s''') % body_message
            server_obj = self.pool.get('ir.mail_server')
            address = collaborator['email']
            message = server_obj.build_email(preferences['reply_email'], [address], subject, body, [], None, preferences['reply_email'], attachments, None, None, False, 'html')
            try:
                if server_obj.send_email(cr, uid, message): 
                    _logger.info('Incorporation Notify mail successfully sent to: %s', address)
                    return True
                else:
                    _logger.warning('Incorporation Notify Failed to send email to: %s', address)
                    return False
            except:
                _logger.warning('Incorporation Notify Failed to send email to: %s', address)
                return False

        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email'])
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['mailing'] == False:
            return False
        #---Agregar Archivos Adjuntos--------------------------------------------------------
        attachments = []
        try:
            message = self.browse(cr, uid, preferences['id'])
            attachments.append((message.collaborator_manual.datas_fname, base64.b64decode(message.collaborator_manual.datas)))
        except:None  
        #------------------------------------------------------------------------------------
        subject = self.build_incorporation_string(cr, uid, preferences['Message_information_incorporation_subject'], collaborator_id)
        res_send_email = send_email()
        return res_send_email
    
    def _build_event_completed_string(self, cr, uid, preferences, message, event_id, service_id, collaborator_id, type_attend):
        service_obj = self.pool.get('kemas.service')
        service = service_obj.read(cr, uid, service_id, [])
        event_obj = self.pool.get('kemas.event')
        event = event_obj.read(cr, uid, event_id, ['date_start', 'service_id', 'place_id', 'attend_on_time_points', 'late_points', 'not_attend_points'])
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'name', 'nick_name', 'gender', 'points', 'level_name'])
        #------------------------------------------------------------------------------------
        """
        %%na - Name of system
        %%ds - Date of service
        %%dy - Day of service
        %%sr - Service's name
        %%sp - Service Place
        %%st - Time Start
        %%fn - Time End
        %%te - Time of entry
        %%tl - Time Limit
        %%tr - Time register
        %%nk - Collaborator's Nick name
        %%cl - Collaborator's Name
        %%pt - Collaborator's Points
        %%lv - Collaborator's Level
        %%gn - ('o'=male, 'a'=female)
        %%pe - points earned
        %%pl - Lost points
        %%da - Date
        %%tm - Time
        %%dt - Date and Time
        """
        message = message.replace('%na', unicode(preferences['name_system']))
        message = message.replace('%se', unicode(preferences['system_email']))
        message = message.replace('%hs', unicode(preferences['url_system']))
        message = message.replace('%na', unicode(preferences['name_submitting']))
        
        message = message.replace('%cl', unicode(extras.get_standard_names(collaborator['name'])))
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%pt', unicode(collaborator['points']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        message = message.replace('%em', unicode(collaborator['email']).lower())
        message = message.replace('%cl', unicode(extras.get_standard_names(collaborator['name'])))
        if collaborator['gender'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        
        message = message.replace('%ds', unicode(extras.convert_date_format_short_str(event['date_start'])))
        message = message.replace('%dy', unicode(extras.convert_date_format_long(event['date_start']), 'utf8'))
        message = message.replace('%sr', unicode(event['service_id'][1]).title())
        message = message.replace('%sp', unicode(event['place_id'][1]))
        message = message.replace('%st', unicode(extras.convert_float_to_hour_format(service['time_start'])))
        message = message.replace('%fn', unicode(extras.convert_float_to_hour_format(service['time_end'])))
        message = message.replace('%te', unicode(extras.convert_float_to_hour_format(service['time_entry'])))
        message = message.replace('%tl', unicode(extras.convert_float_to_hour_format(service['time_limit'])))
        message = message.replace('%tr', unicode(extras.convert_float_to_hour_format(service['time_register'])))
        
        if type_attend == 'just_time':
            message = message.replace('%pe', unicode(event['attend_on_time_points']))
            message = message.replace('%pl', unicode(0))
        elif type_attend == 'late':
            message = message.replace('%pe', unicode(0))
            message = message.replace('%pl', unicode(event['late_points']))
        elif type_attend == 'absence':
            message = message.replace('%pe', unicode(0))
            message = message.replace('%pl', unicode(event['not_attend_points']))
        return message
    
    def build_event_completed_string(self, cr, uid, preferences, event_id, service_id, collaborator_id, type_attend, IM=False):
        if type_attend == 'just_time':
            if IM:
                message = preferences['message_im_event_completon_on_time']
            else:
                message = preferences['message_event_completon_on_time']
        elif type_attend == 'late':
            if IM:
                message = preferences['message_im_event_completon_late']
            else:
                message = preferences['message_event_completon_late']
        elif type_attend == 'absence':
            if IM:
                message = preferences['message_im_event_completon_absence']
            else:
                message = preferences['message_event_completon_absence']
        return self._build_event_completed_string(cr, uid, preferences, message, event_id, service_id, collaborator_id, type_attend)
            
    def build_event_string(self, cr, uid, message, line_id):
        event_obj = self.pool.get('kemas.event')
        service_obj = self.pool.get('kemas.service')
        collaborator_obj = self.pool.get('kemas.collaborator')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        activity_obj = self.pool.get('kemas.activity')
        line = line_obj.read(cr, uid, line_id, ['collaborator_id', 'activity_ids', 'event_id'])
        event = event_obj.read(cr, uid, line['event_id'][0], ['date_start', 'service_id', 'place_id', 'attend_on_time_points', 'late_points', 'not_attend_points', 'information'])
        service = service_obj.read(cr, uid, event['service_id'][0], ['time_start', 'time_end', 'time_entry', 'time_limit', 'time_register'])
        collaborator = collaborator_obj.read(cr, uid, line['collaborator_id'][0], ['email', 'name', 'nick_name', 'gender', 'code', 'points', 'level_name', 'username', 'password'])
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        message = message.replace('%cl', unicode(extras.get_standard_names(collaborator['name'])))
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%cd', unicode(collaborator['code']))
        message = message.replace('%pt', unicode(collaborator['points']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        message = message.replace('%us', unicode(collaborator['username']))
        message = message.replace('%ps', unicode(collaborator['password']))
        message = message.replace('%em', unicode(collaborator['email']).lower())
        message = message.replace('%hs', unicode(preferences['url_system']))
        message = message.replace('%re', unicode(preferences['reply_email']))
        message = message.replace('%se', unicode(preferences['system_email']).lower())
        message = message.replace('%sd', unicode(cr.dbname))
        message = message.replace('%ns', unicode(preferences['name_submitting']))
        message = message.replace('%na', unicode(preferences['name_system']))
        if collaborator['gender'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        
        message = message.replace('%ds', unicode(extras.convert_date_format_short_str(event['date_start'])))
        
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        fecha_del_evento = extras.convert_to_tz(event['date_start'], tz)        
        try:
            try:message = message.replace('%dy', unicode(extras.convert_date_format_long(fecha_del_evento), 'utf8'))
            except:message = message.replace('%dy', unicode(extras.convert_date_format_long(fecha_del_evento)))
        except:None
        try:
            event_information = ''
            if event['information']:
                event_information = unicode(event['information'])
            message = message.replace('%in', event_information)
        except:None
        message = message.replace('%sr', unicode(event['service_id'][1]).title())
        message = message.replace('%sp', unicode(event['place_id'][1]))
        message = message.replace('%st', unicode(extras.convert_float_to_hour_format(service['time_start'])))
        message = message.replace('%es', unicode(extras.convert_float_to_hour_format(service['time_end'])))
        message = message.replace('%te', unicode(extras.convert_float_to_hour_format(service['time_entry'])))
        message = message.replace('%tl', unicode(extras.convert_float_to_hour_format(service['time_limit'])))
        message = message.replace('%tr', unicode(extras.convert_float_to_hour_format(service['time_register'])))
        message = message.replace('%at', unicode(event['attend_on_time_points']))
        message = message.replace('%lt', unicode(event['late_points']))
        message = message.replace('%ab', unicode(event['not_attend_points']))
        
        detail_ids = line['activity_ids']
        activities = ''
        if detail_ids:
            activities = unicode(u'''
            <p style="font-family: georgia, serif; font-weight: normal; font-size: 15px; line-height: 20px; color: #595959; margin-top: 0; margin-left: 0; margin-bottom: 20px; margin-right: 0; padding: 0;" align="justify">
                <b>La actividades que se te han asignado para este servicio son:</b>
            </p>
            <ul style="font-family: georgia, serif; font-weight: normal; font-size: 15px; line-height: 20px; color: #595959; margin-top: 0; margin-left: 0; margin-bottom: 20px; margin-right: 0; padding: 1;" align="justify">
            ''')
            details = activity_obj.read(cr, uid, detail_ids, ['name'])
            for detail in details:
                activities += unicode(u'''<li>%s</li>''') % unicode(detail['name'])
            activities += unicode(u'''</ul>''')
        message = message.replace('%ac', unicode(activities))
        
        message = extras.cambiar_meses_a_espaniol(message)
        return message
 
    def send_email_event_completed(self, cr, uid, service_id, event_id, collaborator_id, type_attend, context={}):        
        def send_email():
            if preferences['use_event_completion'] == False:return None
            body_message = self.build_event_completed_string(cr, uid, preferences, event_id, service_id, collaborator_id, type_attend)
            #------------------------------------------------------------------------------------
            if preferences['use_header_message_event_completion']:
                header = self.build_header_footer_string(cr, uid, preferences['header_email'])
                footer = self.build_header_footer_string(cr, uid, preferences['footer_email'])
                if header: 
                    body = header + '<br/>' 
                else: 
                    body = ''
                body += unicode(u'''%s''') % body_message
                if footer:
                    body += '<br/>' + footer
            else:
                body = unicode(u'''%s''') % body_message
            server_obj = self.pool.get('ir.mail_server')
            address = collaborator['email']
            message = server_obj.build_email(preferences['reply_email'], [], subject, body, [address], None, preferences['reply_email'], None, None, None, False, 'html')
            try:
                if server_obj.send_email(cr, uid, message): 
                    _logger.info('Event completed mail successfully sent to: %s', address)
                    return True
                else:
                    _logger.warning('Event completed Notify Failed to send email to: %s', address)
                    return False
            except:
                _logger.warning('Event completed Notify Failed to send email to: %s', address)
                return False
        
        config_obj = self.pool.get('kemas.config')
        collaborator_obj = self.pool.get('kemas.collaborator')
        with Environment.manage():
            collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email'])
            config_id = config_obj.get_correct_config(cr, uid)
            preferences = config_obj.read(cr, uid, config_id, [])
            if preferences['mailing'] == False:
                return False
            
            subject = self._build_event_completed_string(cr, uid, preferences, preferences['message_event_completon_subject'], event_id, service_id, collaborator_id, type_attend)
            res_send_email = send_email()

        return res_send_email
    
    def send_email_event(self, cr, uid, line_id, context={}):
        def send_email():
            if preferences['use_message_event'] == False:return None
            body_message = self.build_event_string(cr, uid, preferences['Message_information_event'], line_id)
            #------------------------------------------------------------------------------------
            if preferences['use_header_message_event']:
                header = self.build_header_footer_string(cr, uid, preferences['header_email'])
                footer = self.build_header_footer_string(cr, uid, preferences['footer_email'])
                if header: 
                    body = header + '<br/>' 
                else: 
                    body = ''
                body += unicode(u'''%s''') % body_message
                if footer:
                    body += '<br/>' + footer
            else:
                body = unicode(u'''%s''') % body_message
            server_obj = self.pool.get('ir.mail_server')
            address = collaborator['email']
            message = server_obj.build_email(preferences['reply_email'], [], subject, body, [address], None, preferences['reply_email'], None, None, None, False, 'html')
            try:
                if server_obj.send_email(cr, uid, message): 
                    _logger.info('New Event Notify mail successfully sent to: %s', address)
                    return True
                else:
                    _logger.warning('New Event Notify Failed to send email to: %s', address)
                    return False
            except:
                _logger.warning('New Event Notify Failed to send email to: %s', address)
                return False
        
        config_obj = self.pool.get('kemas.config')
        collaborator_obj = self.pool.get('kemas.collaborator')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        with Environment.manage():
            line = line_obj.read(cr, uid, line_id, ['collaborator_id', 'activity_ids', 'event_id'])
            collaborator = collaborator_obj.read(cr, uid, line['collaborator_id'][0], ['email'])
            config_id = config_obj.get_correct_config(cr, uid)
            preferences = config_obj.read(cr, uid, config_id, [])
            if preferences['mailing'] == False:
                return False
            
            subject = self.build_event_string(cr, uid, preferences['Message_information_event_subject'], line_id)
            res_send_email = send_email()
            return res_send_email
            
    def get_correct_config(self, cr, uid, fields_to_read=False):
        config_ids = self.search(cr, uid, [])
        dic = []
        if config_ids:
            for config_id in config_ids:
                dic.append(self.read(cr, uid, config_id, ['sequence'])['sequence'])
            correct_seq = min(dic)
            config_ids = self.search(cr, uid, [('sequence', '=', correct_seq)])
            if config_ids:
                if fields_to_read:
                    return self.read(cr, uid, config_ids[0], fields_to_read)
                return config_ids[0]
        else:
            return False
    
    def set_chages_in_res(self, cr, uid, config_id):
        config = self.read(cr, uid, config_id, [])
        res_company_obj = self.pool.get('res.company')
        res_partner_obj = self.pool.get('res.partner')
        res_company_obj.write(cr, uid, 1, {
                                              'name':config['name_system'],
                                              'logo':config['system_logo'],
                                              })
        company = res_company_obj.browse(cr, uid, 1)
        res_partner_obj.write(cr, uid, company.partner_id.id, {
                                              'name':config['name_system'],
                                              })
        
    def create(self, cr, uid, vals, *args, **kwargs):
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Preference'), ])[0]
        vals['sequence'] = int(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        res = super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
        config_id = self.get_correct_config(cr, uid)
        self.set_chages_in_res(cr, uid, config_id)
        return res
        
    def write(self, cr, uid, ids, vals, context={}):
        res = super(kemas_config, self).write(cr, uid, ids, vals, context)
        config_id = self.get_correct_config(cr, uid)
        self.set_chages_in_res(cr, uid, config_id)
        return res
    
    _rec_name = "default_points"
    _name = 'kemas.config'
    _order = 'sequence'
    _columns = {
        'default_attend_on_time_points': fields.integer('Points for attend on time', help="Default points will increase to an collaborator for being on time to the service.."),
        'default_late_points': fields.integer('Points for being late', help="Default point is decreased to a contributor for not arriving on time."),
        'default_not_attend_points': fields.integer('Points for not attend', help="Default point is decreased to a collaborator not to asist to a service."),
        'default_points': fields.integer('Default points', help="Number of points assigned to a collaborator to create your registration"),
        'name_system': fields.char('Name System', size=255, required=True, help='System name, it will show up also in the reports.'),
        'url_system': fields.char('URL System', size=255, required=True, help='The Url of System.'),
        'sequence': fields.integer('Sequence', help="Prioritization of configurations"),
        'use_attachments_in_im': fields.boolean('Use attachments in IM?', required=True, help='Do you want that the attachments to emails are also sent to the IM messages?'),
        'use_subject_in_im': fields.boolean('Use Subject in IM?', required=True, help='Do you want to include the matter in IM?'),
        'number_replacements': fields.integer('Number replacements'),
        #---Images and logos------------------------
        'logo': fields.binary('Logo', help='The reports Logo.'),
        'system_logo': fields.binary('System Logo', help='The System Logo.'),
        #---Cliente de registro asistencia---------
        'logo_program_client': fields.binary('Imagen de Cabecera', help='Es la imagen que va a salir en la cabecera del programa para registro de asistencias.'),
        'frequency_program_client': fields.integer('Frecuencia de conexion', help="Frecuencia en segundos con la que el programa se conecta al sistema para consultar los datos"),
        'allow_checkout_registers':fields.boolean('Permitir registrar registro de salida', required=False, help="Indica si se va poder registrar las salidas de los colaboradores"),
        #---Report----------------------------------
        'report_header': fields.text('Report header', help='Text to be displayed in the header of the report.'),
        'use_header': fields.boolean('Use?'),
        'report_footer': fields.text('Report footer', help='Text to be displayed in the footer of the report.'),
        'use_footer': fields.boolean('Use?'),
        #---Email----------------------------------
        'collaborator_manual': fields.many2one('ir.attachment', 'Collaborator manual', help='It is the user manual for collaborators who are sent as an attachment in the welcome email.'),
        'mailing': fields.boolean('Mailing?', help='Indicates whether or not to use the tool with notification emails.'),
        'footer_email': fields.text('Footer', help='Text that is sent in the header of all emails.'),
        'header_email': fields.text('Header', help='Text that is sent in the footer of all emails.'),
        #---Incorporation e-mail------------------
        'use_message_im_incorporation': fields.boolean('Use IM notification?', required=True, help='?'),
        'Message_im_information_incorporation': fields.text('Message'),
        
        'use_message_incorporation': fields.boolean('Use email notification?', required=True, help='Use this email to notify?'),
        'use_header_message_incorporation': fields.boolean('Use system header and footer?', help='Uncheck this box if you do not want to use email header and footer configured in the system for this email in the system'),
        'Message_information_incorporation': fields.text('Message'),
        'Message_information_incorporation_subject': fields.char('Subject', size=64, help='Subject of e-mail'),
        #---Event e-mail--------------------------
        'use_message_im_event': fields.boolean('Use IM notification?', required=True, help='?'),
        'Message_im_information_event': fields.text('Message'),
        
        'work_in_background_event': fields.boolean('Work in backgound?', required=True, help='Send notification e-mails in background?'),
        'use_message_event': fields.boolean('Use email notification?', required=True, help='Use this email to notify?'),
        'use_header_message_event': fields.boolean('Use system header and footer?', help='Uncheck this box if you do not want to use email header and footer configured in the system for this email in the system'),
        'Message_information_event': fields.text('Message'),
        'Message_information_event_subject': fields.char('Subject', size=64, help='Subject of e-mail'),
        
        'name_submitting': fields.char('Name submitting', size=64),
        'reply_email': fields.char('Reply email', size=255),
        'system_email': fields.char('System email', size=255),
        #---Finalizacion de un evento----------------------
        'use_event_completion': fields.boolean('Use email notification?', required=True, help='Using or not the notifications of completion of an event?'),
        'use_header_message_event_completion': fields.boolean('Use system header and footer?', help='Uncheck this box if you do not want to use email header and footer configured in the system for this email in the system'),
        'use_im_event_completion': fields.boolean('Use IM notification?', required=True, help='Using or not the IM notifications of completion of an event?'),
        'message_event_completon_subject': fields.char('Subject', size=64, help='Subject of e-mail'),
        
        'message_event_completon_on_time': fields.text('Message'),
        'message_im_event_completon_on_time': fields.text('Message'),
        
        'message_event_completon_late': fields.text('Message'),
        'message_im_event_completon_late': fields.text('Message'),
        
        'message_event_completon_absence': fields.text('Message'),
        'message_im_event_completon_absence': fields.text('Message'),
        
        'use_mail_event_completion_canceled': fields.boolean('Use?', required=True),
        'message_event_completon_canceled_subject': fields.char('Subject', size=64, help='Subject of e-mail'),
        'message_event_completon_canceled': fields.text('Message'),
        'use_im_event_completion_canceled': fields.boolean('Use IM notification?', required=True),
        'message_im_event_completon_canceled': fields.text('Message'),
        #---Massive email----------------------------------
        'massive_mail_body_default': fields.text('Cuerpo del Correo massivo por defecto'),
        'massive_mail_use_header': fields.boolean('Marcar por defector el uso de cabeceras y pies de correo establecidas en el sistema?', help='La opcion que este marcado aparecera por defecto cada vez que se cree un nuevo correo massivo'),
        'send_IM_massive_email': fields.boolean('Send an IM?', required=True, help='Send instant message to notify that was mailed?'),
        'Message_information_massive_email': fields.text('Message'),
        #---Add / Remove Points----------------------------
        'use_message_add_remove_points': fields.boolean('Use email notification?', required=True, help='Use this email to notify?'),
        'Message_add_remove_points_subject': fields.char('Subject', size=64, help='Subject of e-mail'),
        
        'use_message_im_add_points': fields.boolean('Use IM notification?', required=True, help='?'),
        'use_header_message_add_remove_points': fields.boolean('Use system header and footer?', help='Uncheck this box if you do not want to use email header and footer configured in the system for this email in the system'),
        'Message_im_add_points': fields.text('Message'),
        'Message_add_points': fields.text('Message'),
        
        'use_message_im_remove_points': fields.boolean('Use IM notification?', required=True, help='?'),
        'Message_im_remove_points': fields.text('Message'),
        'Message_remove_points': fields.text('Message'),
        #---QR Code - Collaborator Form-------------------
        'qr_text': fields.text('QR code text', required=True),
        'qr_width': fields.integer('Width', required=True),
        'qr_height': fields.integer('height', required=True),
        #---Bar Code - Collaborator Form-------------------
        'bc_type': fields.selection([
            ('code128', 'Code128'),
            ('code39', 'Code39'),
            ('ean', 'EAN'),
            ('ean8', 'EAN8'),
            ('ean13', 'EAN13'),
            ('gs1', 'GS1'),
            ('gtin', 'GTIN'),
            ('isbn', 'ISBN'),
            ('isbn10', 'ISBN10'),
            ('isbn13', 'ISBN13'),
            ('itf', 'ITF'),
            ('jan', 'JAN'),
            ('pzn', 'PZN'),
            ('upc', 'UPC'),
            ('upca', 'UPCA'),
             ], 'Typo de Codigo de Barras', required=True),
        'bc_text': fields.char('Texto de Codigo de barras', size=32, required=True),
        'bc_write_text': fields.boolean(u'¿legible para lectura?', required=False),
        'bc_module_width': fields.float('Ancho', digits=(16, 2), required=True),
        'bc_module_height': fields.float('Alto', digits=(16, 2), required=True),
        'bc_quiet_zone': fields.float('Quiet zone', digits=(16, 2), required=False),
        'bc_font_size': fields.integer('Font_size', required=False),
        'bc_text_distance': fields.float('Text distance', digits=(16, 2), required=False),
        'bc_background':fields.char('Background', size=64, required=False),
        'bc_foreground':fields.char('Foreground', size=64, required=False),
        'bc_text2':fields.char('Texto bajo la imagen', size=64, required=False),
        }

    def _get_logo(self, cr, uid, context={}):
        # photo_path = addons.get_module_resource('kemas', 'images', 'logo.png')
        # return open(photo_path, 'rb').read().encode('base64')
        return False
    
    def _get_system_logo(self, cr, uid, context={}):
        # photo_path = addons.get_module_resource('kemas', 'images', 'system_logo.png')
        # return open(photo_path, 'rb').read().encode('base64')
        return False

    _defaults = {
        'name_system' : 'Kemas 4D',
        'default_points' : 100,
        'default_attend_on_time_points' : 10,
        'default_late_points' : 20,
        'default_not_attend_points' : 40,
        'url_system' : 'http://127.0.0.1:8069',
        'number_replacements':5,
        #---Images and logos----------------------------
        'logo': _get_logo,
        'system_logo': _get_system_logo,
        #---
        'use_header_message_incorporation' : True,
        'use_header_message_event' : True,
        'use_header_message_event_completion' : True,
        'use_header_message_add_remove_points' : True,
        #---IM------------------------------------------
        'use_attachments_in_im':True,
        'use_subject_in_im':True,
        'use_message_im_incorporation':True,
        'use_message_im_event':True,
        
        'Message_im_information_incorporation':"""Hola %nk, 
Te informamos que tu registro en nuestro sistema ha sido completado. 
Porfavor revisa el correo que te mandamos a (%em) en el cual vas a encontrar más detalles.
        """,
        'Message_im_information_event':"""
<p align=justify>
Hola %nk,<br/> 
Te informamos que el d&iacute;a <b>%dy</b> a las <b>%te</b>, tienes que asistir al servicio: <b>%sr</b>. 
%ac
<p>
Recuerda que la hora de entrada es a las <u><b>%te</b></u> y tienes <u><b>%tr</b></u> minutos para registrar tu asistencia. 
<br/><br/><p align=justify><i>%in</i><p><br/>
Porfavor revisa el correo que te mandamos a <u>(%em)</u> en el cual vas a encontrar m&aacute;s detalles.
        """,
        #---Email---------------------------------------
        'default_not_attend_points' : 40,
        'reply_email':'notificaciones@kemas.com',
        'system_email':'notificaciones@kemas.com',
        'header_email' : '<img src="https://launchpadlibrarian.net/104796320/Logo%20100x100%20b.png" style="width: 100px; height: 100px;"/><br/>',
        'footer_email':u'''<hr/>
<font size="2" face="Georgia" color="gray">
<center>
<p>
Usted ha recibido este mensaje porque forma parte del equipo de colaboradores de Ke+Ministerio. Si usted cree esto es un error porfavor envie un correo a %se.
</p>
</center>
</font>''',
        #---Incorporation----------------------------------------------------------------------
        'use_message_incorporation':True,
        'Message_information_incorporation_subject':'[%na] Bienvenido',
        'Message_information_incorporation':'''
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te damos la bienvenida al equipo de colaboradores de Ke+ Ministerio.
<p>
<b>Datos con los que inicias:</b><br/>
<table>
<tr >
<td align="right"><b><font size="3" face="VIVIAN">Codigo:</font><b></td>
<td><font size="3" face="VIVIAN">%cd</font></td>
</tr>
<tr>
<td align="right"><b><font size="3" face="VIVIAN">Puntos:</font><b></td>
<td><font size="3" face="VIVIAN">%pt</font></td>
</tr>
<tr>
<td align="right"><b><font size="3" face="VIVIAN">Nivel:</font><b></td>
<td><font size="3" face="VIVIAN">%lv</font></td>
</tr>
</table>
<br/>
<p align=justify>
Puedes revisar revisar tu datos, actualizaciones de puntaje, calendario de eventos, repositorio, etc. En la página del sistema está dirección <b>%hs</b>, El Nombre de las Base de Datos a la que debes conectar es <b>%sd</b>. 
<br/><br/>
Tus credenciales para ingresar al sistema:
<br/>
<blockquote>
<table>
<tr >
<td align="right"><b><font size="3" face="Helvetica" color="#0174DF">Username:</font><b></td>
<td><font size="3" face="Helvetica" color="#0174DF">%us</font></td>
</tr>
<tr>
<td align="right"><b><font size="3" face="Helvetica" color="#0174DF">Password:</font><b></td>
<td><font size="3" face="Helvetica" color="#0174DF">%ps</font></td>
</table>
</blockquote>
</font>
<br/>
</p>
<i>
<p align=justify>
El manual de uso del sistema web está adjunto al correo.
</p>
</i>
''',
        #---Event------------------------------------------------------------------------------
        'work_in_background_event':True,
        'use_message_event':True,
        'Message_information_event_subject':'[%na] %sr||%ds %st',
        'Message_information_event':'''
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te informamos que el día <b>%dy</b> a las <b>%te</b>, tienes que asistir al servicio: <b>%sr</b>, este durará de <b>%st</b> a <b>%es</b>, lugar del servicio: <b>%sp</b>.
<br/>
%ac
<br/>
Recuerda que la hora de entrada es a las <b>%te</b> y tienes <b>%tr</b> minutos para registrar tu asistencia, para incrementar tus puntos deberás llegar a tiempo, caso contrario tus puntos seran restados, los puntos para este servicio se detallan a continuación:
<br/><br/>
• Tus puntos actualmente = <b>%pt</b>.<br/>
• Puntos que se restaran por atraso = <b>%lt</b>.<br/>
• Puntos que se restaran por inasistencia = <b>%ab</b>.<br/>
• Puntos que se agregaran por asistencia puntual = <b>%at</b>.
<br/><br/>
<i><p align=justify>%in<p></i>
<p>
</font>
<br/>
<i>
<p align=justify>
Para más infomación y consulta de tus datos da click <a href="%hs">aquí</a>.
</p>
</i>''',
        
        'use_event_completion':True,
        'use_im_event_completion':True,
        'message_event_completon_subject' : "[%na] %sr||%ds %st [FINALIZADO]",
        'message_event_completon_on_time': """
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te informamos que ha finalizado el servicio: <b>%sr</b>, programado para el día <b>%dy</b> a las <b>%te</b> en el <b>%sp</b>, ha terminado y registraste tu asistencia <b>puntualmente<b>. 
<br/><br/>
• Puntos Ganados = <b>%pe</b>.<br/>
• Tus puntos actualmente = <b>%pt</b>.<br/>
• Nivel actual = <b>%lv</b>.<br/>
<p>
</font>
<br/><br/>
<i>
<p align=justify>
Para más infomación y consulta de tus datos da click <a href="%hs">aquí</a>.
</p>
</i>
        """,
        'message_im_event_completon_on_time': """Hola %nk, 
Te informamos que ha finalizado el servicio: %sr, programado para el día %dy a las %te, ha terminado y registraste tu asistencia PUNTUALMENTE. 

• Puntos Ganados = %pe.
• Tus puntos actualmente = %pt.
• Nivel actual = %lv.        
        """,
        'message_event_completon_late': """
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te informamos que ha finalizado el servicio: <b>%sr</b>, programado para el día <b>%dy</b> a las <b>%te</b> en el <b>%sp</b>, ha terminado y <b>no registraste tu asistencia a tiempo<b>. 
<br/><br/>
• Puntos Perdidos = <b>%pl</b>.<br/>
• Tus puntos actualmente = <b>%pt</b>.<br/>
• Nivel actual = <b>%lv</b>.<br/>
<p>
</font>
<br/><br/>
<i>
<p align=justify>
Para más infomación y consulta de tus datos da click <a href="%hs">aquí</a>.
</p>
</i>
        """,
        'message_im_event_completon_late': """Hola %nk, 
Te informamos que ha finalizado el servicio: %sr, programado para el día %dy a las %te, ha terminado y NO REGISTRASTE TU ASISTENCIA a tiempo. 

• Puntos Perdidos = %pl.
• Tus puntos actualmente = %pt.
• Nivel actual = %lv.        
        """,
        'message_event_completon_absence': """
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te informamos que ha finalizado el servicio: <b>%sr</b>, programado para el día <b>%dy</b> a las <b>%te</b> en el <b>%sp</b>, ha terminado y <b>no registraste tu asistencia<b>. 
<br/><br/>
• Puntos Perdidos = <b>%pl</b>.<br/>
• Tus puntos actualmente = <b>%pt</b>.<br/>
• Nivel actual = <b>%lv</b>.<br/>
<p>
</font>
<br/><br/>
<i>
<p align=justify>
Para más infomación y consulta de tus datos da click <a href="%hs">aquí</a>.
</p>
</i>
        """,
        'message_im_event_completon_absence': """Hola %nk, 
Te informamos que ha finalizado el servicio: %sr, programado para el día %dy a las %te, ha terminado y NO REGISTRASTE TU ASISTENCIA. 

• Puntos Perdidos = %pl.
• Tus puntos actualmente = %pt.
• Nivel actual = %lv.        
        """,
        #---Massive email----------------------------------------------------------------------
        'send_IM_massive_email':True,
        'Message_information_massive_email':"""Hola %nk, 
Acabamos de enviarte un correo a (%em), no olvides revisarlo.
        """,
        'massive_mail_use_header': False,
        'massive_mail_body_default' : '''
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<!-- saved from url=(0056)http://www.themefuse.com/demo/html/TechOffers/index.html -->
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title></title> 
  </head>
  <body style="margin: 0; padding: 0; background-color: #464c58;" background="https://dl.dropboxusercontent.com/u/96556423/kemas/mail_backgrounds/components/dots.jpg">
    <table cellpadding="0" cellspacing="0" width="100%" height="100%" background="https://dl.dropboxusercontent.com/u/96556423/kemas/mail_backgrounds/components/dots.jpg" bgcolor="#464c58">
      <tbody>
        <tr>
          <td>
            <table align="center" cellpadding="0" cellspacing="0" width="720">
              <tbody>
                <tr>
                  <br/>
                  <!-- 
                  <td>
                    <table cellpadding="0" cellspacing="0" style="width: 720px; height: 105px;" align="center">
                      <tbody>
                        <tr>
                          <td width="58px"></td>
                          <td style="font-family: Georgia, &#39;Times New Roman&#39;, Times, serif; font-size: 32px; letter-spacing:-1px; color: #ffffff; padding-top:18px;">Bienvenido</td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                  -->
                </tr>
              
                <tr>
                  <td>
                    <table align="center" cellpadding="0" cellspacing="0">
                      <tbody>
                        <tr>
                          <td width="10px" height="100%"></td>
                          <td width="700px" height="16px" background="https://dl.dropboxusercontent.com/u/96556423/kemas/mail_backgrounds/components/top.gif"></td> 
                          <td style="width: 10px; height: 100%;"></td>
                        </tr>
                      </tbody>
                    </table>  
                    <!-- top -->
                  </td>
                </tr>
              
                <tr>
                  <td>
                    <table cellpadding="0" cellspacing="0" style="width: 720px; height: 87px;" align="center">
                      <tbody>
                        <tr>
                          <td width="10px" height="87px"></td>
                          <td width="700px" height="87px" background="https://dl.dropboxusercontent.com/u/96556423/kemas/mail_backgrounds/correo_masivo.jpg"></td>
                          <td width="10px" height="87px"></td>
                        </tr>
                      </tbody>
                    </table>
                    <!-- ribon -->
                  </td>
                </tr>
              
                <tr>
                  <td>
                    <table align="center" cellpadding="0" cellspacing="0">
                      <tbody>
                        <tr>
                          <td width="10px" height="100%"/>
                          <td width="640px" height="100%" bgcolor="#FFFFFF" style="padding-left: 33px; padding-right: 27px;">
                            <table cellpadding="0" cellspacing="0" style="margin-top:19px;">
                              <tbody>
                                <tr>
                                  <td width="640px" height="100%" bgcolor="#FFFFFF" style="padding-left: 33px; padding-right: 27px;">
                                    <h1 style="font-family:Georgia, &#39;Times New Roman&#39;, Times, serif; font-size:20px; letter-spacing:-1px; font-weight:normal; color:#202125; line-height:35px;">
                                      Saludos,
                                    </h1>
                                    <p style="font-family: georgia, serif; font-weight: normal; font-size: 15px; line-height: 20px; color: #595959; margin-top: 0; margin-left: 0; margin-bottom: 20px; margin-right: 0; padding: 0;" align="justify">
                                      [Cuepo del Correo]
                                    </p>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                            <!-- third set of offers -->  
                          </td>
                          <td style="width: 10px; height: 100%;"/>  
                        </tr>
                      </tbody>
                    </table>  
                <!-- third set of offers -->
              </td>
            </tr>
              
                <tr>
              <td>
                <table align="center" cellpadding="0" cellspacing="0">
                  <tbody>
                        <tr>
                      <td width="10px" height="100%"></td>
                      <td width="700px" height="16px" background="https://dl.dropboxusercontent.com/u/96556423/kemas/mail_backgrounds/components/bottom.gif"></td>  
                      <td style="width: 10px; height: 100%;"></td>
                        </tr>
                        <tr>
                          <td width="10px" height="100%"></td>
                          <td align="justify" style="padding-top:11px; padding-bottom:32px;">
                            <p style="font-family:Arial, Helvetica, sans-serif; font-size:11px; color:#ffffff; line-height:16px; text-align:center;">
                              Has recibido este mensaje del equipo de comunicaciones ke+.
                            </p>
                          </td> 
                          <td style="width: 10px; height: 100%;"></td>
                        </tr>
                  </tbody>
                    </table>  
                <!-- bottom and copyrights -->
              </td>
            </tr>
              </tbody>
            </table>
            <!-- newsletter -->
          </td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
        ''',
        #---Modificacion manual de puntos------------------------------------------------------------------------------
        'use_message_add_remove_points':True,
        'use_message_im_add_points':True,
        'use_message_im_remove_points':True,
        'Message_add_remove_points_subject':'[%na] Modificacion de puntos',
        'Message_add_points':'''
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te informamos que acabas de recibir <b>%mp</b>.
<br/>
<i><p align=justify>%ds<p></i>
<p>
</font>
<br/>
<i>
<p align=justify>
Para más infomación y consulta de tus datos da click <a href="%hs">aquí</a>.
</p>
</i>''',
        'Message_im_add_points':"""
Hola %nk,<br />
Acabas de recibir <b>%mp</b> puntos.
<p align="justify">
<i>%ds</i></p>
<p>
        """,
        'Message_remove_points':'''
<font size="3" face="Arial" color="green">
<b>Estimad%gn %nk,</b>
</font>
<font size="3" face="VIVIAN">
<br/>
<p align=justify>
Te informamos que acabas de perder <b>%mp</b>.
<br/>
<i><p align=justify>%ds<p></i>
<p>
</font>
<br/>
<i>
<p align=justify>
Para más infomación y consulta de tus datos da click <a href="%hs">aquí</a>.
</p>
</i>''',
        'Message_im_remove_points':"""
Hola %nk,<br />
Acabas de perder <b>%mp</b> puntos.
<p align="justify">
<i>%ds</i></p>
<p>
        """,
        #---QR Code----------------------------------------------------------------------------
        'qr_text':"""Código: %cd
Nombre: %cl
Nivel: %lv
Fecha de Ingreso al ministerio: %jd

%dt
        """,
        'qr_width':150,
        'qr_height':150,
        #---Bar Code----------------------------------------------------------------------------
        'bc_text': "%cd",
        'bc_type': "code128",
        'bc_module_width': 0.2,
        'bc_module_height': 15.0,
        'bc_quiet_zone': 6.5,
        'bc_font_size': 10,
        'bc_text_distance': 5.0,
        'bc_background': 'white',
        'bc_foreground': 'black',
        'bc_write_text': False,
        'bc_text2': '',
    }
    
    
    _sql_constraints = [
        ('config_name', 'unique (name_system)', 'This system name already exist!'),
        ('config_sequence', 'unique (sequence)', 'This sequence already exist!'),
        ]
    def validate_points(self, cr, uid, ids):
        value = self.read(cr, uid, ids[0], ['default_attend_on_time_points'])['default_attend_on_time_points']
        if int(value) < 1:return False
        value = self.read(cr, uid, ids[0], ['default_late_points'])['default_late_points']
        if int(value) < 1:return False
        value = self.read(cr, uid, ids[0], ['default_not_attend_points'])['default_not_attend_points']
        if int(value) < 1:return False
        value = self.read(cr, uid, ids[0], ['default_points'])['default_points']
        if int(value) < 1:return False        
        return True
    _constraints = [
        (validate_points, 'You can not enter values ​​less than 1 or leave the field empty.', ['default_points']),
        ]
class kemas_activity(osv.osv):
    def __name_get(self, cr, uid, ids, context={}):     
        if not len(ids):
            return[]
        reads = self.browse(cr, uid, ids, context)
        res = []
        for record in reads:   
            if context.get('no_name_get', False):
                if context['no_name_get']:   
                    name = (record.name)
                else:
                    name = (record.name + ' (' + unicode(record.area_id.name) + ')')
            else:
                name = (record.name + ' (' + unicode(record.area_id.name) + ')')
            res.append((record.id, name))
        return res
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context and context.has_key('collaborator_id'):
            if context['collaborator_id']:
                collaborator_obj = self.pool.get('kemas.collaborator')
                area_ids = collaborator_obj.read(cr, uid, context['collaborator_id'], ['area_ids'])['area_ids']
                result_ids = []
                for area_id in area_ids:
                    area_obj = self.pool.get('kemas.area')
                    activity_ids = area_obj.read(cr, uid, area_id, ['activity_ids'])['activity_ids']
                    for activity_id in activity_ids:
                        result_ids.append(activity_id)
                result_ids = list(set(result_ids))
                
                args.append(('id' , 'in', result_ids))
            else:
                args.append(('id' , 'in', []))
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    _order = 'name'
    _name = 'kemas.activity'
    _columns = {
        'area_id': fields.many2one('kemas.area', 'Area', required=True, help='Area to which belongs'),
        'name': fields.char('Name', size=64, required=True, help='The name of the activity'),
        'description': fields.text('Description', help='The description of the activity'),
        }
    _sql_constraints = [
        ('activity_name', 'unique (name,area_id)', 'This Activity already exist!'),
        ]
class kemas_team(osv.osv):
    def write(self, cr, uid, ids, vals, context={}):
        old_records = self.read(cr, uid, ids, ['responsible_ids'])
        result = super(kemas_team, self).write(cr, uid, ids, vals, context)
        records = self.read(cr, uid, ids, ['responsible_ids'])
        
        partner_obj = self.pool['res.partner']
        md_obj = self.pool['ir.model.data']
        md_ids = md_obj.search(cr, uid, [('name', '=', 'res_partner_category_resp_team')])
        cat_id = md_obj.read(cr, uid, md_ids[0], ['res_id'])['res_id']
        for record in records:
            if vals.get('logo', False):
                vals_write = {}
                vals_write['logo'] = extras.crop_image(vals['logo'], 192)
                vals_write['logo_medium'] = extras.crop_image(vals['logo'], 64)
                vals_write['logo_small'] = extras.crop_image(vals['logo'], 48)
                super(kemas_team, self).write(cr, uid, [record['id']], vals_write, context)
            # Poner etiqueta de responsable a los responsables
            partner_obj.write(cr, uid, record['responsible_ids'], vals={'category_id': [(4, cat_id)]})
            # En el caso de que se hayan quitado responsables se verifica si ya no son responsables de otros team se les quita la etiquetas
            for old_record in old_records:
                if old_record['id'] == record['id']:
                    del_partner_ids = list(set(old_record['responsible_ids']) - set(record['responsible_ids']))
                    for del_partner_id in del_partner_ids:
                        if not self.search(cr, uid, [('responsible_ids', 'in', del_partner_id)]):
                            partner = partner_obj.read(cr, uid, del_partner_id, ['category_id'])
                            if cat_id in partner['category_id']:
                                partner_obj.write(cr, uid, [partner['id']], vals={'category_id': [(3, cat_id)]})
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            vals['logo'] = extras.crop_image(vals['logo'], 192)
            vals['logo_medium'] = extras.crop_image(vals['logo'], 64)
            vals['logo_small'] = extras.crop_image(vals['logo'], 48)
        res_id = super(kemas_team, self).create(cr, uid, vals, context)
        
        # Poner etiqueta de responsable a los responsables
        if vals['responsible_ids']:
            md_obj = self.pool['ir.model.data']
            md_ids = md_obj.search(cr, uid, [('name', '=', 'res_partner_category_resp_team')])
            cat_id = md_obj.read(cr, uid, md_ids[0], ['res_id'])['res_id']
            self.pool['res.partner'].write(cr, uid, vals['responsible_ids'][0][2], vals={'category_id': [(4, cat_id)]})
        return res_id
    
    _order = 'name'
    _name = 'kemas.team'
    _columns = {
        'logo': fields.binary('Logo', help='The Team Logo.'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='The name of the Team'),
        'collaborator_ids': fields.one2many('kemas.collaborator', 'team_id', 'Collaborators', help='Collaborators to belong to this Team.', readonly=False),
        'responsible_ids': fields.many2many('res.partner', id1='team_id', id2='responsible_id', string='Responsables'),
        'description': fields.text('Description', help='The description of the Team'),
        }
    _sql_constraints = [
        ('team_name', 'unique (name)', "This Team already exist!"),
        ]
    
    def _get_logo(self, cr, uid, context={}):
        # photo_path = addons.get_module_resource('kemas', 'images', 'team.png')
        # return open(photo_path, 'rb').read().encode('base64')
        return False

    _defaults = {
        'logo': _get_logo,
    }
    
class kemas_school4d_detail(osv.osv):
    _order = 'datetime'
    _name = 'kemas.school4d_detail'
    _columns = {
        'line_id': fields.many2one('kemas.school4d_line', 'Person', required=True, ondelete="cascade"),
        'datetime': fields.datetime('Date', required=True),
        'description': fields.text('Description', required=True),
    }
    
    _defaults = {  
        'datetime': lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        }

class kemas_school4d_stage(osv.osv):    
    _name = 'kemas.school4d.stage'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Stage Name', required=True, size=64, translate=True),
        'sequence': fields.integer('Sequence'),
    }
    _defaults = {
        'sequence': 1
    }
    _order = 'sequence'
    
class kemas_school4d_line(osv.osv):
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('user_collaborator', False):
            collaborator_obj = self.pool.get('kemas.collaborator')
            collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
            args.append(('collaborator_id', 'in', collaborator_ids))
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def write(self, cr, uid, ids, vals, context={}):
        if vals.get('stage_id', False):
            stage_obj = self.pool.get('kemas.event.stage')
            stage = stage_obj.read(cr, uid, vals['stage_id'])
            if stage['sequence'] == 1:
                vals['state'] = 'listening'
            elif stage['sequence'] == 2:
                vals['state'] = 'believing'
            elif stage['sequence'] == 3:
                vals['state'] = 'preaching'
                
        
        return super(osv.osv, self).write(cr, uid, ids, vals, context)
    
    def create(self, cr, uid, vals, context={}):
        if context.get('user_collaborator', False):
            collaborator_obj = self.pool.get('kemas.collaborator')
            collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
            if collaborator_ids:
                vals['collaborator_id'] = collaborator_ids[0]
        return super(osv.osv, self).create(cr, uid, vals, context)
     
    def set_priority(self, cr, uid, ids, priority):
        """Set task priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, *args):
        """Set task priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set task priority to normal
        """
        return self.set_priority(cr, uid, ids, '2')
    
    def prev_stage(self, cr, uid, ids, context={}):
        prev_state = 'listening'
        state = self.read(cr, uid, ids[0], ['state'])['state']
        if state == 'preaching':
            prev_state = 'believing'
        elif state == 'believing':
            prev_state = 'listening'
        vals = {}
        vals['state'] = prev_state
        super(osv.osv, self).write(cr, uid, ids, vals)
        
    def next_stage(self, cr, uid, ids, context={}):
        next_state = 'listening'
        state = self.read(cr, uid, ids[0], ['state'])['state']
        if state == 'listening':
            next_state = 'believing'
        elif state == 'believing':
            next_state = 'preaching'
        vals = {}
        vals['state'] = next_state
        super(osv.osv, self).write(cr, uid, ids, vals)
    
    def get_age(self, cr, uid, ids, name, arg, context={}):
        def do(person_id):
            try:
                birth = super(osv.osv, self).read(cr, uid, person_id, ['birth'])['birth']
                age = extras.calcular_edad(birth)
                return age
            except: return ""
                
        result = {}
        for person_id in ids:
            result[person_id] = do(person_id)
        return result
    
    def on_change_birth(self, cr, uid, ids, birth, context={}):
        values = {}
        values['age'] = extras.calcular_edad(birth)
        return {'value':values}
    
    _order = 'name'
    _name = 'kemas.school4d_line'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', required=True, ondelete="cascade"),
        'photo': fields.binary('Photo', help='The photo of the person'),
        'name': fields.char('Name of person', size=64, required=True, help='Name of person you are discipling wing'),
        'details': fields.text('Details'),
        'detail_ids': fields.one2many('kemas.school4d_detail', 'line_id', 'Details'),
        'state': fields.selection([
            ('listening', 'Listening'),
            ('believing', 'Believing'),
            ('preaching', 'Preaching'),
            ], 'State', required=True),
        'mobile': fields.char('Mobile', size=10, help="The number of mobile phone of the person. Example: 088729345"),
        'email': fields.char('E-mail', size=128, help="The person email."),
        'web_site': fields.char('Web site', size=128, help="The web site of the person. example: Facebook account."),
        'address': fields.char('Address', size=255, help="The person address."),
        'birth': fields.date('Birth', help="Date of bith od the person."),
        'age': fields.function(get_age, type='char', string='Age'),

        'stage': fields.selection([
            ('listening', 'Listening'),
            ('believing', 'Believing'),
            ('preaching', 'Preaching'),
            ], 'Stage'),
        #-----KANBAN METHOD
        'priority': fields.selection([('4', 'Very Low'), ('3', 'Low'), ('2', 'Medium'), ('1', 'Important'), ('0', 'Very important')], 'Priority', select=True),
        'color': fields.integer('Color Index'),
        'stage_id': fields.many2one('kemas.school4d.stage', 'Stage'),
    }

    def _get_default_image(self, cr, uid, is_company, context={}, colorize=False):
        if is_company:
            image = open(openerp.modules.get_module_resource('base', 'static/src/img', 'company_image.png')).read()
        else:
            image = tools.image_colorize(open(openerp.modules.get_module_resource('kemas', 'images', 'avatar.png')).read())
        return tools.image_resize_image_big(image.encode('base64'))

    
    _defaults = {  
        'state': lambda *a: 'listening',
        'priority': '2',
        'stage_id': 1,
        'color':6,
        'photo': lambda self, cr, uid, ctx: self._get_default_image(cr, uid, ctx.get('default_is_company', False), ctx),
        }
    
    def _read_group_stage_id(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context={}):
        stage_obj = self.pool.get('kemas.school4d.stage')
        access_rights_uid = access_rights_uid or uid

        stage_ids = stage_obj.search(cr, uid, [('sequence', 'in', [1, 2, 3])])
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        return result

    _group_by_full = {
        'stage_id': _read_group_stage_id
    }
    
class kemas_area(osv.osv):
    def write(self, cr, uid, ids, vals, context={}):
        old_records = self.read(cr, uid, ids, ['responsible_ids'])
        result = super(kemas_area, self).write(cr, uid, ids, vals, context)
        records = self.read(cr, uid, ids, ['responsible_ids'])
        
        partner_obj = self.pool['res.partner']
        md_obj = self.pool['ir.model.data']
        md_ids = md_obj.search(cr, uid, [('name', '=', 'res_partner_category_resp_area')])
        cat_id = md_obj.read(cr, uid, md_ids[0], ['res_id'])['res_id']
        for record in records:
            if vals.get('logo', False):
                vals_write = {}
                vals_write['logo'] = extras.crop_image(vals['logo'], 192)
                vals_write['logo_medium'] = extras.crop_image(vals['logo'], 64)
                vals_write['logo_small'] = extras.crop_image(vals['logo'], 48)
                super(kemas_area, self).write(cr, uid, [record['id']], vals_write, context)
            # Poner etiqueta de responsable a los responsables
            partner_obj.write(cr, uid, record['responsible_ids'], vals={'category_id': [(4, cat_id)]})
            # En el caso de que se hayan quitado responsables se verifica si ya no son responsables de otros area se les quita la etiquetas
            for old_record in old_records:
                if old_record['id'] == record['id']:
                    del_partner_ids = list(set(old_record['responsible_ids']) - set(record['responsible_ids']))
                    for del_partner_id in del_partner_ids:
                        if not self.search(cr, uid, [('responsible_ids', 'in', del_partner_id)]):
                            partner = partner_obj.read(cr, uid, del_partner_id, ['category_id'])
                            if cat_id in partner['category_id']:
                                partner_obj.write(cr, uid, [partner['id']], vals={'category_id': [(3, cat_id)]})
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            vals['logo'] = extras.crop_image(vals['logo'], 192)
            vals['logo_medium'] = extras.crop_image(vals['logo'], 64)
            vals['logo_small'] = extras.crop_image(vals['logo'], 48)
        res_id = super(kemas_area, self).create(cr, uid, vals, context)
        
        # Poner etiqueta de responsable a los responsables
        if vals['responsible_ids']:
            md_obj = self.pool['ir.model.data']
            md_ids = md_obj.search(cr, uid, [('name', '=', 'res_partner_category_resp_area')])
            cat_id = md_obj.read(cr, uid, md_ids[0], ['res_id'])['res_id']
            self.pool['res.partner'].write(cr, uid, vals['responsible_ids'][0][2], vals={'category_id': [(4, cat_id)]})
        return res_id
    
    _order = 'name'
    _name = 'kemas.area'
    _columns = {
        'logo': fields.binary('Logo', help='El logotipo de Área'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Nombre', size=64, required=True, help='Nombre del Área'),
        'responsible_ids': fields.many2many('res.partner', id1='area_id', id2='responsible_id', string='Responsables'),
        'description': fields.text('Description', help='Una descripción del Área'),
        'history': fields.text('Historia'),
        'activity_ids': fields.one2many('kemas.activity', 'area_id', 'Actividades', help='Actividades relacionadas a ésta Ärea'),
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_collaborator_area_rel', 'area_id', 'collaborator_id', 'Colaboradores', help='colaboradores que pertenecen a esta Área'),
        }
    _sql_constraints = [
        ('area_name', 'unique (name)', "This Area already exist!"),
        ]
    def _get_logo(self, cr, uid, context={}):
        # photo_path = addons.get_module_resource('kemas', 'images', 'area.png')
        # return open(photo_path, 'rb').read().encode('base64')
        return False

    _defaults = {
        'logo': _get_logo,
    }
    
class kemas_level(osv.osv):
    def get_next_level(self, cr, uid, level_id):
        level_ids = self.search(cr, uid, [('previous_id', '=', level_id)])
        if level_ids:
            return level_ids[0]
            
    def get_order_levels(self, cr, uid):
        level_ids = self.search(cr, uid, [('first_level', '=', True)])
        if level_ids:
            first_level_id = level_ids[0]
            order_levels = []
            next_level = first_level_id
            while next_level != None:
                order_levels.append(next_level)
                next_level = self.get_next_level(cr, uid, next_level)
            return order_levels
        else:
            return None
    
    def name_get(self, cr, uid, ids, context={}):     
        if not len(ids):
            return[]
        reads = self.browse(cr, uid, ids, context)
        res = []
        for record in reads:   
            if context.get('points_of_level', False):
                name = u'''%s(%s %s)''' % (unicode(record.name), unicode(record.points), _("Points"))
            else:
                name = record.name
            res.append((record.id, name))
        return res
    
    def validate_points_zero(self, cr, uid, ids):
        level = self.read(cr, uid, ids[0], [])
        if level['points'] <= 0 and level['first_level'] == False:
            return False
        return True
            
    def validate_points(self, cr, uid, ids):
        level = self.read(cr, uid, ids[0], [])
        if level['first_level'] == False:
            try:
                previous_level_points = self.read(cr, uid, level['previous_id'][0], ['points'])['points']
                if int(level['points']) <= int(previous_level_points):
                    return False
            except:None
        return True
            
    def validate_unique_first_level(self, cr, uid, ids):
        firts_level = self.read(cr, uid, ids[0], ['first_level'])['first_level']
        if firts_level:
            level_ids = self.search(cr, uid, [('first_level', '=', True)])
            if len(level_ids) > 1:
                return False
        return True
    
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_level, self).write(cr, uid, ids, vals, context)
        for record_id in ids:
            if vals.get('logo', False):
                vals_write = {}
                vals_write['logo'] = extras.crop_image(vals['logo'], 192)
                vals_write['logo_medium'] = extras.crop_image(vals['logo'], 64)
                vals_write['logo_small'] = extras.crop_image(vals['logo'], 48)
                super(kemas_level, self).write(cr, uid, [record_id], vals_write, context)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            vals['logo'] = extras.crop_image(vals['logo'], 192)
            vals['logo_medium'] = extras.crop_image(vals['logo'], 64)
            vals['logo_small'] = extras.crop_image(vals['logo'], 48)
            
        if vals.get('first_level', False):
            vals['points'] = 0
        res_id = super(kemas_level, self).create(cr, uid, vals, context)
        self.pool.get('kemas.collaborator').update_collaborators_level(cr, uid)        
        return res_id
     
    _order = 'points'
    _name = 'kemas.level'
    _columns = {
        'logo': fields.binary('Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='Name of this level.'),
        'previous_id': fields.many2one('kemas.level', 'Previous Level', required=False, ondelete='restrict', help='Level that precedes this.'),
        'points': fields.integer('Points', help="Number of points required to reach this level."),
        'first_level': fields.boolean('Is first level?', help="This box must be checked if this is the first level."),
        'collaborator_ids': fields.one2many('kemas.collaborator', 'level_id', 'Levels', help='Collaborators found at this level'),
        'description': fields.text('Description'),
        }
    
    _constraints = [
        (validate_unique_first_level, 'There can be only one level set as the first level.', ['first_level']),
        (validate_points_zero, 'The points must be greater than zero.', ['points']),
        (validate_points, 'The points have to be higher than the previous level.', ['points']),
        ]
    
    _sql_constraints = [
        ('level_name', 'unique (name)', "This level's name already exist!"),
        ]

class kemas_collaborator_progress_level(osv.osv):
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=True, submenu=False):
        res = super(osv.osv, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)        
        collaborator_obj = self.pool.get('kemas.collaborator')
        level_obj = self.pool.get('kemas.level')
        collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
        xml = '''<form string="Progress">
                  <field name="percentaje" widget="progressbar" readonly="1" colspan="4" nolabel="1"/>
               </form>'''
        if collaborator_ids:
            collaborator = super(kemas_collaborator, collaborator_obj).read(cr, uid, collaborator_ids[0], ['points', 'level_id', ])
            #Cargar Datos-------------------------------------------------------------------
            current_level_id = collaborator['level_id'][0]
            current_level = level_obj.read(cr, uid, current_level_id, ['points', 'name'])
            current_level_points = current_level['points']
            current_level_name = current_level['name']
            
            next_level_id = level_obj.get_next_level(cr, uid, current_level_id)
            if next_level_id:
                next_level = level_obj.read(cr, uid, next_level_id, ['points', 'name'])
                Next_level_points = next_level['points']
                Next_level_name = next_level['name']
                
                xml = '''<form string="Progress">
                           <group colspan="4" expand="1" col="20">
                               <label string="%s" align="1" colspan="3"/>
                               <field name="percentaje" widget="progressbar" readonly="1" colspan="14" nolabel="1"/>
                               <label string="%s" align="0" colspan="3"/>
                           </group>
                       </form>''' % (current_level_name + ' [' + str(current_level_points) + ']', Next_level_name + ' [' + str(Next_level_points) + ']')
            else:
                xml = '''<form string="Progress">
                           <group colspan="4" expand="1" col="20">
                               <label string="" align="1" colspan="3"/>
                               <field name="percentaje" widget="progressbar" readonly="1" colspan="14" nolabel="1"/>
                               <label string="%s" align="0" colspan="3"/>
                           </group>
                       </form>''' % (current_level_name + ' [' + str(current_level_points) + ']')


        doc = etree.fromstring(xml.encode('utf8'))
        xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
        res['arch'] = xarch
        res['fields'] = xfields        
        res['type'] = 'form'
        return res
    
    def fields_get(self, cr, uid, fields=None, context={}, write_access=True): 
        collaborator_obj = self.pool.get('kemas.collaborator')
        level_obj = self.pool.get('kemas.level')
        result = super(kemas_collaborator_progress_level, self).fields_get(cr, uid, fields, context, write_access)
        def_dic = {}
        collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
        if collaborator_ids:
            collaborator = super(kemas_collaborator, collaborator_obj).read(cr, uid, collaborator_ids[0], ['points', 'level_id', ])
            #Cargar Datos-------------------------------------------------------------------
            next_level_id = level_obj.get_next_level(cr, uid, collaborator['level_id'][0])
            if next_level_id:
                next_level = level_obj.read(cr, uid, next_level_id, ['points'])
                percentaje = float(collaborator['points'] * 100) / float(next_level['points'])
                if percentaje < 0:
                    percentaje = 0
                if percentaje > 100:
                    percentaje = 100
                def_dic['percentaje'] = percentaje
            else:
                def_dic['percentaje'] = 100
        self._defaults = def_dic
        return result
    _name = 'kemas.collaborator.progress.level'
    _columns = {'percentaje': fields.float(''), }

class kemas_web_site(osv.osv):
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_web_site, self).write(cr, uid, ids, vals, context)
        for record_id in ids:
            if vals.get('logo', False):
                vals_write = {}
                vals_write['logo'] = extras.crop_image(vals['logo'], 192)
                vals_write['logo_medium'] = extras.crop_image(vals['logo'], 64)
                vals_write['logo_small'] = extras.crop_image(vals['logo'], 48)
                super(kemas_web_site, self).write(cr, uid, [record_id], vals_write, context)
            
            if vals.has_key('allow_get_avatar'):
                line_obj = self.pool.get('kemas.collaborator.web.site')
                line_ids = line_obj.search(cr, uid, [('web_site_id', '=', record_id)])
                
                vals = {'allow_get_avatar': vals['allow_get_avatar']}
                if not vals['allow_get_avatar']:
                    vals['get_avatar_from_website'] = False
                line_obj.write(cr, uid, line_ids, vals)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            vals['logo'] = extras.crop_image(vals['logo'], 192)
            vals['logo_medium'] = extras.crop_image(vals['logo'], 64)
            vals['logo_small'] = extras.crop_image(vals['logo'], 48)
        return super(kemas_web_site, self).create(cr, uid, vals, context)
    
    def on_change_allow_get_avatar(self, cr, uid, ids, allow_get_avatar, context={}):
        values = {}
        if not allow_get_avatar:
            values['get_avatar_method'] = False
        return {'value': values}

    _order = 'name'
    _name = 'kemas.web.site'
    _columns = {
        'logo': fields.binary('Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='The name of the Web Site'),
        'url': fields.char('URL', size=256, help='Web address.'),
        'line_ids': fields.one2many('kemas.collaborator.web.site', 'web_site_id', 'Collaborators'),
        'allow_get_avatar':fields.boolean(u'Permitir sincronizar datos', required=False, help=u"Indica si se pueden obtener datos está página por ejemplo la foto, esta opción es util con las redes sociales."),
        'get_avatar_method':fields.selection([
            ('facebook', 'facebook.com'),
            ('gravatar', 'Gravatar'),
             ], u'Método de obtención de la foto'),
        }
    _defaults = {  
        'url': 'https://www.'
        }

class kemas_suspension(osv.osv):
    def get_end_date(self, cr, uid, days, day1, day2, day3, day4, day5, day6, day7, context={}):
        from datetime import datetime
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        now = datetime.strptime(extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
        date_today = "%s-%s-%s" % (extras.completar_cadena(now.year, 4), extras.completar_cadena(now.month), extras.completar_cadena(now.day))
        
        days_str = {
                    'LUN':True,
                    'MAR':True,
                    'MIE':True,
                    'JUE':True,
                    'VIE':True,
                    'SAB':True,
                    'DOM':True
                    }
        if day1:
            days_str['LUN'] = True
        else:
            days_str['LUN'] = False
        
        if day2: 
            days_str['MAR'] = True
        else:
            days_str['MAR'] = False
            
        if day3: 
            days_str['MIE'] = True
        else:
            days_str['MIE'] = False
            
        if day4: 
            days_str['JUE'] = True
        else:
            days_str['JUE'] = False
            
        if day5: 
            days_str['VIE'] = True
        else:
            days_str['VIE'] = False
            
        if day6: 
            days_str['SAB'] = True
        else:
            days_str['SAB'] = False
            
        if day7: 
            days_str['DOM'] = True
        else:
            days_str['DOM'] = False
        
        workdays = []
        if days_str['LUN']:workdays.append('LUN')
        if days_str['MAR']:workdays.append('MAR')
        if days_str['MIE']:workdays.append('MIE')
        if days_str['JUE']:workdays.append('JUE')
        if days_str['VIE']:workdays.append('VIE')
        if days_str['SAB']:workdays.append('SAB')
        if days_str['DOM']:workdays.append('DOM')
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        return extras.get_end_date(date_today, int(days), tz, workdays=tuple(workdays))
    
    def lift(self, cr, uid, ids, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        vals = {
                'state': 'ended',
                'user_lift_id': uid,
                'date_lifted' : time.strftime("%Y-%m-%d %H:%M:%S")
                }
        self.write(cr, uid, ids, vals)
        suspensions = self.read(cr, uid, ids, ['collaborator_id'])
        collaborator_ids = []
        for suspension in suspensions:
            collaborator_ids.append(suspension['collaborator_id'][0])
            # Escribir una linea en la bitacora del Colaborador
            vals = {
                    'collaborator_id' : suspension['collaborator_id'][0],
                    'description' : 'Suspension Levantada',
                    'type' : 'info',
                    }
            self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals)
        vals = {
            'state':'Active'
            }
        super(kemas_collaborator, collaborator_obj).write(cr, uid, collaborator_ids, vals)
        
        
    def lift_by_collaborator(self, cr, uid, collaborator_id):
        suspension_ids = self.search(cr, uid, [('state', '=', 'on_going'), ('collaborator_id', '=', collaborator_id)])
        self.lift(cr, uid, suspension_ids)
        
    def lift_suspensions_expired(self, cr, uid, context={}):
        threaded_sending = threading.Thread(target=self._lift_suspensions_expired, args=(cr.dbname, uid))
        threaded_sending.start()
        
    def _lift_suspensions_expired(self, db_name, uid, context={}):
        from datetime import datetime
        db = pooler.get_db(db_name)
        cr = db.cursor()
        
        with Environment.manage():
            suspension_ids = self.search(cr, uid, [('state', '=', 'on_going')])
            suspensions = self.read(cr, uid, suspension_ids, ['date_end', 'collaborator_id'])
            count = 0
            for suspension in suspensions:
                tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
                now = datetime.strptime(extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
                end_suspension = datetime.strptime(suspension['date_end'], '%Y-%m-%d %H:%M:%S')
                date_start = now.date().__str__()
                date_end = end_suspension.date().__str__()         
                date_start = DateTime.strptime(date_start, '%Y-%m-%d')
                date_end = DateTime.strptime(date_end, '%Y-%m-%d')
                res = DateTime.Age (date_end, date_start)
                if res.days < 1:
                    self.lift_by_collaborator(cr, uid, suspension['collaborator_id'][0])
                    count += 1
            if count:
                print """\n
                         -------------------------------------------------------------------------------------------------------------------------
                         ***************************************************[%d] Suspensiones Levantadas**********************************************
                         -------------------------------------------------------------------------------------------------------------------------\n""" % (count)
            cr.commit()
    
    def _get_days_remaining(self, cr, uid, ids, name, arg, context={}): 
        def get_days_remaining(collaborator):
            if suspension['state'] == 'on_going':
                from datetime import datetime
                tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
                now = datetime.strptime(extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
                end_suspension = datetime.strptime(suspension['date_end'], '%Y-%m-%d %H:%M:%S')    
                date_start = now.date().__str__()
                date_end = end_suspension.date().__str__()                
                date_start = DateTime.strptime(date_start, '%Y-%m-%d')
                date_end = DateTime.strptime(date_end, '%Y-%m-%d')
                res = DateTime.Age (date_end, date_start)
                return str(res.days)
            else:
                return '0 días'

        result = {}
        suspensions = super(osv.osv, self).read(cr, uid, ids, ['id', 'state', 'date_end'])
        for suspension in suspensions:
            result[suspension['id']] = get_days_remaining(suspension)
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('user_collaborator', False):
            collaborator_obj = self.pool.get('kemas.collaborator')
            collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
            args.append(('collaborator_id', 'in', collaborator_ids))
        
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_create', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date_create', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['state'] = vals.get('state', 'on_going')
        vals['date_create'] = vals.get('date_create', time.strftime("%Y-%m-%d %H:%M:%S")) 
        vals['user_create_id'] = uid
        return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
     
    def name_get(self, cr, uid, ids, context={}):
        records = self.read(cr, uid, ids, ['id', 'collaborator_id', 'date_create'])
        res = []
        for record in records:
            name = "%s - %s" % (record['collaborator_id'][1], str(record['date_create'][:10]))
            res.append((record['id'], name))  
        return res
    
    _rec_name = 'collaborator_id'
    _name = 'kemas.suspension'
    _order = 'date_create DESC'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', required=True, help='Collaborator who underwent the suspension'),
        'date_create': fields.datetime('Date create', help='Date the collaborator was suspended'),
        'date_lifted': fields.datetime('Date lifted', help='Date suspension lifted her collaborator'),
        'date_end': fields.datetime('Date end', help='The date the suspension ends'),
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        'days_remaining': fields.function(_get_days_remaining, type='char', string='Days remaining', help='Days remaining to end the suspension'),
        'description': fields.text('Description'),
        'state': fields.selection([
            ('on_going', 'On going'),
            ('ended', 'Ended'),
            ], 'State'),
        'user_create_id': fields.many2one('res.users', 'Create by', help='The user who suspended the collaborador.'),
        'user_lift_id': fields.many2one('res.users', 'Lifted by', help='User who lifted the suspension to collaborator'),
        }

class kemas_collaborator_web_site(osv.osv):
    def sync(self, cr, uid, ids, context={}):
        wsline = self.read(cr, uid, ids[0], [])
        if not wsline['get_avatar_from_website']:
            return False
        web_site = self.pool.get('kemas.web.site').read(cr, uid, wsline['web_site_id'][0], ['allow_get_avatar', 'get_avatar_method'])
        if not web_site['allow_get_avatar']:
            return False
        
        vals = {}
        if web_site['get_avatar_method'] == 'facebook':
            profile = extras.get_facebook_info(wsline['url'], 'large')
            if profile:
                if profile.get('photo'):
                    vals['photo'] = profile['photo']
                if profile.get('gender'):
                    if profile['gender'] == 'male':
                        vals['gender'] = 'Male'
                    else:
                        vals['gender'] = 'Female'
        elif web_site['get_avatar_method'] == 'gravatar':
            photo = extras.get_avatar(wsline['url'], 120)
            if photo:
                vals['photo'] = photo
        
        result = False
        if vals:
            result = self.pool.get('kemas.collaborator').write(cr, uid, [wsline['collaborator_id'][0]], vals)
        return result
        
    def reload_info(self, cr, uid, ids, context={}):
        if self.sync(cr, uid, ids, context):    
            wsline = self.read(cr, uid, ids[0], []) 
            return {   
                    'res_id' : wsline['collaborator_id'][0],
                    'context': "{}",
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'kemas.collaborator',
                    'type': 'ir.actions.act_window',
                   }
        else:
            return False
    
    def on_change_web_site_id(self, cr, uid, ids, web_site_id, context={}):
        values = {}
        web_site_obj = self.pool.get('kemas.web.site')
        try:
            url = web_site_obj.read(cr, uid, web_site_id, ['url'])['url']
            if url:
                values['url'] = str(url) + '/'
        except: None
        
        values['allow_get_avatar'] = False
        if web_site_id:
            values['allow_get_avatar'] = web_site_obj.read(cr, uid, web_site_id, ['allow_get_avatar'])['allow_get_avatar']
        
        return {'value': values}
    
    _order = 'web_site_id'
    _rec_name = 'url'
    _name = 'kemas.collaborator.web.site'
    _columns = {
        'web_site_id': fields.many2one('kemas.web.site', 'Web Site'),
        'collaborator_id': fields.many2one('kemas.collaborator', 'collaborator', required=True),
        'url': fields.char('URL o E-mail', size=256, required=True, help='Web address.'),
        'get_avatar_from_website':fields.boolean(u'Sincronizar datos', required=False),
        'allow_get_avatar':fields.boolean(u'Permitir sincronizar datos', required=False, help=u"Indica Si se van a sincronizar datos con esta cuenta por ejemplo la foto, esta opción es util con las redes sociales."),
        }
    _defaults = {  
        'url': 'http://www.'
        }
    _sql_constraints = [
            ('u_web_site', 'unique (web_site_id,collaborator_id)', 'Ya se ha registrado una cuenta relaicionado a este sitio web!'),
            ]
    
    def _validate_unique_sync_account(self, cr, uid, ids): 
        """
        Esta funcion verifica: Que un colaborador solo pueda tener una sola cuenta para sincronizar datos.
        @return: Si la validacion es correctar de vuelve True caso contrario False y se revierte el proceso de Guardado.
        """
        def validate_unique_sync_account(record):
            wsline_ids = self.search(cr, uid, [('collaborator_id', '=', record['collaborator_id'][0]), ('get_avatar_from_website', '=', True)])
            if len(wsline_ids) > 1:
                return False
            else:
                return True
            
        records = self.read(cr, uid, ids, ['collaborator_id'])
        for record in records:
            if not validate_unique_sync_account(record):
                return False
        return True
    
    _constraints = [(_validate_unique_sync_account, u'\n\nSolo se puede usar una sola cuenta para sincronizar datos.', [u'Sitios web']), ]
    
class kemas_collaborator_logbook(osv.osv):
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['date'] = vals.get('date', time.strftime("%Y-%m-%d %H:%M:%S"))
        vals['user_id'] = uid
        return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
     
    _name = 'kemas.collaborator.logbook'
    _order = 'date Desc'
    _columns = {
        'date': fields.datetime('Date'),
        'user_id': fields.many2one('res.users', 'User', help='User who perform this transaction'),
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator'),
        'description': fields.char('Description', size=1000),
        'type': fields.selection([
            ('info', 'Information'),
            ('important', 'Important'),
            ('low_importance', 'Low importance'),
            ('bad', 'Bad'),
             ], 'Type'),
        }

class kemas_skill(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def _get_collaborators(self, cr, uid, ids, name, arg, context={}): 
        def get_collaborators(skill_id):
            skill_line_obj = self.pool['kemas.skill.line']
            
            skill_line_ids = skill_line_obj.search(cr, uid, [('skill_id', '=', skill_id)])
            skill_lines = skill_line_obj.read(cr, uid, skill_line_ids, ['collaborator_id'])
            
            collaborator_ids = []
            for skill_line in skill_lines:
                collaborator_ids.append(skill_line['collaborator_id'][0])
            return collaborator_ids
             
        result = {}
        for record_id in ids:
            result[record_id] = get_collaborators(record_id)
        return result
    
    _name = 'kemas.skill'
    _columns = {
        'name': fields.char('Nombre', size=64, required=True),
        'active': fields.boolean('Active', required=False, help='Indicates whether this place is active or not'),
        'collaborator_ids' : fields.function(_get_collaborators, type='many2many', relation="kemas.collaborator", string='collaborator'),
        }
    _sql_constraints = [
        ('u_name', 'unique (name)', u'¡Este nombre ya existe!'),
        ]
    _defaults = {  
        'active': True 
        }

class kemas_skill_line(osv.osv):
    _name = 'kemas.skill.line'
    _columns = {
        'skill_id':fields.many2one('kemas.skill', 'Habilidad', required=True),
        'collaborator_id':fields.many2one('kemas.collaborator', 'Colaborador', required=True),
        'description': fields.text(u'Descripción'),
        }
    _sql_constraints = [
        ('u_skill_line', 'unique (skill_id,collaborator_id)', u'¡Esta habilidad ya se le registro a este colaborador!'),
        ]
    _defaults = {  
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        }    

class kemas_collaborator(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        vals = {
                'state':'Active',
                'end_service': False
                }
        collaborators = self.read(cr, uid, ids, ['user_id', 'state', 'type'])
        for collaborator in collaborators:
            if collaborator['state'] in ['Active']:
                continue
            if not super(kemas_collaborator, self).write(cr, uid, [collaborator['id']], vals):
                continue
            #Inactivar usuario----------------------------------------------------------------------------------------
            if collaborator['user_id']:
                self.pool.get('res.users').write(cr, uid, [collaborator['user_id'][0]], {'active': True})
            # Escribir una linea en la bitacora del Colaborador
            vals_log = {
                    'collaborator_id' : collaborator['id'],
                    'description' : 'Colaborador Activado.',
                    'type' : 'info',
                    }
            self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals_log)
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        vals = {
                'state':'Inactive',
                'end_service' : extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
                }
        collaborators = super(kemas_collaborator, self).read(cr, uid, ids, ['user_id', 'state', 'type'])
        for collaborator in collaborators:
            if collaborator['state'] in ['Inactive']:
                continue
            if not super(kemas_collaborator, self).write(cr, uid, [collaborator['id']], vals):
                continue
            #Inactivar usuario----------------------------------------------------------------------------------------
            if collaborator['user_id']:
                self.pool.get('res.users').write(cr, uid, [collaborator['user_id'][0]], {'active': False})
            # Escribir una linea en la bitacora del Colaborador
            vals_log = {
                    'collaborator_id' : collaborator['id'],
                    'description' : 'Colaborador Inactivado.',
                    'type' : 'bad',
                    }
            self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals_log)
        return True
    
    def get_partner_id(self, cr, uid, collaborator_id):
        user_id = super(osv.osv, self).read(cr, uid, collaborator_id, ['user_id'])['user_id'][0]
        return self.pool.get('res.users').read(cr, uid, user_id, ['partner_id'])['partner_id'][0]

    def get_nick_name(self, cr, uid, collaborator_id):
        res = self.name_get(cr, uid, [collaborator_id])
        return res[0][1]
        
    def name_get(self, cr, uid, ids, context={}):
        if type(ids).__name__ == 'int': 
            ids = [ids]
        if not len(ids):
            return [] 
        fields = ['id', 'nick_name', 'last_names']
        if context.get('show_replacements', False):
            replacements_word = self.pool.get('kemas.func').get_translate(cr, uid, _('replacements available'))[0]
            fields.append('replacements')
        records = super(osv.osv, self).read(cr, uid, ids, fields)
        res = []
        for record in records:
            nick_name = unicode(record['nick_name']).title()
            apellido = unicode(extras.do_dic(record['last_names'])[0]).title()
            if context.get('show_replacements', False):
                name = u'''%s %s (%d %s)''' % (nick_name, apellido, record['replacements'], replacements_word)
            else:
                name = u'''%s %s''' % (nick_name, apellido)
            res.append((record['id'], name))
        return res
    
    def on_change_partner_id(self, cr, uid, ids, partner_id, first_names, last_names, state, context={}):
        values = {}
        if partner_id:
            if not first_names or not last_names or state in ['creating']:
                fields_partner = ['name', 'image', 'street', 'street2', 'city', 'state_id', 'country_id', 'phone', 'fax', 'mobile', 'email']
                partner = self.pool['res.partner'].read(cr, uid, partner_id, fields_partner)
                values['first_names'], values['last_names'] = extras.get_short_name(partner['name'])
                values.update({
                               'street': partner['street'],
                               'street2': partner['street2'],
                               'city': partner['city'],
                               'state_id': partner['state_id'] and partner['state_id'][0],
                               'country_id': partner['country_id'] and partner['country_id'][0],
                               'phone': partner['phone'],
                               'fax': partner['fax'],
                               'mobile': partner['mobile'],
                               'email': partner['email'],
                               })
                if partner['image']:
                    values['photo'] = partner['image']          
        return {'value': values}
    
    def on_change_first_names(self, cr, uid, ids, first_names, last_names, context={}):
        values = {}
        if first_names:
            dic_name = extras.do_dic(first_names)
            if dic_name:
                values['nick_name'] = unicode(dic_name[0]).title()
                values['first_names'] = extras.elimina_tildes(first_names).title()
        
        if first_names and last_names:
            first_names = extras.elimina_tildes(first_names).title()
            last_names = extras.elimina_tildes(last_names).title()
            values['name'] = "%s %s" % (first_names, last_names)
        return {'value': values}
    
    def on_change_state_id(self, cr, uid, ids, country_id, state_id, context={}):
        values = {}
        if not country_id and state_id:
            state_obj = self.pool['res.country.state']
            state = state_obj.read(cr, uid, state_id, ['country_id'])
            values['country_id'] = state['country_id'][0]
        return {'value': values}
    
    def on_change_born_state(self, cr, uid, ids, country_id, state_id, context={}):
        values = {}
        if not country_id and state_id:
            state_obj = self.pool['res.country.state']
            state = state_obj.read(cr, uid, state_id, ['country_id'])
            values['born_country'] = state['country_id'][0]
        return {'value': values}
    
    def on_change_last_names(self, cr, uid, ids, first_names, last_names, context={}):
        values = {}
        if last_names:
            values['last_names'] = extras.elimina_tildes(last_names).title()
        
        if first_names and last_names:
            first_names = extras.elimina_tildes(first_names).title()
            last_names = extras.elimina_tildes(last_names).title()
            values['name'] = "%s %s" % (first_names, last_names)
        return {'value': values}
    
    def on_change_nick_name(self, cr, uid, ids, first_name, nick_name, context={}):
        values = {}
        warning = {}
        if first_name and nick_name:
            first_name = unicode(first_name).lower().strip()
            nick_name = unicode(nick_name).lower().strip()
            if nick_name in first_name:
                values['nick_name'] = extras.elimina_tildes(nick_name).upper()
            else:
                warning = {'title' : u'¡Advertencia!', 'message' : u'El nombre de pila debe esta contenido en los nombres.'}
        return {'value': values , 'warning': warning}
    
    def on_change_email(self, cr, uid, ids, email, context={}):
        values = {}
        warning = {}
        if email:
            email = unicode(email).lower().replace(' ', '')
            if not extras.validate_mail(email):
                values['email'] = False
                warning = {'title' : '¡Advertencia!', u'message' : u'Formato de correo electrónico no válido'}
            else:
                values['email'] = email
        return {'value': values , 'warning': warning}            
    
    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        res = super(osv.osv, self).read(cr, uid, ids, fields, context)
        if fields is None or not list(set(['photo', 'photo_medium', 'photo_small', 'photo_very_small']) & set(fields)):
            return res
          
        '''
        user_obj = self.pool.get('res.users')
        group_obj = self.pool.get('res.groups')
        user_id = user_obj.search(cr, uid, [('id', '=', uid), ])
        groups_id = user_obj.read(cr, uid, user_id, ['groups_id'])[0]['groups_id']
        #---Validar si esque el usuario puede este registro----------------------------------------------------
        try:
            if type(context).__name__ == 'dict':
                if not 1 in groups_id:
                    kemas_collaborator_id = group_obj.search(cr, uid, [('name','=', 'Kemas / Collaborator'),])[0]
                    if kemas_collaborator_id in groups_id: 
                        collaborator_ids = super(osv.osv,self).search(cr, uid, [('user_id','=',uid)])
                        if not res[0]['id'] in collaborator_ids:  
                            if context.get('all_collaborators',False)==False:
                                for key in res[0]:
                                    if key != 'id' and key != 'photo': res[0][key]=False
        except:None
        '''
        #--------FOTO----------------------------
        photo_field = False
        if 'photo' in fields:
            photo_field = 'photo'
        elif 'photo_medium' in fields:
            photo_field = 'photo_small'
        elif 'photo_small' in fields:
            photo_field = 'photo_small'
            
        if photo_field:
            if type(res).__name__ == 'list':
                for read_dict in res:
                    collaborator = super(osv.osv, self).read(cr, uid, read_dict['id'], ['gender'])
                    if read_dict.has_key(photo_field):
                        if read_dict[photo_field] == False:
                            if collaborator['gender'] == 'Male':
                                read_dict[photo_field] = self.get_photo_male()
                            else:
                                read_dict[photo_field] = self.get_photo_female()
                        else:
                            continue
                    else:
                        if collaborator['gender'] == 'Male':
                            read_dict[photo_field] = self.get_photo_male()
                        else:
                            read_dict[photo_field] = self.get_photo_female()
            else:
                collaborator = super(osv.osv, self).read(cr, uid, ids, ['gender'])
                if res.has_key(photo_field):
                    if res[photo_field] == False:
                        if collaborator['gender'] == 'Male':
                            res[photo_field] = self.get_photo_male()
                        else:
                            res[photo_field] = self.get_photo_female()               
                else:
                    if collaborator['gender'] == 'Male':
                        res[photo_field] = self.get_photo_male()
                    else:
                        res[photo_field] = self.get_photo_female()
        
        #--------FOTO Para la VISTA DE KANBAN----------------------------
        elif 'photo_medium' in fields:
            if type(res).__name__ == 'list':
                for read_dict in res:
                    collaborator = super(osv.osv, self).read(cr, uid, read_dict['id'], ['gender'])
                    if read_dict.has_key('photo_medium'):
                        if read_dict['photo_medium'] == False:
                            if collaborator['gender'] == 'Male':
                                read_dict['photo_medium'] = self.get_photo_small_male()
                            else:
                                read_dict['photo_medium'] = self.get_photo_small_female()
                        else:
                            continue
                    else:
                        if collaborator['gender'] == 'Male':
                            read_dict['photo_medium'] = self.get_photo_small_male()
                        else:
                            read_dict['photo_medium'] = self.get_photo_small_female()
            else:
                collaborator = super(osv.osv, self).read(cr, uid, ids, ['gender'])
                if res.has_key('photo_medium'):
                    if res['photo_medium'] == False:
                        if collaborator['gender'] == 'Male':
                            res['photo_medium'] = self.get_photo_small_male()
                        else:
                            res['photo_medium'] = self.get_photo_small_female()               
                else:
                    if collaborator['gender'] == 'Male':
                        res['photo_medium'] = self.get_photo_small_male()
                    else:
                        res['photo_medium'] = self.get_photo_small_female()
        return res 

    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        if args is None or not args or not isinstance(args, (list)): args = []
        
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        collaborator_except_ids = []
        if context.get('min_points', False):
            args.append(('points', '>', context['min_points']))
        
        if context.get('except_ids', False):
            if type(context['except_ids']).__name__ == 'str':
                collaborator_except_ids += eval(context['except_ids'])
            else:
                collaborator_except_ids += context.get('except_ids', [])
        
        if context.get('event_collaborator_line_ids', False):
            try:
                collaborator_ids = []
                line_ids = eval(context['event_collaborator_line_ids'])
                for line in line_ids:
                    collaborator_ids.append(line[2]['collaborator_id'])
                collaborator_except_ids += collaborator_ids
            except: 
                try:
                    collaborator_ids = []
                    coll_line_ids = []
                    line_obj = self.pool.get('kemas.event.collaborator.line')
                    line_ids = eval(context['event_collaborator_line_ids'])
                    for line in line_ids:
                        if line[1] and type(line[1]).__name__ in ['int', 'long'] :
                            coll_line_ids.append(line[1])
                    colls = line_obj.read(cr, uid, coll_line_ids, ['collaborator_id'])
                    for coll in colls:
                        collaborator_ids.append(coll['collaborator_id'][0])
                    collaborator_except_ids += collaborator_ids
                except: 
                    try:
                        collaborator_ids = []
                        line_ids = eval(context['event_collaborator_line_ids'])
                        for line in line_ids:
                            collaborator_ids.append(int(line['collaborator_id'][0]))
                        collaborator_except_ids += collaborator_ids
                    except:
                        None
            
        if collaborator_except_ids:
            args.append(('id', 'not in', collaborator_except_ids))
        
        if context.get('user_collaborator', False):
            args.append(('state', 'in', ['Active', 'Suspended']))
            
        if context.has_key('birthday'):
            if context['birthday']:
                args = []
                desde = time.strftime("%Y-%m-") + '01'
                hasta = time.strftime("%Y-%m-") + unicode(extras.dias_de_este_mes())
                args.append(('birthday', '>=', desde))       
                args.append(('birthday', '<=', hasta))       
        
        if context.get('event_id', False):
            event_line_obj = self.pool.get('kemas.event.collaborator.line')
            search_args = [('event_id', '=', context['event_id'])]
            if context.get('exclude_replaceds', False):
                search_args.append(('replacement_id', '=', False))
                search_args.append(('replacement_id', '=', False))
            line_ids = event_line_obj.search(cr, uid, search_args)
            lines = event_line_obj.read(cr, uid, line_ids)
            event_collaborator_ids = []
            for line in lines:
                event_collaborator_ids.append(line['collaborator_id'][0])
            args.append(('id', 'in', event_collaborator_ids))
            
        use_ilike = False
        for arg in args:
            if unicode("'name', 'ilike'") in unicode(arg):
                use_ilike = True
                nick_name = arg[2]
                break
        if use_ilike:   
            nick_name_words = extras.do_dic(nick_name)
            my_args = []
            for nick_name_word in nick_name_words:
                my_args.append(('name', 'ilike', '%s' % unicode(nick_name_word)))
            res_ids_1 = super(osv.osv, self).search(cr, uid, my_args + args)
            res_ids_2 = super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
            result = list(set(res_ids_1) | set(res_ids_2))
            return result
        else:
            return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        
    def lift_suspension(self, cr, uid, ids, context={}):
        self.pool.get('kemas.suspension').lift_by_collaborator(cr, uid, ids[0])
        
    def suspend(self, cr, uid, ids, date_end, description, task_id=False):
        threaded_sending = threading.Thread(target=self._suspend, args=(cr.dbname, uid, ids, date_end, description, task_id))
        threaded_sending.start()
        
    def _suspend(self, db_name, uid, ids, date_end, description, task_id=False):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        def process(collaborator_id, description, date_end):
            vals = {
                     'text_suspension' : description,
                     'end_suspension': date_end,
                     'state' : 'Suspended'
                     }
            collaborator_obj = self.pool.get('kemas.collaborator')
            super(kemas_collaborator, collaborator_obj).write(cr, uid, [collaborator_id], vals)
            # Crear suspension
            suspension_obj = self.pool.get('kemas.suspension')
            vals = {
                   'collaborator_id' : collaborator_id,
                   'date_end' : date_end,
                   'description' : description
                   }
            if task_id:
                vals['task_assigned_id'] = task_id
            suspension_obj.create(cr, uid, vals)
            # Escribir una linea en la bitacora del Colaborador
            vals = {
                    'collaborator_id' : collaborator_id,
                    'description' : 'Suspendido: %s' % description,
                    'type' : 'bad',
                    }
            self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals)
        
        with Environment.manage():
            for collaborator_id in ids:
                process(collaborator_id, description, date_end)
            cr.commit()
            
    def add_remove_points(self, cr, uid, ids, points, description, type='increase'):
        threaded_sending = threading.Thread(target=self._add_remove_points, args=(cr.dbname, uid, ids, points, description, type))
        threaded_sending.start()
        
    def _add_remove_points(self, db_name, uid, ids, points, description, type='increase'):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        config_obj = self.pool.get('kemas.config')
        def change(collaborator_id, points, description, type):
            current_points = super(osv.osv, self).read(cr, uid, collaborator_id, ['points'])['points']
            suspend_collaborator = int(points)
            
            operator = '-'
            if type == 'add': 
                type = 'increase'
            if type == 'remove': 
                type = 'decrease'
            
            if type == 'increase':
                operator = '+'
                new_points = current_points + suspend_collaborator
            else:
                operator = '-'
                new_points = current_points - suspend_collaborator
                points = points * -1
            
            #----Escribir el historial de puntos-----------------------------------------------------
            history_points_obj = self.pool.get('kemas.history.points')
            change_points = suspend_collaborator
            current_points = str(current_points)
            
            summary = str(operator) + str(change_points) + " Puntos. Antes " + str(current_points) + " ahora " + str(new_points) + " Puntos."
            
            # Obtener el Codigo para crear el registro de Historial de Puntos
            seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas History Points'), ])[0]
            vals_1 = {
                    'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    'collaborator_id': collaborator_id,
                    'type': unicode(type),
                    'description': description,
                    'summary': summary,
                    'points': points,
                    'code' : unicode(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
                    }
            
            vals_2 = {
                    'points':new_points
                    }
            error = True
            while error:
                try:
                    cr.commit()
                    history_points_obj.create(cr, uid, vals_1)
                    cr.commit()
                    self.write(cr, uid, [collaborator_id], vals_2)
                    error = False
                except:
                    error = True
            config_obj.send_email_add_remove_points(cr, uid, collaborator_id, description, points, type, {})
        
        with Environment.manage():
            for collaborator_id in ids:
                change(collaborator_id, points, description, type)
            cr.commit()        
            
    def send_join_notification(self, cr, uid):
        threaded_sending = threading.Thread(target=self._send_join_notification, args=(cr.dbname , uid))
        threaded_sending.start()
    
    def _send_join_notification(self, db_name, uid):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        with Environment.manage():
            collaborator_ids = super(osv.osv, self).search(cr, uid, [('notified', 'in', ['no_notified'])])
            count = 0
            for collaborator_id in collaborator_ids:
                count += 1
                self.send_notification(cr, uid, collaborator_id, context={})
            if count > 0:
                _logger.info('[%d] Correo de registro enviados', count)
            cr.commit()
        
    def update_collaborators_level(self, cr, uid):
        threaded_sending = threading.Thread(target=self._update_collaborators_level, args=(cr.dbname , uid))
        threaded_sending.start()
        
    def _update_collaborators_level(self, db_name, uid):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        with Environment.manage():
            collaborator_ids = super(osv.osv, self).search(cr, uid, [])
            collaborators = super(osv.osv, self).read(cr, uid, collaborator_ids, ['id', 'points'])
            for collaborator in collaborators:
                level_id = self.get_corresponding_level(cr, uid, int(collaborator['points']))
                if level_id:
                    vals = {'level_id': level_id}
                    super(osv.osv, self).write(cr, uid, [collaborator['id']], vals)
            _logger.info(u'Actualización de nivel realizada')
            cr.commit()
          
    def get_corresponding_level(self, cr, uid, points):
        level_obj = self.pool.get('kemas.level')
        level_ids = level_obj.get_order_levels(cr, uid)
        if not level_ids:
            raise osv.except_osv(u'¡Advertencia!', u"No se han definido los Niveles en las configuraciones.")
        
        first_level_ids = level_obj.search(cr, uid, [('first_level', '=', True)])
        corresponding_level = None
        if first_level_ids:
            corresponding_level = first_level_ids[0]
        for level_id in level_ids:
            level_points = level_obj.read(cr, uid, level_id, ['points'])['points']
            if int(points) >= int(level_points):
                corresponding_level = level_id
        return corresponding_level
    
    def unlink(self, cr, uid, ids, context={}):
        users_obj = self.pool.get('res.users')
        partner_obj = self.pool.get('res.partner')
        records = self.read(cr, uid, ids, ['user_id', 'type', 'state', 'name_with_nick_name'])
        for record in records:
            if record['state'] in ['Active']:
                raise osv.except_osv(u'¡Error!', u'No se puede borrar a "' + record['name_with_nick_name'] + u'" porque aún esta en estado activo.')
            
            if not record['user_id']:
                continue
            user_id = super(osv.osv, self).read(cr, uid, record['id'], ['user_id'])['user_id'][0]
            partner = users_obj.read(cr, uid, user_id, ['partner_id'])['partner_id']
            users_obj.unlink(cr, uid, [user_id])
            if partner:
                partner_obj.unlink(cr, uid, [partner[0]])
        return super(kemas_collaborator, self).unlink(cr, uid, ids, context)
    
    def _send_notification(self, db_name, uid, collaborator_id):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        with Environment.manage():
            config_obj = self.pool.get('kemas.config')
            if config_obj.send_email_incoporation(cr, uid, collaborator_id):
                vals = {'notified':'notified'}
                cr.commit()
                super(osv.osv, self).write(cr, uid, [collaborator_id], vals)
            else:
                vals = {'notified':'no_notified'}
                cr.commit()
                super(osv.osv, self).write(cr, uid, [collaborator_id], vals)
        cr.commit()
        
    def send_notification(self, cr, uid, collaborator_id, context={}):
        threaded_sending = threading.Thread(target=self._send_notification, args=(cr.dbname , uid, collaborator_id))
        threaded_sending.start()
    
    def create(self, cr, uid, vals, context={}):
        partner_obj = self.pool['res.partner']
        f_obj = self.pool['kemas.func']
        
        cat_collaborator_id = f_obj.get_id_by_ext_id(cr, uid, 'res_partner_category_collaborator')
        if not cat_collaborator_id:
            raise osv.except_osv(u'¡Operación no válida!', u"No hay una categoria de partner para Colaborador.")
        
        # Procesar Nombre
        vals['first_names'] = extras.elimina_tildes(vals['first_names']).title()
        vals['last_names'] = extras.elimina_tildes(vals['last_names']).title()
        vals['name'] = "%s %s" % (vals['first_names'], vals['last_names'],)
        
        vals['email'] = vals['email'] and unicode(vals['email']).lower().replace(' ', '') or ''
        vals['points'] = vals.get('points', self.get_initial_points(cr, uid))
        vals['level_id'] = self.get_corresponding_level(cr, uid, vals['points'])
        
        # Crear un partner
        if not vals.get('partner_id'):
            vals_partner = {
                             'comment': vals.get('comment'),
                             'name': vals.get('name', False),
                             'image': vals.get('image', False),
                             'street': vals.get('street', False),
                             'street2': vals.get('street2', False),
                             'city': vals.get('city', False),
                             'state_id': vals.get('state_id', False),
                             'country_id': vals.get('country_id', False),
                             'email': vals.get('email', False),
                             'birthdate': vals.get('birth', False),
                             'phone': vals.get('phone', False),
                             'fax': vals.get('fax', False),
                             'mobile': vals.get('mobile', False),
                             'category_id': [(6, 0, [cat_collaborator_id])]
                             }
            vals['partner_id'] = partner_obj.create(cr, uid, vals_partner)
        else:
            p_id = vals['partner_id']
            partner = partner_obj.read(cr, uid, p_id, ['category_id'])
            category_ids = list(set(partner['category_id'] + [cat_collaborator_id]))
            partner_obj.write(cr, uid, [p_id], vals={'category_id': [(6, 0, category_ids)]})
        
        # Crear un codigo para la persona que se registre
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Collaborator'), ])[0]
        vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        
        # Asignar un usuario al colaborador
        collaborator_group_id = f_obj.get_id_by_ext_id(cr, uid, 'group_kemas_collaborator')
        if not collaborator_group_id:
            raise osv.except_osv(u'¡Operación no válida!', u"No hay un Grupo Colaborador definido.")
        
        nick_name = unicode(vals['nick_name']).title()
        apellido = unicode(extras.do_dic(vals['last_names'])[0]).title()
        name = u'''%s %s''' % (nick_name, apellido)
        vals['user_id'] = f_obj.create_user(cr, uid, name, vals['email'], vals['code'], collaborator_group_id, False, vals['partner_id'])['user_id']
        vals['state'] = vals.get('state', 'Active')
        
        res_id = super(kemas_collaborator, self).create(cr, uid, vals, context)
        # Escribir el historial de puntos
        history_points_obj = self.pool.get('kemas.history.points')
        description = 'Se inicializa el registro.'
        summary = '+' + str(vals['points']) + ' Puntos.'
        history_points_obj.create(cr, uid, {
                    'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    'collaborator_id': res_id,
                    'type': 'init',
                    'description': description,
                    'summary': summary,
                    'points': vals['points'],
                    })
        
        # Escribir una linea en la bitacora del Colaborador
        vals = {
                'collaborator_id' : res_id,
                'description' : 'Creacion del Colaborador.',
                'type' : 'important',
                }
        self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals)
        return res_id
    
    def write(self, cr, uid, ids, vals, context={}):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        # Cambiar el Puntaje y establecer Nivel
        if vals.has_key('points'):
            vals['level_id'] = self.get_corresponding_level(cr, uid, vals['points'])
            
        collaborators = self.read(cr, uid, ids, ['user_id', 'first_names', 'last_names'])
        for collaborator in collaborators:
            if context.get('is_collaborator', False):
                if collaborator['user_id'] and uid != collaborator['user_id'][0]:
                    raise osv.except_osv(u'¡Operación no válida!', _('You can not change information that is not yours!'))
                
            if context.get('no_update_logbook'):
                continue
            # Escribir una linea en la bitacora del Colaborador
            if not vals is None and not vals.has_key('level_id') and not vals.has_key('points'): 
                modify = ''
                func_obj = self.pool.get('kemas.func')
                for field in vals.keys():
                    field = func_obj.get_translate(cr, uid, field)[0]
                    field = func_obj.get_translate(cr, uid, field)[0]
                    modify += field + ', '
                vals_logbook = {
                        'collaborator_id' : collaborator['id'],
                        'description' : 'Modificacion de Datos: %s' % modify,
                        'type' : 'low_importance',
                        }
                self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals_logbook)
        res = super(kemas_collaborator, self).write(cr, uid, ids, vals, context)
        # Obtener el id de la categoria
        md_obj = self.pool['ir.model.data']
        partner_obj = self.pool['res.partner']
        md_ids = md_obj.search(cr, uid, [('name', '=', 'res_partner_category_collaborator')])
        if not md_ids:
            raise osv.except_osv(u'¡Operación no válida!', u"No hay una categoria de partner para Colaborador.")
        cat_collaborator_id = md_obj.read(cr, uid, md_ids[0], ['res_id'])['res_id']
        
        collaborators = self.read(cr, uid, ids, ['partner_id']) 
        for collaborator in collaborators:
            p_id = collaborator['partner_id'][0]
            partner = partner_obj.read(cr, uid, p_id, ['category_id'])
            category_ids = list(set(partner['category_id'] + [cat_collaborator_id]))
            partner_obj.write(cr, uid, [p_id], vals={'category_id': [(6, 0, category_ids)]})
        return res


    def _person_age(self, cr, uid, ids, name, arg, context={}):
        result = {}
        collaborators = super(osv.osv, self).read(cr, uid, ids, ['id', 'birth'], context=context)
        for collaborator in collaborators:
            result[collaborator['id']] = extras.calcular_edad(collaborator['birth'], 3)
        return result
    
    def _dummy_age(self, cr, uid, ids, name, value, arg, context={}):
        return True
       
    def on_change_join_date(self, cr, uid, ids, join_date, context={}):
        values = {}
        age = extras.calcular_edad(join_date, 3)
        if not age or age == '0':
            age = u'Sin fecha de ingreso'
        values['age_in_ministry'] = age
        return {'value':values}
    
    def on_change_birth(self, cr, uid, ids, birth, context={}):
        values = {}
        age = extras.calcular_edad(birth, 3)
        if not age or age == '0':
            age = u'Sin fecha de nacimiento'
        values['age'] = age
        return {'value':values}
    
    def get_initial_points(self, cr, uid, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        if not config_id:
            raise osv.except_osv(u'¡Advertencia!', u"El Sistema no tiene definidas las configuraciones.")
        return int(config_obj.read(cr, uid, config_id, ['default_points'])['default_points'])
    
    def get_percentage(self, cr, uid, ids, name, arg, context={}):
        def get_percent_progress_level(collaborator_id):
            level_obj = self.pool.get('kemas.level')
            #--------------------------------------------------------------------------------------
            res = 0
            try:
                collaborator = super(kemas_collaborator, self).read(cr, uid, collaborator_id, ['points', 'level_id', ])
                #Cargar Datos-------------------------------------------------------------------
                next_level_id = level_obj.get_next_level(cr, uid, collaborator['level_id'][0])
                if next_level_id:
                    next_level = level_obj.read(cr, uid, next_level_id, ['points'])
                    percentaje = float(collaborator['points'] * 100) / float(next_level['points'])
                    if percentaje < 0:
                        percentaje = 0
                    if percentaje > 100:
                        percentaje = 100
                    res = percentaje
                else:
                    res = 100
            except:None
            return res
        
        result = {}
        for collaborator_id in ids:
            result[collaborator_id] = get_percent_progress_level(collaborator_id)
        return result
    
    def cal_birthday(self, cr, uid, collaborator_id, context={}):
        birth = super(osv.osv, self).read(cr, uid, collaborator_id, ['birth'])['birth']
        birth = datetime.datetime.strptime(birth, '%Y-%m-%d')
        try:
            res = "%s-%s-%s 08:00:00" % (time.strftime("%Y"), birth.month, birth.day)
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            res = extras.convert_to_tz(res, tz)
            return datetime.datetime.strptime(res, "%Y-%m-%d %H:%M:%S")
        except: return None
        
    def _cal_birthday(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        for collaborator_id in ids:
            result[collaborator_id] = self.cal_birthday(cr, uid, collaborator_id, context).__str__()
        return result
    
    def _get_birthday(self, cr, uid, ids, name, arg, context={}):
        def get_birthday(collaborator_id):
            birthday = self.cal_birthday(cr, uid, collaborator_id, context)
            month = ''
            if birthday.month == 1:
                month = _("Jan")
            elif birthday.month == 2:
                month = _("Feb")
            elif birthday.month == 3:
                month = _("Mar")
            elif birthday.month == 4:
                month = _("Apr")
            elif birthday.month == 5:
                month = _("May")
            elif birthday.month == 6:
                month = _("Jun")
            elif birthday.month == 7:
                month = _("Jul")
            elif birthday.month == 8:
                month = _("Aug")
            elif birthday.month == 9:
                month = _("Sep")
            elif birthday.month == 10:
                month = _("Oct")
            elif birthday.month == 11:
                month = _("Nov")
            elif birthday.month == 12:
                month = _("Dec")
            return "%s %s" % (str(birthday.day), month)
        
        result = {}
        for collaborator_id in ids:
            result[collaborator_id] = get_birthday(collaborator_id)
        return result
        
    def _get_nick_name(self, cr, uid, ids, name, arg, context={}):
        def get_nick_name(collaborator_id):
            collaborator = super(osv.osv, self).read(cr, uid, collaborator_id, ['nick_name', 'last_names'])
            nick_name = unicode(collaborator['nick_name']).title()
            apellido = unicode(extras.do_dic(collaborator['last_names'])[0]).title()
            name = u'''%s %s''' % (nick_name, apellido)
            return name
                
        result = {}
        for collaborator_id in ids:
            result[collaborator_id] = get_nick_name(collaborator_id)
        return result
    
    def _get_ministry_age(self, cr, uid, ids, name, arg, context={}):
        result = {}
        collaborators = super(osv.osv, self).read(cr, uid, ids, ['id', 'join_date', 'state', 'end_service'], context=context)
        for collaborator in collaborators:
            if collaborator['state'] != 'Active':
                res = extras.calcular_edad(collaborator['join_date'], 4, collaborator['end_service'])
            else:
                res = extras.calcular_edad(collaborator['join_date'], 4)
            result[collaborator['id']] = res
        return result
    
    def build_QR_text(self, cr, uid, message, collaborator_id):
        fields = ['code', 'name', 'birth', 'gender', 'marital_status', 'phone', 'mobile', 'email', 'address', 'join_date', 'type', 'username', 'level_name']
        collaborator = super(osv.osv, self).read(cr, uid, collaborator_id, fields)
        #------------------------------------------------------------------------------------
        message = message
        message = message.replace('%cd', unicode(collaborator['code']))
        message = message.replace('%cl', unicode(collaborator['name']))
        message = message.replace('%bt', extras.convert_date_to_dmy(unicode(collaborator['birth'])))
        #----Genero-----------------------------------------------------------------
        if collaborator['gender'].lower() == 'male':
            message = message.replace('%gn', 'Hombre')
        else:
            message = message.replace('%gn', 'Mujer')
        #----Estado Civil-----------------------------------------------------------
        if collaborator['marital_status'].lower() == 'single':
            if collaborator['gender'].lower() == 'male':
                message = message.replace('%ms', 'Soltero')
            else:
                message = message.replace('%ms', 'Soltera')
        elif collaborator['marital_status'].lower() == 'married':
            if collaborator['gender'].lower() == 'male':
                message = message.replace('%ms', 'Casado')
            else:
                message = message.replace('%ms', 'Casada')
        elif collaborator['marital_status'].lower() == 'divorced':
            if collaborator['gender'].lower() == 'male':
                message = message.replace('%ms', 'Divorsiado')
            else:
                message = message.replace('%ms', 'Divorsiada')
        elif collaborator['marital_status'].lower() == 'widower':
            if collaborator['gender'].lower() == 'male':
                message = message.replace('%ms', 'Viudo')
            else:
                message = message.replace('%ms', 'Viuda')
        #-------------------------------------------------------------------------
        message = message.replace('%t1', unicode(collaborator['phone']))
        message = message.replace('%mb', unicode(collaborator['mobile']))
        message = message.replace('%em', unicode(collaborator['email']))
        message = message.replace('%ad', unicode(collaborator['address']))
        message = message.replace('%jd', unicode(extras.convert_date_to_dmy(collaborator['join_date'])))
        #-------------------------------------------------------------------------
        message = message.replace('%us', unicode(collaborator['username']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        #---Fecha y hora---------------------------------------------------------- 
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        return unicode(message)
    
    def _get_collaborator_by_bc_id(self, cr, uid, bc_id, context={}):
        import barcode
        result = False
        BC_class = barcode.get_barcode_class('ean13')
        fullcode = BC_class(bc_id).get_fullcode()
        record_id = int(extras.extraer_numeros(fullcode))
        return result
    
    def _get_barcode_image(self, cr, uid, ids, name, arg, context={}):
        import barcode
        from barcode.writer import ImageWriter
        from StringIO import StringIO
        
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        
        fields_to_read = [
                          'bc_type',
                          'bc_text',
                          'bc_module_width',
                          'bc_module_height',
                          'bc_quiet_zone',
                          'bc_font_size',
                          'bc_text_distance',
                          'bc_background',
                          'bc_foreground',
                          'bc_write_text',
                          'bc_text2',
                          ]
        preferences = config_obj.read(cr, uid, config_id, fields_to_read)
        options = {
                   'module_width': preferences['bc_module_width'] or 0.2,
                   'module_height': preferences['bc_module_height'] or 15.0,
                   'quiet_zone': preferences['bc_quiet_zone'] or 6.5,
                   'font_size': preferences['bc_font_size'] or 10,
                   'text_distance': preferences['bc_text_distance'] or 5.0,
                   'background': preferences['bc_background'] or 'white',
                   'foreground': preferences['bc_foreground'] or 'black',
                   'write_text': preferences['bc_write_text'],
                   'text': preferences['bc_text2'] or '',
                   }
        def get_barcode_image(collaborator):
            bc_text = preferences['bc_text'].replace('%cd', unicode(collaborator['code']))
            """
            id_int = int(extras.extraer_numeros(collaborator['id']))
            bc_text = extras.completar_cadena(id_int, 12)
            """
            BC = barcode.get_barcode_class(preferences['bc_type'])
            foo = BC(unicode(bc_text), writer=ImageWriter())
            fp = StringIO()
            foo.write(fp, options=options)
            return base64.encodestring(fp.getvalue())

        result = {}
        collaborators = super(kemas_collaborator, self).read(cr, uid, ids, ['code'])
        for collaborator in collaborators:
            result[collaborator['id']] = get_barcode_image(collaborator)
        return result
    
    def _get_QR_image(self, cr, uid, ids, name, arg, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, ['qr_text', 'qr_width', 'qr_height'])
        width = preferences['qr_width']
        height = preferences['qr_height']
        
        def get_QR_image(collaborator_id):
            value = self.build_QR_text(cr, uid, preferences['qr_text'], collaborator_id)
            return extras.get_image_code(value, width, height, False, "QR")

        result = {}
        for collaborator_id in ids:
            result[collaborator_id] = get_QR_image(collaborator_id)
        return result
    
    def _get_days_remaining(self, cr, uid, ids, name, arg, context={}): 
        def get_days_remaining(collaborator_id):
            suspension_obj = self.pool.get('kemas.suspension')
            suspension_ids = suspension_obj.search(cr, uid, [('collaborator_id', '=', collaborator_id), ('state', '=', 'on_going')])
            if suspension_ids:
                return suspension_obj.read(cr, uid, suspension_ids[0], ['days_remaining'])['days_remaining']
            return '0'

        result = {}
        for collaborator_id in ids:
            result[collaborator_id] = get_days_remaining(collaborator_id)
        return result
    
    def mailing(self, cr, uid, ids, name, arg, context={}):
        result = {}
        mailing = self.pool.get('kemas.func').mailing(cr, uid)
        for event_id in ids:
            result[event_id] = mailing
        return result
    
    def reload_avatar(self, cr, uid, ids, context={}):
        collaborators = super(osv.osv, self).read(cr, uid, ids, ['web_site_ids'])
        context['no_update_logbook'] = True
        for collaborator in collaborators:
            wslines = self.pool.get('kemas.collaborator.web.site').read(cr, uid, collaborator['web_site_ids'], ['get_avatar_from_website'])
            for wsline in wslines:
                if wsline['get_avatar_from_website']:
                    self.pool.get('kemas.collaborator.web.site').sync(cr, uid, [wsline['id']], context)
                    continue
        return True
    
    def update_avatars(self, cr, uid, context={}):
        collaborator_ids = super(osv.osv, self).search(cr, uid, [])
        return self.reload_avatar(cr, uid, collaborator_ids, context)
    
    def _replacements(self, cr, uid, ids, name, arg, context={}):
        from datetime import datetime
        # Calcular el numero suspensiones disponibles en este mes 
        config_obj = self.pool.get('kemas.config')
        preferences = config_obj.get_correct_config(cr, uid, ['number_replacements'])           
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
        now = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
        start = "%s-%s-%s 00:00:00" % (now.year, extras.completar_cadena(now.month), '01')
        end = "%s-%s-%s 23:59:59" % (now.year, now.month, extras.dias_de_este_mes())
        start = extras.convert_to_UTC_tz(start, tz)
        end = extras.convert_to_UTC_tz(end, tz)
        
        def replacements(collaborator_id):
            sql = """
                SELECT count(el.id) from kemas_event_collaborator_line as el
                JOIN kemas_event as e on (e.id = el.event_id)
                JOIN kemas_event_replacement as r on (el.replacement_id = r.id)
                WHERE 
                    e.date_start >= '%s' 
                    AND e.date_stop <= '%s' 
                    AND e.state in ('on_going','closed') 
                    AND r.collaborator_id = %d            
                """ % (start, end, collaborator_id)
            cr.execute(sql)
            result_query = cr.fetchall()
            result = preferences['number_replacements'] - int(result_query[0][0])
            if result < 1 :
                result = 0
            return result
        
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id'])
        for record in records:
            result[record['id']] = replacements(record['id'])
        return result
    
    def _last_connection(self, cr, uid, ids, name, arg, context={}): 
        def last_connection(user_id):
            if not user_id:
                return False
            
            sql = """
                SELECT login_date FROM res_users
                WHERE id = %d
                LIMIT 1
                """ % user_id[0]
            cr.execute(sql)
            login_date = cr.dictfetchall()[0]['login_date']
            if login_date is None or not login_date:
                return 'Nunca Conectado'
            
            login_date = parse(login_date)
            now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
            now = parse(now)
            diff = datetime.datetime.now() - login_date
            days = diff.days
            
            if days == 0:
                res = 'Hoy'
            elif days == 1:
                res = 'Ayer'
            else:
                res = unicode("%s, hace %d días", 'utf-8') % (tools.ustr(login_date.strftime('%A %d de %B de %Y')), days)
            return res
        
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id', 'user_id'])
        for record in records:
            result[record['id']] = last_connection(record['user_id'])
        return result
    
    def on_change_personal_id(self, cr, uid, ids, personal_id, context={}):
        values = {}
        warning = {}
        if personal_id:
            if not extras.validar_cedula_ruc(personal_id):
                values['personal_id'] = False
                warning = {'title' : u'¡Error!', 'message' : u"Número de Cédula Incorrecto. \nEn el caso de ser un Pasaporte ingrese la 'P' antes del número."}
        return {'value': values , 'warning': warning}
    
    def _ff_age(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id', 'birth'])
        for record in records:
            result[record['id']] = extras.calcular_edad(record['birth'], 3)
        return result
    
    def _ff_age_in_ministry(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id', 'join_date', 'end_service', 'state'])
        for record in records:
            if record['state'] != 'Active':
                res = extras.calcular_edad(record['join_date'], 4, record['end_service'])
            else:
                res = extras.calcular_edad(record['join_date'], 4)
            result[record['id']] = res
        return result
    
    def _count_all(self, cr, uid, ids, name, arg, context={}): 
        def count_all(record):
            result = {'history_points_count': 0, 'event_count': 'Undefined', 'attendance_count': 0, 'suspension_count': 0, 'logbook_count': 0, }
            # Consultar todos los eventos
            sql = """
                select count(ev.id) from kemas_event  as ev
                join kemas_event_collaborator_line as ln on ev.id = ln.event_id
                where ln.collaborator_id = %d
                """ % record['id']
            cr.execute(sql)
            old_events = cr.fetchall()[0][0]
            
            # Consultar todos los eventos en Curso
            sql = """
                select count(ev.id) from kemas_event  as ev
                join kemas_event_collaborator_line as ln on ev.id = ln.event_id
                where ln.collaborator_id = %d and state in ('on_going')
                """ % record['id']
            cr.execute(sql)
            new_events = cr.fetchall()[0][0]
            
            result['event_count'] = '%d - %d' % (old_events, new_events)
            
            # Contar el historial de puntos
            cr.execute("select count(id) from kemas_history_points where collaborator_id = %d" % record['id'])
            result['history_points_count'] = cr.fetchall()[0][0]
            
            # Contar los registro de asistencias
            cr.execute("select count(id) from kemas_attendance where collaborator_id = %d" % record['id'])
            result['attendance_count'] = cr.fetchall()[0][0]
            
            # Contar los registro de asistencias
            cr.execute("select count(id) from kemas_suspension where collaborator_id = %d" % record['id'])
            result['suspension_count'] = cr.fetchall()[0][0] 
            
            # Contar conexiones al sistema
            cr.execute("select count(id) from kemas_collaborator_logbook_login where collaborator_id = %d" % record['id'])
            result['logbook_count'] = cr.fetchall()[0][0] 
            return result
             
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id'])
        for record in records:
            result[record['id']] = count_all(record)
        return result
    
    def _get_collaborator_photo_inv(self, cr, uid, record_id, name, value, fnct_inv_arg, context):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        if not context.get('no_save_inv'):
            photo = value
            record = super(osv.osv, self).read(cr, uid, record_id, ['gender', 'partner_id'])
            if not photo:
                if record['gender'] == 'Male':
                    photo = self.get_photo_male()
                else:
                    photo = self.get_photo_female()
            vals = {}
            vals['photo'] = extras.crop_image(photo, 192, height_photo=15)
            vals['photo_medium'] = extras.crop_image(photo, 64)
            vals['photo_small'] = extras.crop_image(photo, 48)
            vals['photo_very_small'] = extras.crop_image(photo, 32)
            
            context['no_save_inv'] = True
            self.pool.get('res.partner').write(cr, uid, [record['partner_id'][0]], {'image': extras.crop_image(photo, 256)}, context=context)
            self.write(cr, uid, [record_id], vals, context=context)
        return True
    
    def _get_collaborator_photo(self, cr, uid, ids, name, arg, context={}): 
        def get_collaborator_photo(record):
            result = {'photo': False, 'photo_jarge': False, 'photo_medium': False, 'photo_small': False, 'photo_very_small': False, }
            
            photo = False
            if record['partner_id']:
                partner = self.pool.get('res.partner').read(cr, uid, record['partner_id'][0], ['image'])
                photo = partner['image']
            
            if not photo:
                if record['gender'] == 'Male':
                    photo = self.get_photo_male()
                else:
                    photo = self.get_photo_female()
            if photo:
                result['photo'] = extras.crop_image(photo, 192, height_photo=15)
                result['photo_medium'] = extras.crop_image(photo, 64)
                result['photo_small'] = extras.crop_image(photo, 48)
                result['photo_very_small'] = extras.crop_image(photo, 32)
            return result
             
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['partner_id', 'gender'])
        for record in records:
            result[record['id']] = get_collaborator_photo(record)
        return result
    
    def _get_collaborator_from_partner(self, cr, uid, ids, context=None):
        return self.pool['kemas.collaborator'].search(cr, uid, [('partner_id', 'in', ids)], context=context)
    
    _photo_store_triggers = {
        'kemas.collaborator': (lambda s, c, u, i, x: i, ['partner_id'], 10),
        'res.partner': (_get_collaborator_from_partner, ['image'], 10)
    }
    
    def _get_name_inv(self, cr, uid, record_id, name, value, fnct_inv_arg, context):
        record = super(osv.osv, self).read(cr, uid, record_id, ['partner_id'])
        collaborator_name = self.name_get(cr, uid, [record_id])[0][1]
        return self.pool.get('res.partner').write(cr, uid, [record['partner_id'][0]], {'name': collaborator_name})
    
    def _get_name(self, cr, uid, ids, name, arg, context={}): 
        def get_name(record):
            result = ' -- '
            if record['partner_id']:
                partner = self.pool.get('res.partner').read(cr, uid, record['partner_id'][0], ['name'])
                result = partner['name']
            return result
             
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['partner_id'])
        for record in records:
            result[record['id']] = get_name(record)
        return result
    
    _name_store_triggers = {
        'kemas.collaborator': (lambda s, c, u, i, x: i, ['partner_id'], 10),
        'res.partner': (_get_collaborator_from_partner, ['name'], 10)
    }
    
    _name = 'kemas.collaborator'
    _columns = {
        'partner_id':fields.many2one('res.partner', 'Partner relacionado', required=False, ondelete='cascade'),
        'mailing': fields.function(mailing, type='boolean', string='Enviando Correos'),
        'code': fields.char('Code', size=32, help="Código que se le asigna a cada colaborador"),
        'personal_id' : fields.char('CI/PASS', size=15, help=u"Número de cédula o pasaporte",),
        'photo': fields.function(_get_collaborator_photo, fnct_inv=_get_collaborator_photo_inv, multi='all', string="Foto", type="binary", store=_photo_store_triggers),
        'photo_medium': fields.function(_get_collaborator_photo, multi='all', string="Foto", type="binary", store=_photo_store_triggers),
        'photo_small': fields.function(_get_collaborator_photo, multi='all', string="Foto", type="binary", store=_photo_store_triggers),
        'photo_very_small': fields.function(_get_collaborator_photo, multi='all', string="Foto", type="binary", store=_photo_store_triggers),
        'qr_code': fields.function(_get_QR_image, type='binary', string='QR code data'),
        'bar_code': fields.function(_get_barcode_image, type='binary', string='Bar Code data'),
        'first_names':fields.char('Nombres', size=64, required=True),
        'last_names':fields.char('Apellidos', size=64, required=True),
        'name': fields.function(_get_name, fnct_inv=_get_name_inv, string="Nombres", type="char", store=_name_store_triggers, required=True, help="Nombres completos del Colaborador"),
        'nick_name': fields.char('Nick name', size=32, required=True, help="Nombre por el que le gusta ser llamado."),
        'name_with_nick_name': fields.function(_get_nick_name, type='char', string='Name'),
        'birth': fields.related('partner_id', 'birthdate', type='date', string='Fecha de nacimiento', store=False),
        'birthday_date': fields.function(_get_birthday, type='char', string='Name'),
        'birthday': fields.function(_cal_birthday, type='datetime', string='Name'),
        'age' : fields.function(_ff_age, type='char', string='Edad', help="Edad del colaborador"),
        'gender': fields.selection([('Male', 'Hombre'), ('Female', 'Mujer'), ], u'Género', required=True, help="El género del colaborador",),
        'marital_status': fields.selection([('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widower', 'Widower')], 'Marital status', help=u"Estado Civíl"),
        'skill_line_ids': fields.one2many('kemas.skill.line', 'collaborator_id', 'skill_lines', help='Habilidades que tiene este colaborador'),
        
        'street': fields.related('partner_id', 'street', type='char', string='Calle 1', store=False),
        'street2': fields.related('partner_id', 'street2', type='char', string='Calle 2', store=False),
        'city': fields.related('partner_id', 'city', type='char', string='Ciudad', store=False),
        'state_id': fields.related('partner_id', 'state_id', type='many2one', string='Ciudad', relation="res.country.state", store=False),
        'country_id': fields.related('partner_id', 'country_id', type='many2one', string=u'País', relation="res.country", store=False),
        
        'phone': fields.related('partner_id', 'phone', type='char', string=u'Teléfono', store=False),
        'fax': fields.related('partner_id', 'fax', type='char', string=u'Fax', store=False),
        'mobile': fields.related('partner_id', 'mobile', type='char', string=u'Móvil', store=False),
        'email': fields.related('partner_id', 'email', type='char', string='Email', store=False, required=True),
        
        'web_site_ids': fields.one2many('kemas.collaborator.web.site', 'collaborator_id', 'Web sites', help='Sitio web'),
        'join_date': fields.date('Join date', help="Fecha en la que ingreso en la empresa"),
        'age_in_ministry' : fields.function(_ff_age_in_ministry, type='char', string='Tiempo de colaboración'),
        'end_service': fields.date('End Service', help="Fecha en la que el colaborador salió de la empresa"),
        'logbook_ids': fields.one2many('kemas.collaborator.logbook', 'collaborator_id', 'Logbook'),
        'state': fields.selection([
            ('creating', 'Creating'),
            ('Inactive', 'Inactive'),
            ('Locked', 'Locked'),
            ('Active', 'Active'),
            ('Suspended', 'Suspended'),
            ], 'State', select=True, help="Estado en la que se encuentra actialmente este colaborador"),
        'born_country': fields.many2one('res.country', 'Born Country', required=False, help="País de Nacimiento"),
        'born_state': fields.many2one('res.country.state', 'Born State', required=False, help="Provincia de nacimiento"),
        'born_city': fields.char('Born City', size=255, required=True, help="Ciudad de nacimiento"),
        'user_id': fields.many2one('res.users', 'User', help='Nombre de Usuario asignado con el que se conecta al sistema'),
        'login': fields.related('user_id', 'login', type='char', store=True, string='Username', readonly=1, help="Usuario asignado con el que se conecta al sistema"),
        'points': fields.integer('Points', help="Puntos que tiene actualmente"),
        'level_id': fields.many2one('kemas.level', 'Nivel', required=False, ondelete='restrict', help='Nivel en el que se encuantra por los puntos acumulados.'),
        'notified': fields.selection([
            ('notified', 'Notified'),
            ('no_notified', 'No notified'),
            ], 'Notified', select=True, help="Indica si el correo de creación de usuario fue enviado"),
        'last_connection': fields.function(_last_connection, type='char', string='Ultima Conexion'),
        'progress': fields.function(get_percentage, type='float', string='Progress'),
        'replacements': fields.function(_replacements, type='integer', string='Replacements avaliable', help=u"Número de reemplazos que tiene aún disponibles para este mes"),
        #Suspensions----------------------------------------------------------------------------------------------------------
        'suspension_ids': fields.one2many('kemas.suspension', 'collaborator_id', 'Suspensions'),
        'day_remaining_suspension': fields.function(_get_days_remaining, type='char', string='Days remaining'),
        #One to Many Relations-----------------------------------------------------------------------------------------------
        'school4d_ids': fields.one2many('kemas.school4d_line', 'collaborator_id', 'Persons'),
        'history_points_ids': fields.one2many('kemas.history.points', 'collaborator_id', 'History points'),
        'attendance_ids': fields.one2many('kemas.attendance', 'collaborator_id', 'Attendances', help='Registros de asistencia'),
        'team_id': fields.many2one('kemas.team', 'Team', help='Equipo al que pertenece este colaborador'),
        #Many to Many Relations----------------------------------------------------------------------------------------------
        'area_ids': fields.many2many('kemas.area', 'kemas_collaborator_area_rel', 'collaborator_id', 'area_id', 'Areas', help=u'Áreas en las que labora este colaborador'),
        #Related-------------------------------------------------------------------------------------------------------------
        'level_name': fields.related('level_id', 'name', type='char', string='Level name', readonly=1, store=False),
        'username': fields.related('user_id', 'login', type='char', string='Login', readonly=1, store=True),
        'password': fields.related('user_id', 'password', type='char', string='Password', readonly=1, store=False),
        # Contadores
        'history_points_count': fields.function(_count_all, type='integer', string='Historial de puntos', multi=True),
        'event_count': fields.function(_count_all, type='char', string='Todos los eventos', multi=True),
        'attendance_count': fields.function(_count_all, type='integer', string='Historial de asistencias', multi=True),
        'suspension_count': fields.function(_count_all, type='integer', string='Historial de suspensiones', multi=True),
        'logbook_count': fields.function(_count_all, type='integer', string='Logins', multi=True),
        }
    
    def _get_photo_collaborator(self, cr, uid, ids, context={}):
        return extras.crop_image(self.get_photo_male(), 192, height_photo=15)
    
    def get_photo_male(self):
        photo_path = addons.kemas.__path__[0] + '/images/male.jpg'
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_photo_small_male(self):
        photo_path = addons.kemas.__path__[0] + '/images/male_small.jpg'
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_photo_female(self):
        photo_path = addons.kemas.__path__[0] + '/images/female.jpg'
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_photo_small_female(self):
        photo_path = addons.kemas.__path__[0] + '/images/female_small.jpg'
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_first_level(self, cr, uid, context={}):
        level_obj = self.pool.get('kemas.level')
        level_ids = level_obj.search(cr, uid, [('first_level', '=', True)])
        if level_ids:
            return level_ids[0]
    
    _defaults = {  
        'notified': 'notified',
        'gender': 'Male',
        'marital_status': 'Single',
        'points': '0',
        'state': 'creating',
        'photo': _get_photo_collaborator,
        'level_id': get_first_level,
        'join_date': time.strftime("%Y-%m-%d"),
        }
    
    _sql_constraints = [
        ('collaborator_code', 'unique (code)', 'This Code already exist!'),
        ('collaborator_name', 'unique (name)', "This Collaborator's already exist!"),
        ('collaborator_user_id', 'unique (user_id)', 'This User already exist!'),
        ]


    
class kemas_history_points(osv.osv):
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False, lazy=True):
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_history_points, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby, lazy)
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        collaborator_obj = self.pool.get('kemas.collaborator')
        user_obj = self.pool.get('res.users')
        group_obj = self.pool.get('res.groups')
        user_id = user_obj.search(cr, uid, [('id', '=', uid), ])
        groups_id = user_obj.read(cr, uid, user_id, ['groups_id'])[0]['groups_id']
        if not 1 in groups_id:
            kemas_collaborator_id = group_obj.search(cr, uid, [('name', '=', 'Kemas / Collaborator'), ])[0]
            if kemas_collaborator_id in groups_id: 
                collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
                args.append(('collaborator_id', 'in', collaborator_ids))  
        if context.get('limit_records', False) and limit == None: 
            limit = context.get('limit_records', None)
            order = 'date desc'
        
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def create(self, cr, uid, vals, context={}):
        if not vals.get('code', False):
            seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas History Points'), ])[0]
            vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        vals['reg_uid'] = uid
        collaborator = self.pool.get('kemas.collaborator').read(cr, uid, vals['collaborator_id'], ['user_id'])
        partner_id = self.pool.get('res.users').read(cr, uid, collaborator['user_id'][0], ['partner_id'])['partner_id'][0]
        follower_ids = [partner_id]
        vals['message_follower_ids'] = [(6, 0, follower_ids)]

        # Guardar el registro        
        context['mail_create_nolog'] = True
        res_id = super(osv.osv, self).create(cr, uid, vals, context)
        
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        if partner_id in follower_ids:
            follower_ids.remove(partner_id)
        
        body = u'''
        <div>
            <span>
                • <b>Modificacion de Puntos</b>
            </span>
        </div>
        '''
        context['notify_all_followers'] = True
        context['delete_uid_followers'] = True
        self.pool['mail.th'].log_create(cr, uid, res_id, self._name, body, context=context)
        return res_id
    
    _order = 'date DESC'
    _rec_name = 'date'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _name = 'kemas.history.points'
    _columns = {
        'code': fields.char('Code', size=32, help="code that is assigned to each register", required=True),
        'date': fields.datetime('Date', required=True, help="Date you performed the modification of the points."),
        'reg_uid': fields.many2one('res.users', 'Changed by', readonly=True, help='User who made ​​the points change.'),
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', required=True, ondelete="cascade"),
        'attendance_id': fields.many2one('kemas.attendance', 'Registro de asistencia', ondelete="cascade"),
        'type': fields.selection([
            ('init', 'Init'),
            ('increase', 'Increase'),
            ('decrease', 'Decrease'),
            ], 'Type', select=True, readonly=True),
        'description': fields.text('Description', required=True),
        'summary': fields.char('Summary', size=255, required=True),
        'points': fields.integer('Points', help='Points that involved this change'),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
    _sql_constraints = [
        ('collaborator_code', 'unique (code)', 'This Code already exist!'),
        ]
    
class kemas_place(osv.osv):
    def rebuild_import_data(self, cr, uid, ids, context={}):
        # Reprocesar miembros de los eventos
        event_obj = self.pool['kemas.event']
        event_obj.build_members(cr, uid, super(event_obj.__class__, event_obj).search(cr, uid, [('members', '=', False)],limit=20), {'rebuild_import_data': True})
        
        
        # Reprocesar usuario de las tareas asignadas
        """
        task_assigned_obj = self.pool['kemas.task.assigned']
        collaborator_obj = self.pool['kemas.collaborator']

        tasks = task_assigned_obj.read(cr, uid, task_assigned_obj.search(cr, uid, []), ['collaborator_id'])
        for task in tasks:
            user_id = collaborator_obj.read(cr, uid, task['collaborator_id'][0], ['user_id'])['user_id'][0]
            task_assigned_obj.write(cr, uid, [task['id']], {'user_id': user_id})
        """
        return True
    
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def __fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=True, submenu=False):       
        res = super(kemas_place, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=False, submenu=False)
        if res['type'] == 'form':
            url_map = "https://www.google.com.ec/maps?t=m&amp;ie=UTF8&amp;ll=-2.897671,-78.997305&amp;spn=0.001559,0.002511&amp;z=19&amp;output=embed" 
            map_str = """
            <iframe width="100%%" height="350" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" src="%s"></iframe>
            <br /><small><a href="%s" style="color:#0000FF;text-align:left" target="blank">Ver mapa más grande</a></small>
            """ % (url_map, url_map)
            res['arch'] = res['arch'].replace('<!-- mapa -->', map_str.encode('utf-8'))
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    _order = 'name'
    _name = 'kemas.place'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='The name of the place'),
        'address': fields.text('Address'),
        'Map': fields.text('Mapa'),
        'photo': fields.binary('Photo', help='the photo of the place'),
        'active': fields.boolean('Active', required=False, help='Indicates whether this place is active or not'),
        'map_url':fields.char('URL del mapa', size=400, required=False, readonly=False),
        }
    _sql_constraints = [
        ('place_name', 'unique (name)', 'This Name already exist!'),
        ]
    _defaults = {  
        'active': True
        }

class kemas_repository_category(osv.osv):
    _order = 'name'
    _name = 'kemas.repository.category'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        }
    _sql_constraints = [
        ('recording_category_name', 'unique (name)', 'This Name already exist!'),
        ]
    
class kemas_repository(osv.osv):
    def write_log_draft(self, cr, uid, res_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                • <b>Pasado a Borrador</b>
            </span>
        </div>
        '''
        return self.write_log_update(cr, uid, res_id, body, notify_partner_ids) 
    
    def write_log_done(self, cr, uid, res_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                • <b>Publicado</b>
            </span>
        </div>
        '''
        return self.write_log_update(cr, uid, res_id, body, notify_partner_ids) 
    
    def write_log_update(self, cr, uid, res_id, body, notify_partner_ids=[]):
        # --Escribir un mensaje con un registro de que se paso Estado en Curso
        user_obj = self.pool.get('res.users')
        message_obj = self.pool.get('mail.message')
        
        res_name = self.name_get(cr, uid, [res_id])[0][1]
        partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        vals_message = {
                        'body' : body,
                        'model' : 'kemas.repository',
                        'record_name' : res_name,
                        'res_id' : res_id,
                        'type' : 'notification',
                        'author_id' : partner_id,
                        }
        message_id = message_obj.create(cr, uid, vals_message)
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
        self.write(cr, uid, ids, {'state' : 'done'})
        message_follower_ids = self.read(cr, uid, ids[0], ['message_follower_ids'])['message_follower_ids']
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        if partner_id in message_follower_ids:
            message_follower_ids.remove(partner_id)
        self.write_log_done(cr, uid, ids[0], message_follower_ids)
        return True
    
    def draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state' : 'draft'})
        message_follower_ids = self.read(cr, uid, ids[0], ['message_follower_ids'])['message_follower_ids']
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        if partner_id in message_follower_ids:
            message_follower_ids.remove(partner_id)
        self.write_log_draft(cr, uid, ids[0], message_follower_ids)
        return True
    
    def create(self, cr, uid, vals, *args, **kwargs):
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Repository'), ])[0]
        vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        vals['date'] = str(time.strftime("%Y-%m-%d %H:%M:%S"))
        vals['user_id'] = uid
        return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    _order = 'name'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _name = 'kemas.repository'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='Filename'),
        'file': fields.binary('File'),
        'file_name': fields.char('File name', size=255),
        'type': fields.selection([
            ('binary', 'Binario'),
            ('url', 'Url'),
             ], 'Tipo', required=True, help="Tipo de archivo que se va a adjuntar"),
        'url': fields.char('Url', size=255, help="La Url de la ubicación del archivo"),
        'code': fields.char('Code', size=32, help="unique code that is assigned to each file"),
        'tags': fields.many2many('kemas.repository.category', 'kemas_repository_file_category_rel', 'file_id', 'category_id', 'Etiquetas'),
        'date': fields.datetime('Date upload', help="Date the file was uploaded"),
        'description': fields.text('Description'),
        'user_id': fields.many2one('res.users', 'Uploaded by', help='User who uploaded the file'),
        'state': fields.selection([
            ('draft', 'Borrador'),
            ('done', 'Publicado'),
             ], 'Estado', required=True),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
    
    _defaults = {  
        'state': 'draft',
        'type': 'binary',
        'code': '---',
        }
    
    _sql_constraints = [
        ('repository_name', 'unique (name)', 'This Name already exist!'),
        ]

class kemas_service(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def copy(self, cr, uid, record_id, default=None, context={}):
        if default is None or not default or not isinstance(default, (dict)): default = {}
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        record_base = self.read(cr, uid, record_id, ['name'])
        dict_update = {
                       'name': record_base['name'] + ' (Copia)',
                       }
        default.update(dict_update)
        return super(kemas_service, self).copy(cr, uid, record_id, default, context=context)
    
    def write(self, cr, uid, ids, vals, context={}):
        if super(osv.osv, self).write(cr, uid, ids, vals, context):
            event_obj = self.pool.get('kemas.event')
            event_ids = event_obj.search(cr, uid, [('state', 'in', ['draft', 'on_going']), ('service_id', '=', ids[0])])
            for event_id in event_ids: self.pool.get('kemas.event').write(cr, uid, [event_id], {'service_id':ids[0]}, {'change_service':True})
        return True
     
    def validate_valid_input(self, cr, uid, ids):
        service = self.read(cr, uid, ids[0], [])
        #----La hora de Inicio de servicio no puede ser mayor a la hora de fin de servicio--------------------------------------------------------.
        if float(service['time_start']) >= float(service['time_end']):
            raise osv.except_osv(u'¡Operación no válida!', _('The start time must be less than the end time.'))
        #----El tiempo para registro puntual no puede ser mayor al tiempo limite de registro------------------------------------------------------.
        if float(service['time_register']) >= float(service['time_limit']):
            raise osv.except_osv(u'¡Operación no válida!', _('The time of entry can not be longer than the time limit.'))
        #----La hora de entrada no puede ser mayor a la hora de finalizacion de servicio----------------------------------------------------------.
        if float(service['time_entry']) >= float(service['time_end']):
            raise osv.except_osv(u'¡Operación no válida!', _('The time of entry can not be longer than the end time.'))
        #----La hora de entrada sumada mas el tiempo para registro puntual no puede ser mayor a la la hora de finalizacion de servicio------------.
        if (float(service['time_entry']) + float(service['time_register'])) >= float(service['time_end']):
            raise osv.except_osv(u'¡Operación no válida!', _('The time of entry coupled with the time of entry can not be longer than the time end.'))
        #----La hora de entrada sumada mas el tiempo limite registro de asistencia no puede ser mayor a la la hora de finalizacion de servicio----.
        if (float(service['time_entry']) + float(service['time_limit'])) >= float(service['time_end']):
            raise osv.except_osv(u'¡Operación no válida!', _('The time of entry coupled with the time limit can not be longer than the time end.'))
        return True
    
    def _get_days(self, cr, uid, context={}):
        result = [
                  ('01', u'Lunes'),
                  ('02', u'Martes'),
                  ('03', u'Miércoles'),
                  ('04', u'Jueves'),
                  ('05', u'Viernes'),
                  ('06', u'Sábado'),
                  ('07', u'Domingo'),
                  ]
        return result
    
    _order = 'time_start'
    _name = 'kemas.service'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'time_start': fields.float('Time start', required=True, help='Start time of service'),
        'time_end': fields.float('Time end', required=True, help='End time of service'),
        'day': fields.selection(_get_days, u'Día', required=False),
        'time_entry': fields.float('Time entry', required=True, help='End time of service'),
        'time_register': fields.float('Time register', required=True, help='End time of service'),
        'time_limit': fields.float('Time limit', required=True, help='Limit time to register attendance'),
        'description': fields.text('Description'),
        'active': fields.boolean('Active', required=False, help='Indicates whether this service is active or not'),
        }
    _sql_constraints = [
        ('service_name', 'unique (name)', 'This Name already exist!'),
        ]
    _constraints = [
        (validate_valid_input, 'The input data are inconsistent.', ['time_start']),
        ]
    _defaults = {
        'time_start': float(8 + (0.00 * 100 / 60)),
        'time_end': float(9 + (0.30 * 100 / 60)),
        'time_entry': float(7 + (0.30 * 100 / 60)),
        'time_register': float(0.30 * 100 / 60),
        'time_limit' : 1.00,
        'active':True
        }
    
class kemas_event_collaborator_line(osv.osv):
    def on_change_collaborator(self, cr, uid, ids, context={}):
        values = {}
        values['activity_ids'] = False
        return {'value':values}
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False, lazy=True):
        if context.has_key('search_this_month'):
            context.pop('search_this_month')
        items_to_remove = []
        for arg in domain:
            try:
                if arg[0] == 'ctx':
                    foo = arg[2].split(':')
                    context.update({foo[0]: True})
                    items_to_remove.append(arg)
            except:
                None
        for item in items_to_remove:
            domain.remove(item)
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_event_collaborator_line, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby, lazy)
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_filter', False):
            if context.has_key('search_filter') == 1:
                args.append(('event_id.state', 'in', ['on_going', 'closed', 'draft']))
        
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('event_id.date_start', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('event_id.date_stop', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(kemas_event_collaborator_line, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    _name = 'kemas.event.collaborator.line'
    _rec_name = 'collaborator_id'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', required=True),
        'event_id': fields.many2one('kemas.event', 'event', required=True, ondelete="cascade", select=True),
        'activity_ids': fields.many2many('kemas.activity', 'kemas_event_collaborator_line_activity_rel', 'event_collaborator_line_id', 'activity_id', 'Activities', help='Activities that have been assigned to this Collaborator in this event'),
        'sent_date': fields.datetime('Enviado el'),
        'send_email_state': fields.selection([
            ('Sent', 'Sent'),
            ('Waiting', 'Waiting'),
            ('Timeout', 'Timeout'),
            ('Error', 'Error'),
            ], 'Send email state', select=True),
        'count': fields.integer('Count'),
        'ct': fields.integer('Count'),
        'replacement_id': fields.many2one('kemas.event.replacement', 'Collaborator Replaced', help=''),
        #Related-----------------------------------------------------------------------------------------------------------------------------
        'team_id': fields.related('collaborator_id', 'team_id', type="many2one", relation="kemas.team", string="Team"),
        'level_id': fields.related('collaborator_id', 'level_id', type="many2one", relation="kemas.level", string="Level"),
        'gender': fields.related('collaborator_id', 'gender', type='selection', selection=[('Male', 'Male'), ('Female', 'Female'), ], string='Gender'),
        'points': fields.related('collaborator_id', 'points', type='integer', string='points', readonly=1, store=False),
        'collaborator_state': fields.related('collaborator_id', 'state', type='selection', selection=[
                                                                                         ('creating', 'Creating'),
                                                                                         ('Inactive', 'Inactive'),
                                                                                         ('Locked', 'Locked'),
                                                                                         ('Active', 'Active'),
                                                                                         ], string='State'),
        
        'date_start': fields.related('event_id', 'date_start', type='datetime', string='Date'),
        'service_id': fields.related('event_id', 'service_id', type="many2one", relation="kemas.service", string="Service"),
        'state': fields.related('event_id', 'state', type='char', string='State'),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
    _sql_constraints = [
        ('u_collaborator_event', 'unique (collaborator_id, event_id)', 'One of the contributors appears more than once in the list!'),
        ]
    _defaults = {  
        'send_email_state': 'Waiting',
        'count':1,
        'ct':1
        }
    
class kemas_event_stage(osv.osv):    
    _name = 'kemas.event.stage'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Stage Name', required=True, size=64, translate=True),
        'sequence': fields.integer('Sequence'),
    }
    _defaults = {
        'sequence': 1
    }
    _order = 'sequence'
    
class kemas_event(osv.osv):
    def on_change_team(self, cr, uid, ids, team, context={}):
        values = {}
        # values['event_collaborator_line_ids'] = False
        return {'value':values}
    
    def on_change_min_points(self, cr, uid, ids, points, context={}):
        values = {}
        # values['event_collaborator_line_ids'] = False
        return {'value':values}
    
    def on_change_lines(self, cr, uid, ids, line_ids, context={}):
        values = {}
        values['line_ids'] = unicode(line_ids)
        return {'value':values}
                
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):    
        if context.get('order_date_start', False):
            order = 'date_start ' + context['order_date_start'] 
        
        collaborator_id = False
        if context.get('collaborator_id', False):
            for arg in args:
                try:
                    if arg[0] == 'collaborator_id':
                        collaborator_id = arg[2]
                        args.remove(arg)
                        break
                except:None
        
        collaborator_obj = self.pool.get('kemas.collaborator')
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        user_obj = self.pool.get('res.users')
        group_obj = self.pool.get('res.groups')
        user_id = user_obj.search(cr, uid, [('id', '=', uid), ])
        groups_ids = user_obj.read(cr, uid, user_id, ['groups_id'])[0]['groups_id']
        if not 1 in groups_ids:
            kemas_collaborator_id = group_obj.search(cr, uid, [('name', '=', 'Kemas / Collaborator'), ])[0]
            if kemas_collaborator_id in groups_ids: 
                collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
                event_line_ids = event_line_obj.search(cr, uid, [('collaborator_id', 'in', collaborator_ids)])
                l1 = super(osv.osv, self).search(cr, uid, args + [('event_collaborator_line_ids', 'in', event_line_ids)])

                partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
                sql = """
                select c.res_id from mail_compose_message c
                join mail_compose_message_res_partner_rel as rel on (rel.wizard_id = c.id)
                where rel.partner_id in (%d) and c.model = 'kemas.event' 
                group by c.res_id
                """ % (partner_id)
                cr.execute(sql)
                l2 = extras.convert_result_query_to_list(cr.fetchall())
                l3 = super(osv.osv, self).search(cr, uid, args + [('message_follower_ids', 'in', [partner_id])])
                event_ids = list(set(l1 + l2 + l3))
                args.append(('id', 'in', event_ids))
        
        if context.has_key('on_going'):
            if context['on_going']:   
                args.append(('state', '=', 'on_going'))       
        
        if context.has_key('current_events'):
            if context['current_events']:
                now = time.strftime("%Y-%m-%d %H:%M:%S")   
                args.append(('date_init', '<=', now))
                args.append(('date_stop', '>=', now))
                args.append(('state', '=', 'on_going'))
        
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_start', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date_start', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        
        res_ids = super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        if collaborator_id:
            sql = """
                select e.id from kemas_event as e
                join kemas_event_collaborator_line as l on (l.event_id = e.id)
                where l.collaborator_id = %d and e.id in %s
                """ % (collaborator_id, extras.convert_to_tuple_str(res_ids))
            cr.execute(sql)
            res_ids = list(set(extras.convert_result_query_to_list(cr.fetchall())))
        
        for arg in args:
            if str(arg) in ["['message_unread', '=', True]", "('message_unread', '=', True)"]:
                res_ids += super(osv.osv, self).search(cr, uid, [('message_unread', '=', True)])
                res_ids = list(set(res_ids))
                continue
        return res_ids
    
    def name_get(self, cr, uid, ids, context={}):    
        if type(ids).__name__ == 'int':
            ids = [ids]
        if not len(ids):
            return[]
        
        if type(ids[0]).__name__ == 'dict':
            if ids[0].has_key('res_id'):
                ids = [ids[0]['res_id']]
                
        reads = self.browse(cr, uid, ids, context)
        res = []
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        for record in reads:   
            if record.state in ['on_going', 'draft']:
                date = str(extras.convert_to_tz(record.date_start, tz))[:16]
                name = (unicode(record.service_id.name) + ' | ' + date + '-' + str(extras.convert_float_to_hour_format(record.service_id.time_end)))
            elif record.state in ['creating']:
                date = str(extras.convert_to_tz(record.date_start, tz))[:16]
                name = name = (unicode(record.service_id.name) + ' | ' + str(date))
            else:                
                date = str(extras.convert_to_tz(record.rm_date, tz))[:16]
                name = (record.rm_service + ' | ' + str(date) + ' - ' + str(extras.convert_float_to_hour_format(record.rm_time_end)))
            res.append((record.id, name))
        return res
    
    def send_email(self, cr, uid, ids, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['mailing'] == False or preferences['use_message_event'] == False: 
            raise osv.except_osv(u'¡Operación no válida!', _('Notifications are disabled.'))
        event_line_ids = self.read(cr, uid, ids[0], ['event_collaborator_line_ids'])['event_collaborator_line_ids']
        sending_emails = self.read(cr, uid, ids[0], ['sending_emails'])['sending_emails']
        collaborator_ids_send_email = self.read(cr, uid, ids[0], ['collaborator_ids_send_email'])['collaborator_ids_send_email']     
        event_id = ids[0]
        
        # --Crear el Wizard de Envio de Correos
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        wizard_obj = self.pool.get('kemas.send.notification.event.wizard')
        wizard_line_obj = self.pool.get('kemas.send.notification.event.line.wizard')
        collaborator_obj = self.pool.get('kemas.collaborator')
        
        vals = {'state' : 'load', 'event_id' : event_id, 'sending_emails':sending_emails}
        wizard_id = wizard_obj.create(cr, uid, vals)
        event_lines = event_line_obj.read(cr, uid, event_line_ids, ['send_email_state', 'sent_date', 'collaborator_id'], context)
        for event_line in event_lines:
            collaborator = collaborator_obj.read(cr, uid, event_line['collaborator_id'][0], ['id', 'email'], context)
            if event_line['send_email_state'] == 'Sent':
                send_email = False
                if sending_emails:
                    state = 'Successful'
                else:
                    state = 'Sent'
            elif event_line['send_email_state'] == 'Waiting':
                send_email = True
                state = 'Waiting'
            elif event_line['send_email_state'] == 'Error':
                send_email = True
                state = 'Error'
            elif event_line['send_email_state'] == 'Timeout':
                send_email = True
                state = 'Timeout'
                
            if sending_emails and collaborator['id'] not in collaborator_ids_send_email:
                continue
            wizard_line_obj.create(cr, uid, {
                        'wizard_id': wizard_id,
                        'collaborator_id': collaborator['id'],
                        'email' : collaborator['email'],
                        'state': state,
                        'send_email': send_email,
                        'sent_date' : event_line['sent_date'],
                        'event_line_id': event_line['id'],
                        })
        
        return{
            'context': context,
            'res_id' : wizard_id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kemas.send.notification.event.wizard',
            'type': 'ir.actions.act_window',
            'target':'new',
            }

    def get_collaborators_registered(self, cr, uid, event_id):
        sql = """
            SELECT collaborator_id, checkout_id FROM kemas_attendance 
            WHERE event_id = %d and register_type = 'checkin'
        """ % (event_id)
        cr.execute(sql)
        result_query = cr.dictfetchall()
        for record in result_query:
            if record['checkout_id'] is None:
                record['checkout_id'] = False
        return result_query
    
    def get_collaborators_by_event(self, cr, uid, event_id):
        def is_registered(event_id, collaborator_id):
            sql = """
                SELECT checkout_id FROM kemas_attendance 
                WHERE event_id = %d and collaborator_id = %d and register_type = 'checkin'
                """ % (event_id, collaborator_id)
            cr.execute(sql)
            result_query = cr.dictfetchall()
            if result_query:
                if result_query[0]['checkout_id'] is None:
                    result_query[0]['checkout_id'] = False
                return result_query[0]
            else:
                return False
        
        sql = """
            SELECT cl.id, cl.name, U.login as username 
            FROM kemas_collaborator AS cl
            JOIN res_users as U on (U.id = cl.user_id)
            WHERE cl.id IN
            (
                SELECT collaborator_id FROM kemas_event_collaborator_line 
                WHERE event_id = %d
            )
        """ % (event_id)
        cr.execute(sql)
        result_query = cr.dictfetchall()
        collaborators = []
        
        for collaborator in result_query:
            collaborator['registered'] = is_registered(event_id, collaborator['id'])
            collaborators.append(collaborator)
        
        res = []
        l2 = []
        for collaborator in collaborators:
            if collaborator['registered']:
                l2.append(collaborator)
            else:
                res.append(collaborator)
        for collaborator in l2:
            res.append(collaborator)
        
        return res
        
    def get_next_event(self, cr, uid):
        from datetime import datetime
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        now = datetime.strptime(extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
        date_today = "%s-%s-%s %s" % (extras.completar_cadena(now.year, 4), extras.completar_cadena(now.month), extras.completar_cadena(now.day), "00:00:00")
        def get_event(except_list):
            # [0] Event_id
            # [1] Service name
            # [2] Date start
            # [3] Time entry
            sql = """
                SELECT ev.id,sv.name,ev.date_start,sv.time_entry
                FROM kemas_event as ev
                INNER JOIN kemas_service as sv ON (sv.id = ev.service_id)
                WHERE 
                    ev.date_start > '%s'
                    AND
                    ev.state IN ('on_going')
                    AND 
                    ev.id NOT IN %s
                ORDER BY ev.date_start
                LIMIT 1
            """ % (date_today, extras.convert_to_tuple_str(except_list))
            cr.execute(sql)
            result_query = cr.fetchall()
            res = []
            if result_query:   
                res = result_query[0]
            return res
        
        event_ids = []
        event = []
        valid = False
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        while valid == False:
            event = get_event(event_ids)
            if event == []:
                valid = True
            else:
                dt = datetime.strptime(extras.convert_to_tz(event[2], tz), '%Y-%m-%d %H:%M:%S')
                date_event = "%s-%s-%s %s" % (extras.completar_cadena(dt.year, 4), extras.completar_cadena(dt.month), extras.completar_cadena(dt.day), "00:00:00")
                if date_event == date_today:
                    if event[3] > float(now.hour) + float(now.minute) / 60:
                        valid = True
                    else:
                        valid = False
                        event_ids.append(event[0])
                else:
                    valid = True
        if event:  
            date = datetime.strptime(extras.convert_to_tz(event[2], tz), '%Y-%m-%d %H:%M:%S')
            time_entry = extras.convert_float_to_hour_format(event[3], True)
            date = "%s-%s-%s %s" % (extras.completar_cadena(date.year, 4), extras.completar_cadena(date.month), extras.completar_cadena(date.day), time_entry)
            date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            res_date = date - now
            res = {
                    'name' : event[1],
                    'seconds_remaining' : res_date.total_seconds()
                    }
            return res
        return False
            
    def get_today_events(self, cr, uid):
        from datetime import datetime
        
        def get_events():
            start = '%s 00:00:00' % ((datetime.now() - timedelta(days=1)).date().__str__())
            stop = '%s 23:59:59' % ((datetime.now() + timedelta(days=1)).date().__str__())
            sql = """
                SELECT ev.id,ev.date_start,sv.id
                FROM kemas_event as ev
                INNER JOIN kemas_service as sv ON (sv.id = ev.service_id)
                WHERE 
                    ev.date_start between '%s' AND '%s'
                    AND
                    ev.state IN ('on_going','closed')
                ORDER BY ev.date_start
            """ % (start, stop)
            cr.execute(sql)
            result_query = cr.fetchall()
            res = [] 
            for event in result_query:
                tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
                if extras.convert_to_tz(event[1], tz, res=1) == extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz, res=1):
                    event_ent = {
                                 'id': event[0],
                                 'date_start': event[1],
                                 'service_id': event[2],
                                 }
                    res.append(event_ent)
            return res
        
        events = get_events()
        service_obj = self.pool.get('kemas.service')
        res = []
        for event in events:
            service = super(kemas_service, service_obj).read(cr, uid, event['service_id'])
            line_event = {}
            line_event['id'] = event['id']
            line_event['name'] = service['name']
            
            #----Hora de Entrada-----------------------------------------------------------------
            time_entry = extras.convert_float_to_hour_format(service['time_entry'])
            line_event['time_entry'] = time_entry
            hour = str(time_entry)[:2]
            minutes = str(time_entry)[3:5]
            time_entry = int(minutes) + int(hour) * 60
            line_event['time_entry_int'] = time_entry
            
            #----Hora Limite de Registro a Tiempo------------------------------------------------
            time_register = extras.convert_float_to_hour_format(service['time_register'])
            line_event['time_register'] = time_register
            hour = str(time_register)[:2]
            minutes = str(time_register)[3:5]
            time_register = int(minutes) + int(hour) * 60
            line_event['time_register_int'] = time_entry + time_register
            
            #----Hora Limite de Registro---------------------------------------------------------
            time_limit = extras.convert_float_to_hour_format(service['time_limit'])
            line_event['time_limit'] = time_limit
            hour = str(time_limit)[:2]
            minutes = str(time_limit)[3:5]
            time_limit = int(minutes) + int(hour) * 60
            line_event['time_limit_int'] = time_entry + time_limit
            
            #----Hora de Inicio------------------------------------------------------------------
            time_start = extras.convert_float_to_hour_format(service['time_start'])
            line_event['time_start'] = time_start
            hour = str(time_start)[:2]
            minutes = str(time_start)[3:5]
            time_start = int(minutes) + int(hour) * 60
            line_event['time_start_int'] = time_start
            
            #----Hora de Finalizacion------------------------------------------------------------
            time_end = extras.convert_float_to_hour_format(service['time_end'])
            line_event['time_end'] = time_end
            hour = str(time_end)[:2]
            minutes = str(time_end)[3:5]
            time_end = int(minutes) + int(hour) * 60
            line_event['time_end_int'] = time_end
            
            if event['id'] == self.get_current_event(cr, uid):
                line_event['current_event'] = True
            else:
                line_event['current_event'] = False 
            res.append(line_event)
        return res
        
    def get_current_event(self, cr, uid, extra_info=False):
        result = False
        service_obj = self.pool.get('kemas.service')
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        
        search_args = [('date_init', '<=', now), ('date_stop', '>=', now), ('state', '=', 'on_going')]
        event_ids = super(kemas_event, self).search(cr, uid, search_args, limit=1)
        if not event_ids:
            return result
        
        event = self.read(cr, uid, event_ids[0], ['service_id'])
        service = service_obj.read(cr, uid, event['service_id'][0], [])
        
        # Convertir la hora de entrada a Entero
        time_entry = extras.convert_float_to_hour_format(service['time_entry'])
        hour = str(time_entry)[:2]
        minutes = str(time_entry)[3:5]
        time_entry = int(minutes) + int(hour) * 60
        
        # Convertir la hora actual a Entero
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
        hour = str(now)[11:13]
        minutes = str(now)[14:16]
        now = int(minutes) + int(hour) * 60
        
        # Genrar la hora limite
        time_limit = extras.convert_float_to_hour_format(service['time_limit'])
        hour = str(time_limit)[:2]
        minutes = str(time_limit)[3:5]
        time_limit = int(minutes) + int(hour) * 60
        
        # Genrar la hora para registro puntual de puntos
        time_register = extras.convert_float_to_hour_format(service['time_register'])
        hour = str(time_register)[:2]
        minutes = str(time_register)[3:5]
        time_register = int(minutes) + int(hour) * 60
        
        # Validar si el evento es valido para registro de asistencia o no
        if time_entry <= now and (time_entry + time_limit) > now:
            if extra_info:
                result = {
                          'current_event_id': event['id'],
                          'minutes_remaining': (time_entry + time_limit) - now,
                          'time_entry': time_entry,
                          'now': now,
                          'time_limit': time_limit,
                          'time_register': time_register,
                          }
            else:
                result = event['id']
        return result
    
    def build_members(self, cr, uid, ids, context={}):
        line_obj = self.pool['kemas.event.collaborator.line']
        c_obj = self.pool['kemas.collaborator']
        events = self.read(cr, uid, ids, ['event_collaborator_line_ids'])
        count = 0
        for event in events:
            lines = line_obj.read(cr, uid, event['event_collaborator_line_ids'], ['collaborator_id'])
            members = [c_obj.read(cr, uid, x['collaborator_id'][0], ['user_id'])['user_id'][0] for x in lines]
            vals = {'members' : [(6, 0, members)]}
            if context.get('rebuild_import_data'):
                # Para Importa Colaboradores
                users = self.pool['res.users'].read(cr, uid, members, ['partner_id'])
                vals ['message_follower_ids'] = [(6, 0, [x['partner_id'][0] for x in users])]
                count += 1
                _logger.info("Reprocesando Eventos: %d de %d" % (count, len(ids)))
            super(kemas_event, self).write(cr, uid, ids, vals, context)
        return True
 
    def write(self, cr, uid, ids, vals, context={}):
        if type(ids[0]).__name__ == 'dict':
            if ids[0].has_key('res_id'):
                ids = [ids[0]['res_id']]
        event = super(osv.osv, self).read(cr, uid, ids[0], [])
        if not context.get('tz'):
            context['tz'] = self.pool['kemas.func'].get_tz_by_uid(cr, uid)
            
        if event['sending_emails']:
            raise osv.except_osv(u'¡Operación no válida!', _('You can not make changes to this event as they send notification e-mails.'))
        written = False

        if vals.get('priority', False):
            written = True
        elif vals.get('color', False):
            written = True
        elif vals.get('message_follower_ids', False):
            written = True
        elif vals.get('stage_id', False):
            stage_obj = self.pool.get('kemas.event.stage')
            stage = stage_obj.read(cr, uid, vals['stage_id'])
            if stage['sequence'] == 1:  # draft
                if event['state'] == 'on_going':
                    vals['state'] = 'draft'
                    written = True
                else:
                    raise osv.except_osv(u'¡Operación no válida!', _(''))
            if stage['sequence'] == 2:  # on_going
                if event['state'] == 'draft':
                    vals['state'] = 'on_going'
                    written = True
                else:
                    raise osv.except_osv(u'¡Operación no válida!', _(''))
            elif stage['sequence'] == 3:  # closed
                raise osv.except_osv(u'¡Operación no válida!', _(''))
            elif stage['sequence'] == 4:  # canceled
                raise osv.except_osv(u'¡Operación no válida!', _('')) 
            else:
                written = True
        if context.has_key('change_service') == False:
            if written:
                cr.commit()
                super(kemas_event, self).write(cr, uid, ids, vals, context)
                cr.commit() 
                return True
            
            if event['state'] == 'closed':raise osv.except_osv(u'¡Operación no válida!', _('The event has been Closed and can not be changed.'))
            if event['state'] == 'canceled':raise osv.except_osv(u'¡Operación no válida!', _('The event has been Canceled and can not be changed.'))
            if event['state'] == 'on_going':raise osv.except_osv(u'¡Operación no válida!', _('The event is on going and can not be changed.'))
        else:
            if context['change_service'] == False:
                if written:
                    cr.commit()
                    super(kemas_event, self).write(cr, uid, ids, vals, context)
                    cr.commit()
                    return True
                if event['state'] == 'closed':raise osv.except_osv(u'¡Operación no válida!', _('The event has been Closed and can not be changed.'))
                if event['state'] == 'canceled':raise osv.except_osv(u'¡Operación no válida!', _('The event has been Canceled and can not be changed.'))
                if event['state'] == 'on_going':raise osv.except_osv(u'¡Operación no válida!', _('The event is on going and can not be changed.'))
        service_obj = self.pool.get('kemas.service')
        #---------------------------------------------------------------------------------------------------------------------------
        #--Change Date start y date stop---------------------------------------------------------------------------------------------
        service = service_obj.read(cr, uid, event['service_id'][0], [])
        if vals.has_key('service_id'):
            if vals['service_id']:
                service = service_obj.read(cr, uid, vals['service_id'], [])   
        if vals.get('date_start'):
            date_start = vals['date_start']
        else:
            date_start = extras.convert_to_tz(event['date_start'], context['tz'])
        dates_dic = extras.convert_to_format_date(date_start, service['time_entry'], service['time_start'], service['time_end'], context['tz'])
        if vals.get('date_start') and not self.validate_past_date(cr, uid, extras.convert_to_tz(dates_dic['date_start'], context['tz']), context):
            raise osv.except_osv(u'¡Operación no válida!', u"No se puede poner un evento en una fecha que ya pasó")
        
        vals['date_start'] = dates_dic['date_start']
        vals['date_stop'] = dates_dic['date_stop']
        vals['date_init'] = dates_dic['date_init']
        
        result = super(kemas_event, self).write(cr, uid, ids, vals, context)
        self.build_members(cr, uid, ids, context)
        return result
         
    def replace_collaborators(self, cr, uid, event_id, replaceds, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        users_obj = self.pool.get('res.users')
        old_members = self.read(cr, uid, event_id, ['members'])['members']
        old_followers = self.read(cr, uid, event_id, ['message_follower_ids'])['message_follower_ids']        
        for replaced in replaceds:
            collaborator_id = replaced['collaborator_id']
            replace_id = replaced['replace_id']
            replace_user_id = super(kemas_collaborator, collaborator_obj).read(cr, uid, replace_id, ['user_id'])['user_id'][0]
            collaborator_user_id = super(kemas_collaborator, collaborator_obj).read(cr, uid, collaborator_id, ['user_id'])['user_id'][0]
            if replace_user_id not in old_members:
                super(osv.osv, self).write(cr, uid, [event_id], {'members' : [(4, replace_user_id)]}, context)
            super(osv.osv, self).write(cr, uid, [event_id], {'members' : [(3, collaborator_user_id)]}, context)
            # Modificar Seguidores
            replace_partner_id = users_obj.read(cr, uid, replace_user_id, ['partner_id'])['partner_id'][0]
            collaborator_partner_id = users_obj.read(cr, uid, collaborator_user_id, ['partner_id'])['partner_id'][0]
            if replace_partner_id not in old_followers:
                super(osv.osv, self).write(cr, uid, [event_id], {'message_follower_ids' : [(4, replace_partner_id)]}, context)
            super(osv.osv, self).write(cr, uid, [event_id], {'message_follower_ids' : [(3, collaborator_partner_id)]}, context)
            self.write_log_replace(cr, uid, event_id, collaborator_id, replace_id, replaced['record_id'])
        return True
        
    def validate_past_date(self, cr, uid, date_start, context={}):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        result = True
        if not context.get('tz'):
            context['tz'] = self.pool.get('kema.func').get_tz_by_uid(cr, uid)
        now = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), context['tz'])
        if now > date_start:
            result = False
        return result
    
    def copy(self, cr, uid, record_id, default=None, context={}):
        if default is None or not default or not isinstance(default, (dict)): default = {}
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        dict_update = {
                       'code': False,
                       'comments': False,
                       'state': 'creating',
                       'mailing': False,
                       'sending_emails': False,
                       'attendance_ids': False,
                       }
        dict_update['date_start'] = time.strftime("%Y-%m-%d")
        default.update(dict_update)
        context['copy'] = True
        res_id = super(kemas_event, self).copy(cr, uid, record_id, default, context=context)
        line_obj = self.pool['kemas.event.collaborator.line']
        event = self.read(cr, uid, record_id, ['event_collaborator_line_ids'])
        lines = line_obj.read(cr, uid, event['event_collaborator_line_ids'])
        for line in lines:
            vals = {
                    'collaborator_id': line['collaborator_id'][0],
                    'event_id': res_id
                    }
            line_obj.create(cr, uid, vals)
        self.write(cr, uid, [res_id], {'collaborators_loaded': True}, context)
        line_ids = line_obj.search(cr, uid, [('event_id', '=', res_id)])
        collaborator_ids = line_obj.read(cr, uid, line_ids, ['collaborator_id'])
        self.write(cr, uid, [res_id], {'line_ids': collaborator_ids}, context)
        return res_id
    
    def create(self, cr, uid, vals, context={}):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        vals['date_create'] = vals.get('date_create', str(time.strftime("%Y-%m-%d %H:%M:%S")))
        vals['state'] = vals.get('state', 'draft')
        vals['count'] = 1
        #--Crear Date start y date stop---------------------------------------------------------------------------------------------
        service = self.pool['kemas.service'].read(cr, uid, vals['service_id'], [])
        if not context['tz']:
            context['tz'] = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        
        dates_dic = extras.convert_to_format_date(vals['date_start'], service['time_entry'], service['time_start'], service['time_end'], context['tz'])
        vals['date_start'] = dates_dic['date_start']
        vals['date_stop'] = dates_dic['date_stop']
        vals['date_init'] = dates_dic['date_init']
        if not context.get('copy') and not self.validate_past_date(cr, uid, vals['date_start'], context):
            raise osv.except_osv(u'¡Operación no válida!', u"No se puede crear un evento en una fecha que ya pasó")
        
        context['mail_create_nolog'] = True
        res_id = super(kemas_event, self).create(cr, uid, vals, context)
        collaborator_line_ids = self.read(cr, uid, [res_id], ['event_collaborator_line_ids'])
        line_ids = []
        for line in collaborator_line_ids:
            line_ids += line['event_collaborator_line_ids']
        lines = self.pool['kemas.event.collaborator.line'].read(cr, uid, line_ids, ['collaborator_id'])
        members = []
        for line in lines:
            collaborator_id = line['collaborator_id'][0]
            user_id = super(kemas_collaborator, self.pool.get('kemas.collaborator')).read(cr, uid, collaborator_id, ['user_id'])['user_id'][0]
            members.append(user_id)
        vals = {'members' : [(6, 0, members)]}
        super(kemas_event, self).write(cr, uid, [res_id], vals)
        
        # Escribir log
        ctx = {'notify_all_followers': True, 'delete_uid_followers': True, 'record_name': 'del Evento'}
        self.pool['mail.th'].log_create(cr, uid, res_id, self._name, context=ctx)
        return res_id
    
    def close_this_event(self, cr, uid, ids, context={}): 
        self.close_event(cr, uid, ids[0])
        
    def get_past_events(self, cr, uid, drafts=True):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if drafts:
            event_ids = super(osv.osv, self).search(cr, uid, [('date_stop', '<', now), ('state', 'in', ['draft', 'on_going'])])
        else:
            event_ids = super(osv.osv, self).search(cr, uid, [('date_stop', '<', now), ('state', 'in', ['on_going'])])
        return event_ids
        
    def close_past_events(self, cr, uid, context={}):
        threaded_sending = threading.Thread(target=self._close_past_events, args=(cr.dbname , uid))
        threaded_sending.start()
        
    def _close_past_events(self, db_name, uid, context={}):
        db = pooler.get_db(db_name)
        cr = db.cursor()
        
        with Environment.manage():
            event_ids = self.get_past_events(cr, uid, False)
            for event_id in event_ids:
                self.close_event(cr, uid, event_id)
                event_name = self.name_get(cr, uid, [event_id])[0][1]
                cr.commit()
                _logger.info('Cerrado evento [%s]', event_name)
                
    def close_event(self, cr, uid, event_id, context={}):   
        def send_notifications(self):
            def send(self, db_name, uid):
                db = pooler.get_db(db_name)
                cr = db.cursor()
                cr.commit()
                config_obj = self.pool.get('kemas.config')
                count = 0
                for collaborator in noticaciones['collaborators']:
                    count += 1
                    config_obj.send_email_event_completed(cr, uid, noticaciones['service_id'], noticaciones['event_id'], collaborator['id'], collaborator['type'])
                _logger.info('[%d] Notificaciones de fin de evento enviadas', count)
                cr.commit()
                 
            threaded_sending = threading.Thread(target=send, args=(self, cr.dbname, uid))
            threaded_sending.start()
        
        with Environment.manage():
            service_obj = self.pool.get('kemas.service')
            line_obj = self.pool.get('kemas.event.collaborator.line')
            attendance_obj = self.pool.get('kemas.attendance')
            collaborator_obj = self.pool.get('kemas.collaborator')
            history_points_obj = self.pool.get('kemas.history.points')
            #------------------------------------------------------------------------------
            event = self.read(cr, uid, event_id, ['place_id', 'service_id', 'date_start', 'not_attend_points', 'close_to_end', 'message_follower_ids'])
            service_id = event['service_id'][0]
            service = service_obj.read(cr, uid, service_id, [])
            date_start = self.read(cr, uid, event_id, ['date_start'])['date_start'] 
            # Verificar si el evento esta configurado para inactivar el servicio al finalizar
            if event['close_to_end']:
                service_obj.do_inactivate(cr, uid, [service_id])
            vals = {
                    'state' : 'closed',
                    'color' : 5,
                    'date_close' : str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    #--Summary----------------------------------------------
                    'rm_service': service['name'],
                    'rm_close_to_end' : event['close_to_end'],
                    'rm_place': event['place_id'][1],
                    'rm_date': date_start,
                    'rm_time_start': service['time_start'],
                    'rm_time_end': service['time_end'],
                    'rm_time_entry': service['time_entry'],
                    'rm_time_register': service['time_register'],
                    'rm_time_limit': service['time_limit'],
                    }
            stage_obj = self.pool.get('kemas.event.stage')
            stage_ids = stage_obj.search(cr, uid, [('sequence', '=', 3)])
            if stage_ids:
                vals['stage_id'] = stage_ids[0]
            super(osv.osv, self).write(cr, uid, [event_id], vals)
            #---Verificar las personas que asistieron al servicio-----------------------------
            # Armar una lista de los colaboradores que debian asistir.
            programados = []
            line_ids = self.read(cr, uid, event_id, ['event_collaborator_line_ids'])['event_collaborator_line_ids']
            lines = line_obj.read(cr, uid, line_ids, ['collaborator_id'])
            for line in lines:
                programados.append(line['collaborator_id'][0])
            # Armar una lista de los colaboradores que asistiron.
            noticaciones = {}
            noticaciones['event_id'] = event_id
            noticaciones['service_id'] = service_id
            noticaciones['collaborators'] = []
            
            asistentes = []
            attendance_ids = attendance_obj.search(cr, uid, [('event_id', '=', event_id)])
            attendances = attendance_obj.read(cr, uid, attendance_ids, ['collaborator_id', 'type'])
            for attendance in attendances:
                asistentes.append(attendance['collaborator_id'][0])
                #---Agregar un colaborador a la lista de notificationes
                collaborator = {
                                'id': attendance['collaborator_id'][0],
                                'type':attendance['type']
                                }
                noticaciones['collaborators'].append(collaborator)
            
            inasistentes = list(set(programados) - set(asistentes))
            for inasistente in inasistentes:
                # Escribir registro de Asitencia
                summary = 'Inasistencia.'
                seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Attendance'), ])[0]
                attendance_vals = {
                                   'code' : str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id)),
                                   'collaborator_id': inasistente,
                                   'type': 'absence',
                                   'event_id': event_id,
                                   'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                   'summary': summary,
                                   'user_id': uid
                                   }
                attendance_id = super(kemas_attendance, attendance_obj).create(cr, uid, attendance_vals)
                
                collaborator = collaborator_obj.read(cr, uid, inasistente, ['points'])
                current_points = str(collaborator['points'])
                
                nombre_del_evento = unicode(event['service_id'][1])
                time_start = self.pool.get('kemas.service').read(cr, uid, event['service_id'][0], ['time_start'])['time_start']
                time_start = extras.convert_float_to_hour_format(time_start)
                description = "Inasistencia al Servicio: '%s' del %s, programado para las %s." % (nombre_del_evento, extras.convert_date_format_long_str(event['date_start']), time_start)
                new_points = int(current_points) - int(event['not_attend_points'])
                change_points = str(event['not_attend_points'])
                
                # Escribir puntaje
                super(kemas_collaborator, collaborator_obj).write(cr, uid, [inasistente], {'points': int(new_points)})
                
                history_summary = '-' + str(change_points) + " Puntos. Antes " + str(current_points) + " ahora " + str(new_points) + " Puntos."
                vals_history_points = {
                                       'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                                       'attendance_id': attendance_id,
                                       'collaborator_id': inasistente,
                                       'type': 'decrease',
                                       'description': description,
                                       'summary': history_summary,
                                       'points': abs(int(change_points)) * -1,
                                       }
                history_points_obj.create(cr, uid, vals_history_points)
                # Agregar un colaborador a la lista de notificationes (Inasistente)
                collaborator = {'id': inasistente, 'type':'absence'}
                noticaciones['collaborators'].append(collaborator)
                cr.commit()
            cr.commit()
            self.pool['mail.th'].log_change_state(cr, uid, event_id, self._name, 'Evento Finalizado', 'En Curso', 'Cerrado', context=context)
            send_notifications(self)
            
    def cancel_event(self, cr, uid, ids, context={}): 
        service_obj = self.pool.get('kemas.service')
        for record_id in ids:
            event = self.read(cr, uid, record_id, ['place_id', 'message_follower_ids'])
            service_id = self.read(cr, uid, record_id, ['service_id'])['service_id'][0]
            service = service_obj.read(cr, uid, service_id, [])
            date_start = self.read(cr, uid, record_id, ['date_start'])['date_start'] 
            stage_ids = self.pool['kemas.event.stage'].search(cr, uid, [('sequence', '=', 4)])
            vals = {
                    'state' : 'canceled',
                    'color' : 2,
                    'stage_id': stage_ids and stage_ids[0] or False,
                    'date_cancel' : str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    #--Summary----------------------------------------------
                    'rm_service': service['name'],
                    'rm_place': event['place_id'][1],
                    'rm_date': date_start,
                    'rm_time_start': service['time_start'],
                    'rm_time_end': service['time_end'],
                    'rm_time_entry': service['time_entry'],
                    'rm_time_register': service['time_register'],
                    'rm_time_limit': service['time_limit']
                    }
            super(kemas_event, self).write(cr, uid, [record_id], vals)
            self.pool['mail.th'].log_change_state(cr, uid, record_id, self._name, 'Evento Cancelado', 'En Curso', 'Cancelado', context=context)
        return True
    
    def write_log_delete_replace(self, cr, uid, event_id, collaborator_id, replaced_id, replace_id, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.get_nick_name(cr, uid, collaborator_id)
        replaced = collaborator_obj.get_nick_name(cr, uid, replaced_id)
        body = u'''
        <div>
            <span>
                <font color="red">%s <b>#%s</b> <b>%s</b></font>
            </span>
            <div>     • <b>%s</b>: %s <b>%s</b> %s</div>
        </div>
        ''' % ('Reemplazo de Colaboradores', str(replace_id), 'ANULADO', 'Reemplazo', collaborator, 'por', replaced)
        replaced_id = collaborator_obj.get_partner_id(cr, uid, replaced_id)
        collaborator_id = collaborator_obj.get_partner_id(cr, uid, collaborator_id)
        return self.pool['mail.th'].log_write(cr, uid, event_id, self._name, body, [replaced_id, collaborator_id], context=context)
    
    def write_log_replace(self, cr, uid, event_id, collaborator_id, replaced_id, replace_id, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.get_nick_name(cr, uid, collaborator_id)
        replaced = collaborator_obj.get_nick_name(cr, uid, replaced_id)
        body = u'''
        <div>
            <span>
                <font color="blue">%s <b>#%s</b></font>
            </span>
            <div>     • <b>%s</b>: %s <b>%s</b> %s</div>
        </div>
        ''' % ('Reemplazo de Colaboradores', str(replace_id), 'Reemplazo', collaborator, 'por', replaced)
        replaced_id = collaborator_obj.get_partner_id(cr, uid, replaced_id)
        collaborator_id = collaborator_obj.get_partner_id(cr, uid, collaborator_id)
        return self.pool['mail.th'].log_write(cr, uid, event_id, self._name, body, [replaced_id, collaborator_id], context=context)
    
    def check_crossing(self, cr, uid, event_id, context={}):
        result = True
        event = self.read(cr, uid, event_id, ['date_start', 'date_stop'])
        event_ids = self.search(cr, uid, [('date_start', '<=', event['date_start']), ('date_stop', '>=', event['date_start']), ('state', 'in', ['on_going'])])
        if event_ids and event_ids != event_id:
            result = False
        else:
            event_ids = self.search(cr, uid, [('date_start', '<=', event['date_stop']), ('date_stop', '>=', event['date_stop']), ('state', 'in', ['on_going'])])
            if event_ids and event_ids[0] != event_id:
                result = False
        return result
    
    def on_going(self, cr, uid, ids, context={}):
        if type(ids).__name__ in ['int', 'long']:
            ids = list(ids)
            
        records = self.read(cr, uid, ids, ['event_collaborator_line_ids', 'members', 'message_follower_ids', 'code', 'date_start'])
        for record in records:  
            if not self.validate_past_date(cr, uid, record['date_start'], context):
                raise osv.except_osv(u'¡Operación no válida!', u"No se puede poner en curso un evento en una fecha que ya pasó")
            
            if not self.check_crossing(cr, uid, record['id'], context):
                raise osv.except_osv(u'¡Operación no válida!', u"No se puede poner en curso un evento porque ya hay otro en la misma fecha")
            
            if not record['event_collaborator_line_ids']:
                raise osv.except_osv(u'¡Operación no válida!', u"Antes de poner el evento en curso primero agregue los colaboradores.")
                
            user_obj = self.pool.get('res.users')
            members = user_obj.read(cr, uid, record['members'])
            collaborator_partner_ids = []
            for member in members:
                if member['partner_id']:
                    collaborator_partner_ids.append(member['partner_id'][0])
            vals = {
                    'message_follower_ids' : [(6, 0, collaborator_partner_ids)],
                    'state' : 'on_going',
                    'color' : 4
                    }
            stage_obj = self.pool.get('kemas.event.stage')
            stage_ids = stage_obj.search(cr, uid, [('sequence', '=', 2)])
            if stage_ids:
                vals['stage_id'] = stage_ids[0]
            if not record['code']:
                seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Event'), ])[0]
                vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
            super(kemas_event, self).write(cr, uid, ids, vals)
            self.pool['mail.th'].log_change_state(cr, uid, record['id'], self._name, 'Evento en Curso', 'Borrador', 'En Curso', context=context)
        return True
        
    def draft(self, cr, uid, ids, context={}):
        if super(osv.osv, self).read(cr, uid, ids[0], ['sending_emails'])['sending_emails']:
            raise osv.except_osv(u'¡Operación no válida!', _('You can not make changes to this event as they send notification e-mails.'))
        stage_ids = self.pool['kemas.event.stage'].search(cr, uid, [('sequence', '=', 1)])
        vals = {
                'state': 'draft',
                'color': 7,
                'stage_id': stage_ids and stage_ids[0] or False
                }
        super(kemas_event, self).write(cr, uid, ids, vals)
        for record_id in ids:
            self.pool['mail.th'].log_change_state(cr, uid, record_id, self._name, 'Evento Pausado', 'En Curso', 'Borrador', context=context)
        return True
        
    def get_percentage(self, cr, uid, ids, name, arg, context={}):
        def get_percent_progress_event(event_id):
            service_obj = self.pool.get('kemas.service')
            #-----------------------------------------------------------------------------------------------------
            event = self.read(cr, uid, event_id, ['service_id', 'state', 'date_start'])
            service = service_obj.read(cr, uid, event['service_id'][0], ['time_entry', 'time_start', 'time_end'])
            fecha_evento = datetime.datetime.strptime(event['date_start'], '%Y-%m-%d %H:%M:%S')
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            # if event['state']=='on_going' and fecha_evento.date().__str__() <= extras.convert_to_tz(datetime.datetime.now().__str__(),tz,res=1):
            if event['state'] == 'on_going' and fecha_evento.date().__str__() <= datetime.datetime.now().__str__():
                try:
                    total_minutes = service['time_end'] - service['time_start']
                    now_UTC = extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
                    now_minutes = extras.convert_hour_format_to_float(now_UTC[-8:])
                    after_minutes = now_minutes - service['time_start']
                    progress = float(after_minutes * 100) / float(total_minutes)
                    if progress < 0: 
                        progress = 0
                    if progress > 100:
                        progress = 100
                    return progress
                except: return 200
            else:
                return 200
                
        result = {}
        for event_id in ids:
            result[event_id] = get_percent_progress_event(event_id)
        return result
    
    def mailing(self, cr, uid, ids, name, arg, context={}):
        def mailing():
            config_obj = self.pool.get('kemas.config')
            config_id = config_obj.get_correct_config(cr, uid)
            if config_id:
                config = config_obj.read(cr, uid, config_id, ['mailing', 'use_message_event'])
                if config['mailing'] and config['use_message_event']:
                    return True
                else:
                    return False
            else:
                return False
        result = {}
        for event_id in ids:
            result[event_id] = mailing()
        return result
    
    def set_priority(self, cr, uid, ids, priority):
        """Set task priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, *args):
        """Set task priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set task priority to normal
        """
        return self.set_priority(cr, uid, ids, '2')
    
    def _get_time_start_str(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['time_start'])
        for record in records:
            result[record['id']] = extras.convert_float_to_hour_format(record['time_start'])
        return result
    
    def _get_time_end_str(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['time_end'])
        for record in records:
            result[record['id']] = extras.convert_float_to_hour_format(record['time_end'])
        return result
    
    def _get_event_date_str(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['time_start', 'time_end', 'date_start'])
        for record in records:
            time_start = extras.convert_float_to_hour_format(record['time_start'])
            time_end = extras.convert_float_to_hour_format(record['time_end'])
            result[record['id']] = "%s - %s" % (time_start, time_end)
        return result
    
    def _notification_status(self, cr, uid, ids, name, arg, context={}): 
            def notification_status(line_ids, sending_emails):
                if sending_emails:
                    return unicode('sending')
                lines = line_obj.read(cr, uid, line_ids, ['send_email_state', 'collaborator_id'])
                
                collaborators_failed = ''
                pendings = 0
                sents = 0
                for line in lines:
                    if line['send_email_state'] in ['Timeout', 'Error']:
                        collaborators_failed += line['collaborator_id'][1] + ','
                    elif line['send_email_state'] in ['Waiting']:
                        pendings += 1
                    elif line['send_email_state'] in ['Sent']:
                        sents += 1

                if collaborators_failed != '':
                    collaborators_failed = collaborators_failed[:len(collaborators_failed) - 1]
                    res = 'No se ha podido notificar a: %s.' % collaborators_failed
                elif sents == len(line_ids):
                    res = unicode('ok')
                elif pendings == len(line_ids):
                    res = unicode('pending')
                else:
                    res = unicode('pending')
                return res
             
            result = {}
            records = super(osv.osv, self).read(cr, uid, ids, ['id', 'event_collaborator_line_ids', 'sending_emails'])
            line_obj = self.pool.get('kemas.event.collaborator.line')
            for record in records:
                result[record['id']] = notification_status(record['event_collaborator_line_ids'], record['sending_emails'])
            return result
    
    def refresh_notification_status(self, cr, uid, ids, context={}):
        return True
    
    def _event_day(self, cr, uid, ids, name, arg, context={}): 
        def event_day(date_start):
            date_start = extras.convert_to_tz(date_start, self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
            date_start = parse(date_start)
            day_number = int(date_start.strftime('%u'))
            if day_number == 1:
                res = 'Lunes'
            elif day_number == 2:
                res = 'Martes'
            elif day_number == 3:
                res = unicode('Miércoles', 'utf-8')
            elif day_number == 4:
                res = 'Jueves'
            elif day_number == 5:
                res = 'Viernes'
            elif day_number == 6:
                res = unicode('Sábado', 'utf-8')
            elif day_number == 7:
                res = 'Domingo'
            return res
         
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['date_start'])
        for record in records:
            result[record['id']] = event_day(record['date_start'])
        return result
    
    def _getcollaborator_ids(self, cr, uid, ids, name, arg, context={}): 
        def getcollaborator_ids(record):
            lines = self.pool.get('kemas.event.collaborator.line').read(cr, uid, record['event_collaborator_line_ids'], ['collaborator_id'])
            collaborator_ids = []
            for line in lines:
                collaborator_ids.append(line['collaborator_id'][0])
            return collaborator_ids
             
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id', 'event_collaborator_line_ids'])
        for record in records:
            result[record['id']] = getcollaborator_ids(record)
        return result
    
    def _count_all(self, cr, uid, ids, name, arg, context={}): 
        def count_all(record):
            result = {'attendance_count': 0, 'replacements_count': 0}
            # Contar los registros de asistencias
            cr.execute("select count(id) from kemas_attendance where event_id = %d" % record['id'])
            result['attendance_count'] = cr.fetchall()[0][0] 
            cr.execute("select count(id) from kemas_event_replacement where event_id = %d" % record['id'])
            result['replacements_count'] = cr.fetchall()[0][0] 
            return result
             
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['id'])
        for record in records:
            result[record['id']] = count_all(record)
        return result
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_start DESC,code'
    _name = 'kemas.event'
    _rec_name = 'service_id'
    _columns = {
        'service_id': fields.many2one('kemas.service', 'Service', required=True, help='Name of service relating to this event.', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'place_id': fields.many2one('kemas.place', 'Place', required=True, help='Place where the event was done.', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}, ondelete="restrict"),
        'code': fields.char('Code', size=32, help="Unique code that is assigned to each event", readonly=True),
        'comments': fields.text('Comments', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'information': fields.text('Information', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'state': fields.selection([
            ('creating', 'Creating'),
            ('draft', 'Draft'),
            ('on_going', 'On Going'),
            ('closed', 'Closed'),
            ('canceled', 'Canceled'),
            ], 'State'),
        'count': fields.integer('Count'),
        'collaborator_id': fields.many2one('kemas.collaborator', 'Colaborador', help='Colaborador por el cual se va filtrar los eventos'),
        'close_to_end': fields.boolean('Inactivar servicio al finalizar', required=False, states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}, help='Marque esta casilla para en el momento en el que finalize este evento el Servicio quede Inactivado y no se pueda usar de nuevo, esta función es util para cuando es un evento que solo se va a usar una sola vez.'),
        # Envio de Correos
        'mailing': fields.function(mailing, type='boolean', string='Mailing'),
        'sending_emails': fields.boolean('Sending emails?'),
        'collaborator_ids_send_email': fields.many2many('kemas.collaborator', 'kemas_event_collaborator_send_email_rel', 'event_id', 'collaborator_id', 'Collaborators to notify', help=''),
        # Fechas
        'date_init': fields.datetime('Date Init', help=''),
        'date_start': fields.datetime('Date', required=True, help='Scheduled date', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'date_stop': fields.datetime('Date Stop', help=''),
        'date_create': fields.datetime('Date create', help="Date the create"),
        'date_close': fields.datetime('Date close', help="Date the closed"),
        'date_cancel': fields.datetime('Date cancel', help="Date the canceled"),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        # Points
        'attend_on_time_points': fields.integer('Points for attend on time (+)', help="Points will increase to an collaborator for being on time to the service.", states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'late_points': fields.integer('Points for being late (-)', help="Point is decreased to a contributor for not arriving on time.", states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'not_attend_points': fields.integer('Points for not attend (-)', help="Point is decreased to a collaborator not to asist to a service.", states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'min_points': fields.integer('Minimum points', help="Minimum points required in order to participate in this event.", states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        # Summary fields
        'rm_service': fields.char('Service', size=255, help=""),
        'rm_close_to_end': fields.boolean('Inactivado al finalizar', required=False, help='Indica si el evento fue inactivado al finalizar el evento'),
        'rm_place': fields.char('Place', size=255, help=""),
        'rm_date': fields.datetime('Date', help=''),
        'rm_time_start': fields.float('Time start', help=""),
        'rm_time_end': fields.float('Time End', help=""),
        'rm_time_entry': fields.float('Time entry', help=""),
        'rm_time_register': fields.float('Time registrer', help=""),
        'rm_time_limit': fields.float('Time Limit', help=""),
        'team_id': fields.many2one('kemas.team', 'Team', help='Team that will participate in this event.', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'collaborators_loaded': fields.boolean('collaborators loaded?'),
        'notification_status': fields.function(_notification_status, type='char', string='Estado de notificaciones'),
        # One to Many Relations
        'event_collaborator_line_ids': fields.one2many('kemas.event.collaborator.line', 'event_id', 'Collaborators', help='Collaborators who participated in this event', states={'on_going':[('readonly', True)], 'closed':[('readonly', True)], 'canceled':[('readonly', True)]}),
        'collaborator_ids': fields.function(_getcollaborator_ids, type='one2many', relation="kemas.collaborator", string='Colaboradores'),
        # line_ids': fields.one2many('kemas.event.collaborator.line', 'event_id', 'Lines'),
        'line_ids': fields.text('Lines'),
        'attendance_ids': fields.one2many('kemas.attendance', 'event_id', 'Attendances', help='Attendance register', readonly=True),
        # Ralated
        'time_start': fields.related('service_id', 'time_start', type='char', string='Time start', readonly=True, store=False),
        'time_end': fields.related('service_id', 'time_end', type='char', string='Time end', readonly=True, store=False),
        'time_entry': fields.related('service_id', 'time_entry', type='char', string='Time entry', readonly=True, store=False),
        'time_limit': fields.related('service_id', 'time_limit', type='char', string='time limit', readonly=True, store=False),
        # Dashboard
        'progress': fields.function(get_percentage, type='float', string='Progress'),
        #-----KANBAN METHOD
        'priority': fields.selection([('4', 'Very Low'), ('3', 'Low'), ('2', 'Medium'), ('1', 'Important'), ('0', 'Very important')], 'Priority', select=True),
        'color': fields.integer('Color Index'),
        'stage_id': fields.many2one('kemas.event.stage', 'Stage', required=False),
        'photo_place': fields.related('place_id', 'photo', type='binary', store=True, string='photo'),
        'members': fields.many2many('res.users', 'event_user_rel', 'event_id', 'uid', 'Event Members', help=""),
        # Campos para cuando un evento finalice alamacer los datos que tenia el servicio en ese entoces
        'time_start_str': fields.function(_get_time_start_str, type='char', string='Time Start'),
        'time_end_str': fields.function(_get_time_end_str, type='char', string='Time end'),
        'event_date_str': fields.function(_get_event_date_str, type='char', string='Event date'),
        'event_day': fields.function(_event_day, type='char', string='Dia del evento'),
        # Contadores
        'replacements_count': fields.function(_count_all, type='integer', string='Reeplazos', multi=True),
        'attendance_count': fields.function(_count_all, type='integer', string='Asistencias', multi=True),
        }
    _sql_constraints = [
        ('event_code', 'unique (code)', 'This Code already exist!'),
        ]
    def get_default_attend_on_time_points(self, cr, uid, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        return int(config_obj.read(cr, uid, config_id, ['default_attend_on_time_points'])['default_attend_on_time_points'])
    
    def get_default_late_points(self, cr, uid, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        return int(config_obj.read(cr, uid, config_id, ['default_late_points'])['default_late_points'])
    
    def get_default_not_attend_points(self, cr, uid, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        return int(config_obj.read(cr, uid, config_id, ['default_not_attend_points'])['default_not_attend_points'])
    
    def load_collaborators(self, cr, uid, ids, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        
        event = self.read(cr, uid, ids[0], ['team_id', 'line_ids', 'min_points'])
        line_ids = line_obj.search(cr, uid, [('event_id', '=', ids[0])])
        line_obj.unlink(cr, uid, line_ids)
        
        args = [('state', '=', 'Active'), ('points', '>', int(event['min_points']))]
        if event['team_id']:
            args.append(('team_id', '=', event['team_id'][0]))
        
        collaborator_ids = collaborator_obj.search(cr, uid, args, context=context)
        for collaborator_id in collaborator_ids:
            vals = {
                    'collaborator_id': collaborator_id,
                    'event_id':ids[0]
                    }
            line_obj.create(cr, uid, vals) 
        self.write(cr, uid, ids, {'collaborators_loaded': True}, context)
        line_ids = line_obj.search(cr, uid, [('event_id', '=', ids[0])])
        collaborator_ids = line_obj.read(cr, uid, line_ids, ['collaborator_id'])
        self.write(cr, uid, ids, {'line_ids': collaborator_ids}, context)
        return True
    
    def _get_def_stage(self, cr, uid, context={}):
        stage_obj = self.pool.get('kemas.event.stage')
        stage_ids = stage_obj.search(cr, uid, [('sequence', '=', 1)])
        result = stage_ids and stage_ids[0] or False
        if not result:
            raise osv.except_osv(u'¡Advertencia!', u"No se han definido las etapas 'Stages'. para los eventos")
        return result
    
    _defaults = {
        'state':'creating',
        'attend_on_time_points': get_default_attend_on_time_points,
        'late_points': get_default_late_points,
        'not_attend_points': get_default_not_attend_points,
        'progress': 200,
        
        'priority': '2',
        'stage_id': _get_def_stage,
        'color': 6,
        'collaborators_loaded': True,
        'min_points': 1,
        'count': 1,
        }

    def _read_group_stage_id(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context={}):
        stage_obj = self.pool.get('kemas.event.stage')
        access_rights_uid = access_rights_uid or uid

        stage_ids = stage_obj.search(cr, uid, [('sequence', 'in', [1, 2])])
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        return result

    _group_by_full = {
        'stage_id': _read_group_stage_id
    }
    
class kemas_attendance(osv.osv):   
    def name_get(self, cr, uid, ids, context={}):
        records = self.read(cr, uid, ids, ['code', 'event_id'])
        res = []
        for record in records:
            name = "%s | Evento: %s" % (record['code'], unicode(record['event_id'][1]))
            res.append((record['id'], name))  
        return res
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False, lazy=True):
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_attendance, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby, lazy)
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context is None or not context or not isinstance(context, (dict)): context = {}
        
        collaborator_obj = self.pool.get('kemas.collaborator')
        user_obj = self.pool.get('res.users')
        group_obj = self.pool.get('res.groups')
        user_id = user_obj.search(cr, uid, [('id', '=', uid), ])
        groups_id = user_obj.read(cr, uid, user_id, ['groups_id'])[0]['groups_id']
        if not 1 in groups_id:
            kemas_collaborator_id = group_obj.search(cr, uid, [('name', '=', 'Kemas / Collaborator'), ])[0]
            if kemas_collaborator_id in groups_id: 
                collaborator_ids = collaborator_obj.search(cr, uid, [('user_id', '=', uid)])
                args.append(('collaborator_id', 'in', collaborator_ids))    
        if context.get('limit_records', False) and limit == None: 
            limit = context.get('limit_records', None)
            order = 'date desc'
        
        context['tz'] = context.get('tz', False) or self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date', '>=', range_dates['date_start']))
            args.append(('date', '<=', range_dates['date_stop']))  
        
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def _register_attendance(self, cr, uid, collaborator_id, username, context={}):
        '''
        r_1    Error en logeo
        r_2    Logueo correcto pero este Usuario no pertenece a un Colaborador
        r_3    El colaborador no esta asignado para este evento
        r_4    No hay eventos para registrar la asistencia
        r_5    Ya se registro al entrada
        r_6    Ya se registro la salida
        r_7    Codigo Inexistente
        '''
        vals = {'collaborator_id': collaborator_id}
        context['with_register_type'] = True
        res = self.create(cr, uid, vals, context)
        if res == 'no event':
            _logger.warn("'%s'. No hay Eventos registrar asistencias. %s" % (username, "REGISTRO DE ASISTENCIA"))
            return 'r_4'
        elif res == 'no envolved':
            _logger.warn("'%s' no esta registrado en este Evento. %s" % (username, "REGISTRO DE ASISTENCIA"))
            return 'r_3'
        elif res == 'already register':
            _logger.warn("'%s' Ya marco un registro de Entrada. %s" % (username, "REGISTRO DE ASISTENCIA"))
            return 'r_5'
        elif res == 'already checkout':
            _logger.warn("'%s' Ya marco un registro de Salida. %s" % (username, "REGISTRO DE ASISTENCIA"))
            return 'r_6'
        else:
            if res['register_type'] == 'checkin':
                _logger.info("'%s' Marco ENTRADA. %s" % (username, "REGISTRO DE ASISTENCIA"))
            else:
                _logger.info("'%s' marco SALIDA. %s" % (username, "REGISTRO DE ASISTENCIA"))
            return res
        return res
    
    def register_attendance_with_card(self, cr, uid, code, context={}):
        collaborator_obj = self.pool['kemas.collaborator']
        collaborator_ids = collaborator_obj.search(cr, uid, [('code', '=', code)], limit=1)
        if collaborator_ids:
            username = collaborator_obj.read(cr, uid, collaborator_ids[0], ['username'])['username']
            context['card_use'] = True
            return self._register_attendance(cr, uid, collaborator_ids[0], username, context)
        else:
            _logger.warning("'%s' Incorrect CODE. %s" % (code, "REGISTER ATTENDANCE"))
            return 'r_7'
    
    def register_attendance(self, cr, uid, username, password, context={}):
        from openerp.service import security
        collaborator_obj = self.pool.get('kemas.collaborator')
        user_id = security.login(cr.dbname, username, password)
        if user_id:
            collaborator_ids = super(collaborator_obj.__class__, collaborator_obj).search(cr, uid, [('user_id', '=', user_id), ('state', '=', 'Active')], limit=1)
            if collaborator_ids:
                return self._register_attendance(cr, uid, collaborator_ids[0], username, context)
            else:
                return 'r_2'
        else:
            _logger.warning("'%s' Incorrect Password. %s" % (username, "REGISTER ATTENDANCE"))
            return 'r_1'
    
    def create(self, cr, uid, vals, context={}):
        seq_obj = self.pool.get('ir.sequence')
        if vals.get('code'):
        	# Esto se agrego para permitir importar datos
            seq_id = seq_obj.search(cr, uid, [('name', '=', 'Kemas Attendance'), ])[0]
            vals['code'] = str(seq_obj.get_id(cr, uid, seq_id))
            return  super(kemas_attendance, self).create(cr, uid, vals, context)
            
        event_obj = self.pool.get('kemas.event')
        event_collaborator_line_obj = self.pool.get('kemas.event.collaborator.line')
        kemas_event_collaborator_line_obj = self.pool.get('kemas.event.collaborator.line')
        collaborator_obj = self.pool.get('kemas.collaborator')
        history_points_obj = self.pool.get('kemas.history.points')
        service_obj = self.pool.get('kemas.service')
        config_obj = self.pool.get('kemas.config')
        
        current_event = event_obj.get_current_event(cr, uid, extra_info=True)
        if not current_event: 
            return 'no event'
        
        vals['count'] = 1
        vals['user_id'] = uid
        vals['date'] = time.strftime("%Y-%m-%d %H:%M:%S")
        vals['event_id'] = current_event['current_event_id']
        vals['card_use'] = context.get('card_use', False)
        
        preferences = config_obj.read(cr, uid, config_obj.get_correct_config(cr, uid), ['allow_checkout_registers'])
        
        fields_to_read = ['service_id', 'date_start', 'attend_on_time_points', 'attend_on_time_points', 'late_points']
        event = event_obj.read(cr, uid, current_event['current_event_id'], fields_to_read)
        event['event_collaborator_line_ids'] = super(kemas_event_collaborator_line, kemas_event_collaborator_line_obj).search(cr, uid, [('event_id', '=', current_event['current_event_id'])])
        collaborators_involved_ids = event['event_collaborator_line_ids']
        collaborators_involved_list = []

        for collaborators_involved_id in collaborators_involved_ids:
            collaborator_id = event_collaborator_line_obj.read(cr, uid, collaborators_involved_id, ['collaborator_id'])['collaborator_id'][0]
            collaborators_involved_list.append(collaborator_id)
        
        #---Este colaborador ya registro asistencia
        checkin_id = False
        search_args = [('collaborator_id', '=', vals['collaborator_id']), ('event_id', '=', current_event['current_event_id']), ('register_type', '=', 'checkin')]
        attendance_ids = super(kemas_attendance, self).search(cr, uid, search_args)
        if attendance_ids:
            if preferences['allow_checkout_registers']:
                last_register = self.read(cr, uid, attendance_ids[0], ['checkout_id'])
                if last_register['checkout_id']:
                    return 'already checkout'
                else:
                    checkin_id = attendance_ids[0]
            else:
                return 'already register'
        
        # El Colaborador ho esta entre los colaboradores desginados para este evento   
        if not vals['collaborator_id'] in collaborators_involved_list:
            return 'no envolved'
        
        if checkin_id:
            vals['checkin_id'] = checkin_id
            vals['register_type'] = 'checkout'
        else:
            vals['register_type'] = 'checkin'
        
        #---------Verificar tipo de Asistencia------------------------------------------------------
        time_entry = current_event['time_entry']
        now = current_event['now']
        time_register = current_event['time_register']
        
        type_attendance = 'just_time'
        summary = 'Asistencia Puntual.'
        if (time_entry + time_register) < now:
            type_attendance = 'late'
            minutos_tarde = now - (time_entry + time_register)
            tiempo_de_atraso = extras.convert_minutes_to_hour_format(minutos_tarde)
            summary = "Asistencia Inpuntual, %s minutos tarde." % (tiempo_de_atraso)
        
        vals['type'] = type_attendance
        vals['summary'] = summary
        
        #----Escribir el historial de puntos-----------------------------------------------------
        collaborator = collaborator_obj.read(cr, uid, vals['collaborator_id'], ['points'])
        current_points = str(collaborator['points'])
        history_type = 'increase'
        operator = '+'
        
        nombre_del_evento = unicode(event['service_id'][1])
        time_start = service_obj.read(cr, uid, event['service_id'][0], ['time_start'])['time_start']
        time_start = extras.convert_float_to_hour_format(time_start)
        description = "Asistencia Puntual al Servicio: '%s' del %s, programado para las %s." % (nombre_del_evento, extras.convert_date_format_long_str(event['date_start']), time_start)
                    
        new_points = int(current_points) + int(event['attend_on_time_points'])
        change_points = abs(int(event['attend_on_time_points']))
        if type_attendance != 'just_time':
            history_type = 'decrease'
            operator = '-'
            description = unicode("""Asistencia Inpuntual,%s minutos tarde al Servicio:'%s' del %s.""", 'utf-8') % (tiempo_de_atraso, unicode(event['service_id'][1]), extras.convert_date_format_long_str(event['date_start']))
            new_points = int(current_points) - int(event['late_points'])
            change_points = abs(int(event['late_points'])) * -1
            
        #---Escribir puntaje
        current_level_id = collaborator_obj.get_corresponding_level(cr, uid, int(new_points))
        vals_puntos = {
                       'points':int(new_points),
                       'level_id':current_level_id,
                       }
        super(collaborator_obj.__class__, collaborator_obj).write(cr, uid, [vals['collaborator_id']], vals_puntos)
        
        # Generar codigo
        seq_id = seq_obj.search(cr, uid, [('name', '=', 'Kemas Attendance'), ])[0]
        vals['code'] = str(seq_obj.get_id(cr, uid, seq_id))
        res_id = super(kemas_attendance, self).create(cr, uid, vals, context)
        
        history_summary = str(operator) + str(change_points) + " Puntos. Antes " + str(current_points) + " ahora " + str(new_points) + " Puntos."
        vals_history_points = {
            'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
            'event_id': event['id'],
            'collaborator_id': vals['collaborator_id'],
            'attendance_id' : res_id,
            'type': history_type,
            'description': description,
            'summary': history_summary,
            'points': change_points,
            }
        history_points_obj.create(cr, uid, vals_history_points)      
        
        # Actualizar el registro de entrada
        if checkin_id:
            self.write(cr, uid, [checkin_id], {'checkout_id': res_id})  
        
        if context.get('with_register_type', False):
            res_id = {'res_id': res_id, 'register_type': vals['register_type']}
        return res_id
    
    _name = 'kemas.attendance'
    _order = 'date DESC'
    _rec_name = 'collaborator_id'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator'),
        'code': fields.char('Code', size=32, help="unique code that is assigned to each attendance record"),
        'register_type': fields.selection([
            ('checkin', 'Entrada'),
            ('checkout', 'Salida'),
            ], 'Tipo de registro', required=True),
        'type': fields.selection([
            ('just_time', 'On Time'),
            ('late', 'Late'),
            ('absence', 'Absence'),
            ], 'Type', select=True),
        'count': fields.integer('Count'),
        'event_id': fields.many2one('kemas.event', 'event', ondelete="restrict"),
        'date': fields.datetime('Date', help="Date the create"),
        'summary': fields.text('Summary'),
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        'service_id': fields.related('event_id', 'service_id', type="many2one", relation="kemas.service", string="Service", store=True),
        'user_id': fields.many2one('res.users', 'User', help='User who opened the system to record attendance.'),
        
        'checkin_id':fields.many2one('kemas.attendance', 'Registro de Entrada', help=''),
        'checkout_id':fields.many2one('kemas.attendance', 'Registro de Salida', help=''),
        'card_use':fields.boolean('Registro con tarjeta', required=False),
        }
    _sql_constraints = [
        ('uattendance_collaborator', 'unique (collaborator_id,event_id,register_type)', 'This collaborator has registered their attendance at this event!'),
        ('ucode', 'unique (code)', 'This code already exists!'),
        ]
    _defaults = {  
        'count': 1,
        'register_type': 'checkin'
        }
    
class kemas_event_replacement(osv.osv):
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('is_collaborator', False):
            args += ['|', ('collaborator_replacement_id.user_id', '=', uid), ('collaborator_id.user_id', '=', uid)]
            
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('datetime', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('datetime', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def unlink(self, cr, uid, ids, context={}): 
        event_obj = self.pool.get('kemas.event')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        attendace_obj = self.pool.get('kemas.attendance')        
        records = self.read(cr, uid, ids, ['event_collaborator_line_id', 'collaborator_id', 'collaborator_replacement_id', 'event_id'])
        for record in records:
            event = event_obj.read(cr, uid, record['event_id'][0], ['state'])
            if event['state'] not in ['on_going']:                
                raise osv.except_osv(u'Operación no válida', u'No se puede eliminar este reemplazo porque el evento no está en Curso')
            else:
                search_args = [('event_id', '=', record['event_id'][0]), ('collaborator_id', '=', record['collaborator_replacement_id'][0])]
                if attendace_obj.search(cr, uid, search_args):
                    raise osv.except_osv(u'Operación no válida', u'No se puede borrar un reemplazo de un colaborador que ya registro asistencia en este evento.')
                collaborator_id = record['collaborator_id'][0]
                replace_id = record['collaborator_replacement_id'][0]
                
                collaborator_obj = self.pool.get('kemas.collaborator')
                users_obj = self.pool.get('res.users')
                old_members = event_obj.read(cr, uid, event['id'], ['members'])['members']
                old_followers = event_obj.read(cr, uid, event['id'], ['message_follower_ids'])['message_follower_ids']  
                # Modificar los members
                replace_user_id = super(kemas_collaborator, collaborator_obj).read(cr, uid, replace_id, ['user_id'])['user_id'][0]
                collaborator_user_id = super(kemas_collaborator, collaborator_obj).read(cr, uid, collaborator_id, ['user_id'])['user_id'][0]
                if collaborator_user_id not in old_members:
                    super(kemas_event, event_obj).write(cr, uid, [event['id']], {'members' : [(4, collaborator_user_id)]}, context)
                super(kemas_event, event_obj).write(cr, uid, [event['id']], {'members' : [(3, replace_user_id)]}, context)
                # Modificar Seguidores
                replace_partner_id = users_obj.read(cr, uid, replace_user_id, ['partner_id'])['partner_id'][0]
                collaborator_partner_id = users_obj.read(cr, uid, collaborator_user_id, ['partner_id'])['partner_id'][0]
                if collaborator_partner_id not in old_followers:
                    super(kemas_event, event_obj).write(cr, uid, [event['id']], {'message_follower_ids' : [(4, collaborator_partner_id)]}, context)
                super(kemas_event, event_obj).write(cr, uid, [event['id']], {'message_follower_ids' : [(3, replace_partner_id)]}, context)
                
                line_obj.write(cr, uid, record['event_collaborator_line_id'][0], vals={'collaborator_id' : collaborator_id})
                event_obj.write_log_delete_replace(cr, uid, event['id'], collaborator_id, replace_id, record['id'])
                
        return super(osv.osv, self).unlink(cr, uid, ids, context)
    
    def name_get(self, cr, uid, ids, context={}):     
        records = self.read(cr, uid, ids, ['id', 'collaborator_id', 'collaborator_replacement_id'])
        res = []        
        for record in records:
            collaborator = unicode(record['collaborator_id'][1])
            if context.get('replacemente_long_name', False):
                replacement = record['collaborator_replacement_id'][1]
                name = "%s %s %s" % (collaborator, _('by'), replacement)
            else:
                name = collaborator
            res.append((record['id'], name))
        return res
    
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['datetime'] = vals.get('datetime', time.strftime("%Y-%m-%d %H:%M:%S"))
        vals['user_id'] = uid
        return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)

    _name = 'kemas.event.replacement'
    _rec_name = 'collaborator_replacement_id'
    _order = 'datetime DESC'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', help='Collaborator who was originally assigned to the event'),
        'collaborator_replacement_id': fields.many2one('kemas.collaborator', 'Collaborator replacement', help='Collaborator replacement'),
        'event_id': fields.many2one('kemas.event', 'Event', help='Event that was carried out the replacement', ondelete="cascade"),
        'event_collaborator_line_id': fields.many2one('kemas.event.collaborator.line', 'event_collaborator_line', ondelete="cascade", help=''),
        'user_id': fields.many2one('res.users', 'User', help='Persona que realizó el reemplado'),
        'datetime': fields.datetime('Date'),
        'description': fields.text('Description'),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }

# vim:expandtab:smartind:tabstop=4:softtabstop=4:shiftwidth=4:
