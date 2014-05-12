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
from lxml import etree
from tools.translate import _
from mx import DateTime
from datetime import *
from datetime import timedelta
from datetime import datetime
import time
import datetime 
import kemas_extras
import addons
import unicodedata
import random
import logging
import calendar
import pooler
import threading
from mx import DateTime
import base64
import openerp
import tools
import tools7
import math
from dateutil.parser import  *
from openerp import SUPERUSER_ID
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
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('datetime', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('datetime', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def create(self, cr, uid, vals, context={}):
        vals['datetime'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
    
class kemas_func(osv.osv):
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
            ret_val = createBarcodeDrawing(code, value=str(value), **options)
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
        group_obj = self.pool.get('res.groups')
        user_obj = self.pool.get('res.users')
        
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
        name = kemas_extras.quitar_acentos(name)
        username = ''
        try:
            username = kemas_extras.buid_username(name)
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

    def create_user(self, cr, uid, name, email, password, group, photo=False):
        username = self.build_username(cr, uid, name)
        user_obj = self.pool.get('res.users')
        groups_obj = self.pool.get('res.groups')
        vals = {
                'image' : photo,
                'name': name,
                'login': username,
                'company_id': 1,
                'menu_id': 1,
                # 'menu_tips':True,
                'user_email' : email,
                'password': unicode(password).lower(),
                'tz' : self.get_tz_by_uid(cr, uid)
                }
        user_id = user_obj.create(cr, uid, vals) 
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
    _columns = {
        'name': fields.char('Name', size=64),
        }

class kemas_massive_email_line(osv.osv):
    def on_change_email(self, cr, uid, ids, email):
        if email:
            if kemas_extras.validate_mail(email):
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
        def send_IMs():
            def send_IM(collaborator):
                try:
                    body = config_obj.build_incorporation_string(cr, uid, unicode(preferences['Message_information_massive_email']), collaborator['id'])
                    address = collaborator['im_account']
                    if address == False:
                        return None
                    attachments_to_send = attachments
                    if preferences['use_attachments_in_im'] == False:
                        attachments_to_send = []
                    subject_to_send = ""
                    message = server_obj.build_email(preferences['reply_email'], [address], subject_to_send, body, [], None, preferences['reply_email'], attachments_to_send, None, None, False, 'plain')
                    try:
                        if server_obj.send_email(cr, uid, message): 
                            _logger.info('Massive IM mail successfully sent to: %s', address)
                            return True
                        else:
                            _logger.warning('Massive IM Failed to send email to: %s', address)
                            return False
                    except:
                        _logger.warning('Massive IM Failed to send email to: %s', address)
                        return False
                except:
                    return False
                    
            if preferences['send_IM_massive_email'] == False:return None
            collaborator_obj = self.pool.get('kemas.collaborator')
            collaborators = collaborator_obj.read(cr, uid, collaborator_ids, ['id', 'im_account'])
            for collaborator in collaborators:
                send_IM(collaborator)
            
        db, pool = pooler.get_db_and_pool(db_name)
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
        
        send_IMs()
        
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
            raise osv.except_osv(_('Error!'), _('No recipients to send mail.'))
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
                    raise osv.except_osv(_('Error!'), _('No hay ninguna configuracion del Sistema definida.'))
                def_dic['state'] = 'draft'
                self._defaults = def_dic
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_this_month', False):
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
                
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_create', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
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
                
        # Procesar grabaciones
        obj = self.pool.get('kemas.recording')
        """
        records = super(osv.osv, obj).read(cr, uid, obj.search(cr, uid, []), [field_name, 'url'])
        for record in records:
            youtube_thumbnail = kemas_extras.get_thumbnail_youtube_video(record['url'])
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
        
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        string = string.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        string = string.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        string = string.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        return string
    
    def build_add_remove_points_string(self, cr, uid, message, collaborator_id, description, points):
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'name', 'nick_name', 'genre', 'points', 'level_name'])
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%cl', unicode(kemas_extras.get_standard_names(collaborator['name'])))
        message = message.replace('%pt', unicode(collaborator['points']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        message = message.replace('%em', unicode(collaborator['email']).lower())
        
        message = message.replace('%na', unicode(preferences['name_system']))
        message = message.replace('%se', unicode(preferences['system_email']).lower())
        message = message.replace('%hs', unicode(preferences['url_system']))
        message = message.replace('%na', unicode(preferences['name_submitting']))
        if collaborator['genre'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        
        try:
            description = description.replace('\n', '<br/>')
            try:message = message.replace('%ds', unicode(description, 'utf8'))
            except:message = message.replace('%ds', unicode(description))
        except:None
        
        message = message.replace('%mp', unicode(points))
        
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
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
        def send_IM():
            try:
                if type == 'add' or type == 'increase':
                    if preferences['use_message_im_add_points'] == False:return None
                    body = self.build_add_remove_points_string(cr, uid, preferences['Message_im_add_points'], collaborator_id, description, points)
                else:
                    if preferences['use_message_im_remove_points'] == False:return None
                    body = self.build_add_remove_points_string(cr, uid, preferences['Message_im_remove_points'], collaborator_id, description, points)
                address = collaborator['im_account']
                if address == False:
                    return None
                subject_to_send = subject
                if preferences['use_subject_in_im'] == False:
                    subject_to_send = ""
                message = server_obj.build_email(preferences['reply_email'], [], subject_to_send, body, [address], None, preferences['reply_email'], None, None, None, False, 'html')
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
            except: 
                _logger.warning('Manual change points Notify Failed to send email to: %s', address)
                return False
            
        server_obj = self.pool.get('ir.mail_server')
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'im_account'])
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
        if res_send_email:
            send_IM()
        return res_send_email
    
    def build_incorporation_string(self, cr, uid, message, collaborator_id):
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'name', 'nick_name', 'genre', 'code', 'points', 'level_name', 'username', 'password'])
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        message = message
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%cl', unicode(kemas_extras.get_standard_names(collaborator['name'])))
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
        if collaborator['genre'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
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
        def send_IM():
            try:
                if preferences['use_message_im_incorporation'] == False:return None
                body = self.build_incorporation_string(cr, uid, unicode(preferences['Message_im_information_incorporation']), collaborator_id)
                address = collaborator['im_account']
                if address == False:
                    return None
                attachments_to_send = attachments
                if preferences['use_attachments_in_im'] == False:
                    attachments_to_send = []
                subject_to_send = subject
                if preferences['use_subject_in_im'] == False:
                    subject_to_send = ""
                message = server_obj.build_email(preferences['reply_email'], [address], subject_to_send, body, [], None, preferences['reply_email'], attachments_to_send, None, None, False, 'plain')
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
            except: 
                _logger.warning('Incorporation Notify Failed to send email to: %s', address)
                return False
        server_obj = self.pool.get('ir.mail_server')
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'im_account'])
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
        if res_send_email:
            send_IM()
        return res_send_email
    
    def _build_event_completed_string(self, cr, uid, preferences, message, event_id, service_id, collaborator_id, type_attend):
        service_obj = self.pool.get('kemas.service')
        service = service_obj.read(cr, uid, service_id, [])
        event_obj = self.pool.get('kemas.event')
        event = event_obj.read(cr, uid, event_id, ['date_start', 'service_id', 'place_id', 'attend_on_time_points', 'late_points', 'not_attend_points'])
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'name', 'nick_name', 'genre', 'points', 'level_name'])
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
        
        message = message.replace('%cl', unicode(kemas_extras.get_standard_names(collaborator['name'])))
        message = message.replace('%nk', unicode(collaborator['nick_name']).title())
        message = message.replace('%pt', unicode(collaborator['points']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        message = message.replace('%em', unicode(collaborator['email']).lower())
        message = message.replace('%cl', unicode(kemas_extras.get_standard_names(collaborator['name'])))
        if collaborator['genre'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        
        message = message.replace('%ds', unicode(kemas_extras.convert_date_format_short_str(event['date_start'])))
        message = message.replace('%dy', unicode(kemas_extras.convert_date_format_long(event['date_start']), 'utf8'))
        message = message.replace('%sr', unicode(event['service_id'][1]).title())
        message = message.replace('%sp', unicode(event['place_id'][1]))
        message = message.replace('%st', unicode(kemas_extras.convert_float_to_hour_format(service['time_start'])))
        message = message.replace('%fn', unicode(kemas_extras.convert_float_to_hour_format(service['time_end'])))
        message = message.replace('%te', unicode(kemas_extras.convert_float_to_hour_format(service['time_entry'])))
        message = message.replace('%tl', unicode(kemas_extras.convert_float_to_hour_format(service['time_limit'])))
        message = message.replace('%tr', unicode(kemas_extras.convert_float_to_hour_format(service['time_register'])))
        
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
        collaborator = collaborator_obj.read(cr, uid, line['collaborator_id'][0], ['email', 'name', 'nick_name', 'genre', 'code', 'points', 'level_name', 'username', 'password'])
        #------------------------------------------------------------------------------------
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        message = message.replace('%cl', unicode(kemas_extras.get_standard_names(collaborator['name'])))
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
        if collaborator['genre'].lower() == 'male':
            message = message.replace('%gn', 'o')
        else:
            message = message.replace('%gn', 'a')
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        
        message = message.replace('%ds', unicode(kemas_extras.convert_date_format_short_str(event['date_start'])))
        
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        fecha_del_evento = kemas_extras.convert_to_tz(event['date_start'], tz)        
        try:
            try:message = message.replace('%dy', unicode(kemas_extras.convert_date_format_long(fecha_del_evento), 'utf8'))
            except:message = message.replace('%dy', unicode(kemas_extras.convert_date_format_long(fecha_del_evento)))
        except:None
        try:
            event_information = ''
            if event['information']:
                event_information = unicode(event['information'])
            message = message.replace('%in', event_information)
        except:None
        message = message.replace('%sr', unicode(event['service_id'][1]).title())
        message = message.replace('%sp', unicode(event['place_id'][1]))
        message = message.replace('%st', unicode(kemas_extras.convert_float_to_hour_format(service['time_start'])))
        message = message.replace('%es', unicode(kemas_extras.convert_float_to_hour_format(service['time_end'])))
        message = message.replace('%te', unicode(kemas_extras.convert_float_to_hour_format(service['time_entry'])))
        message = message.replace('%tl', unicode(kemas_extras.convert_float_to_hour_format(service['time_limit'])))
        message = message.replace('%tr', unicode(kemas_extras.convert_float_to_hour_format(service['time_register'])))
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
        
        message = kemas_extras.cambiar_meses_a_espaniol(message)
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
        def send_IM():
            try:
                if preferences['use_im_event_completion'] == False:return None
                body = self.build_event_completed_string(cr, uid, preferences, event_id, service_id, collaborator_id, type_attend, True)
                address = collaborator['im_account']
                if address == False:
                    return None
                subject_to_send = subject
                if preferences['use_subject_in_im'] == False:
                    subject_to_send = ""
                message = server_obj.build_email(preferences['reply_email'], [], subject_to_send, body, [address], None, preferences['reply_email'], None, None, None, False, 'plain')
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
            except: 
                _logger.warning('Event completed Notify Failed to send email to: %s', address)
                return False
            
        server_obj = self.pool.get('ir.mail_server')
        config_obj = self.pool.get('kemas.config')
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, collaborator_id, ['email', 'im_account'])
        #------------------------------------------------------------------------------------
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['mailing'] == False:
            return False
        #------------------------------------------------------------------------------------
        subject = self._build_event_completed_string(cr, uid, preferences, preferences['message_event_completon_subject'], event_id, service_id, collaborator_id, type_attend)
        res_send_email = send_email()
        if res_send_email:
            send_IM()
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
        def send_IM():
            try:
                if preferences['use_message_im_event'] == False:return None
                body = self.build_event_string(cr, uid, preferences['Message_im_information_event'], line_id)
                address = collaborator['im_account']
                if address == False:
                    return None
                subject_to_send = subject
                if preferences['use_subject_in_im'] == False:
                    subject_to_send = ""
                message = server_obj.build_email(preferences['reply_email'], [], subject_to_send, body, [address], None, preferences['reply_email'], None, None, None, False, 'html')
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
            except: 
                _logger.warning('New Event Notify Failed to send email to: %s', address)
                return False
            
        server_obj = self.pool.get('ir.mail_server')
        config_obj = self.pool.get('kemas.config')
        event_obj = self.pool.get('kemas.event')
        service_obj = self.pool.get('kemas.service')
        collaborator_obj = self.pool.get('kemas.collaborator')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        activity_obj = self.pool.get('kemas.activity')
        line = line_obj.read(cr, uid, line_id, ['collaborator_id', 'activity_ids', 'event_id'])
        event = event_obj.read(cr, uid, line['event_id'][0], ['date_start', 'service_id', 'place_id', 'attend_on_time_points', 'late_points', 'not_attend_points'])
        service = service_obj.read(cr, uid, event['service_id'][0], ['time_start', 'time_end', 'time_entry', 'time_limit', 'time_register'])
        collaborator = collaborator_obj.read(cr, uid, line['collaborator_id'][0], ['email', 'im_account'])
        #------------------------------------------------------------------------------------
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['mailing'] == False:
            return False
        #------------------------------------------------------------------------------------
        subject = self.build_event_string(cr, uid, preferences['Message_information_event_subject'], line_id)
        res_send_email = send_email()
        if res_send_email:
            send_IM()
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
        # --Suspensiones
        'day_to_suspension_task_closed': fields.integer(u'Dia de suspensión', required=False, help=u"Días que se van a suspender a un colaborador por no haber entregado una tarea a tiempo"),
        #---Images and logos------------------------
        'logo': fields.binary('Logo', help='The reports Logo.'),
        'system_logo': fields.binary('System Logo', help='The System Logo.'),
        'max_size_photos': fields.integer('Max size photos', help="Maximum size in kilobytes (KB) that can take photos of the system.", required=True),
        'max_size_logos': fields.integer('Max size logos', help="Maximum size in kilobytes (KB) that can take images of the system.", required=True),
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
            ('Standard39', 'Standard39'),
            ('QR', 'QR'),
            ('EAN13', 'EAN13'),
            ('FIM', 'FIM'),
            ('UPCA', 'UPCA'),
            ('EAN8', 'EAN8'),
            ('Extended93', 'Extended93'),
            ('USPS_4State', 'USPS_4State'),
            ('Codabar', 'Codabar'),
            ('MSI', 'POSTNET'),
            ('Code11', 'Code11'),
            ('Standard93', 'Standard93'),
            ('I2of5', 'I2of5'),
            ('Code128', 'Code128'),
             ], 'Typo de Codigo de Barras', required=True),
        'bc_text': fields.char('Texto de Codigo de barras', size=32, required=True),
        'bc_width': fields.integer('Ancho', required=True),
        'bc_height': fields.integer('Alto', required=True),
        'bc_hr_form': fields.boolean("Human Readable", help="Legible para lectura?"),
        }
    def _get_logo(self, cr, uid, context={}):
        photo_path = addons.get_module_resource('kemas', 'images', 'logo.png')
        return open(photo_path, 'rb').read().encode('base64')
    
    def _get_system_logo(self, cr, uid, context={}):
        photo_path = addons.get_module_resource('kemas', 'images', 'system_logo.png')
        return open(photo_path, 'rb').read().encode('base64')

    _defaults = {
        'name_system' : 'Kemas 4D',
        'default_points' : 100,
        'default_attend_on_time_points' : 10,
        'default_late_points' : 20,
        'default_not_attend_points' : 40,
        'url_system' : 'http://127.0.0.1:8069',
        'number_replacements':5,
        # --suspensiones
        'day_to_suspension_task_closed': 10,
        #---Images and logos----------------------------
        'logo': _get_logo,
        'system_logo': _get_system_logo,
        'max_size_photos':40,
        'max_size_logos':20,
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
        'bc_text':"%cd",
        'bc_type':"Code128",
        'bc_width':200,
        'bc_height':50,
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
        result = super(kemas_team, self).write(cr, uid, ids, vals, context)
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'team'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_team, self).write(cr, uid, [id], vals_write, context)
        return result
    
    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'team'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
        return super(kemas_team, self).create(cr, uid, vals, context)
    
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
    _name = 'kemas.team'
    _columns = {
        'logo': fields.binary('Logo', help='The Team Logo.'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='The name of the Team'),
        'responsible': fields.char('Responsible', size=64, required=False, help='Person in charge of this Team.'),
        'description': fields.text('Description', help='The description of the Team'),
        #Many to Many Relations----------------------------------------------------------------------------------------------
        'collaborator_ids': fields.one2many('kemas.collaborator', 'team_id', 'Collaborators', help='Collaborators to belong to this Team.', readonly=True),
        }
    _sql_constraints = [
        ('team_name', 'unique (name)', "This Team already exist!"),
        ]
    def _get_logo(self, cr, uid, context={}):
        photo_path = addons.get_module_resource('kemas', 'images', 'team.png')
        return open(photo_path, 'rb').read().encode('base64')

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
    
    def on_change_photo(self, cr, uid, ids, photo):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        values = {} 
        if kemas_extras.restrict_size(photo, preferences['max_size_photos']):
            return {'value':{}}
        else:
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('The size of the photo can not be greater than'))[0]
            msg = "%s %s KB..!!" % (msg, str(preferences['max_size_photos']))
            return {'value':{'photo': False}, 'warning':{'title':_('Error!'), 'message':msg}}
        
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
                age = kemas_extras.calcular_edad(birth)
                return age
            except: return ""
                
        result = {}
        for person_id in ids:
            result[person_id] = do(person_id)
        return result
    
    def on_change_birth(self, cr, uid, ids, birth, context={}):
        values = {}
        values['age'] = kemas_extras.calcular_edad(birth)
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
        'telef': fields.char('Telefone', size=10, help="The number of phone of the person. Example: 072878563"),
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
            image = tools7.image_colorize(open(openerp.modules.get_module_resource('kemas', 'images', 'avatar.png')).read())
        return tools7.image_resize_image_big(image.encode('base64'))

    
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
        result = super(kemas_area, self).write(cr, uid, ids, vals, context)
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'area'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_area, self).write(cr, uid, [id], vals_write, context)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'area'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
        return super(kemas_area, self).create(cr, uid, vals, context)
    
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
    _name = 'kemas.area'
    _columns = {
        'logo': fields.binary('Logo', help='The Area Logo.'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='The name of the area'),
        'responsible': fields.char('Responsible', size=64, required=True, help='Person in charge of this Area.'),
        'description': fields.text('Description', help='the description of the area'),
        'history': fields.text('History'),
        'activity_ids': fields.one2many('kemas.activity', 'area_id', 'Activities', help='Activities that belong to this area'),
        #Many to Many Relations----------------------------------------------------------------------------------------------
        'collaborator_ids': fields.many2many('kemas.collaborator', 'kemas_collaborator_area_rel', 'area_id', 'collaborator_id', 'Collaborators', help='Collaborators to belong to this Area.'),
        }
    _sql_constraints = [
        ('area_name', 'unique (name)', "This Area already exist!"),
        ]
    def _get_logo(self, cr, uid, context={}):
        photo_path = addons.get_module_resource('kemas', 'images', 'area.png')
        return open(photo_path, 'rb').read().encode('base64')

    _defaults = {
        'logo': _get_logo,
    }
    
class kemas_level(osv.osv):
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
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'level'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_level, self).write(cr, uid, [id], vals_write, context)
        return result


    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'level'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
            
        if vals.get('first_level', False):
             vals['points'] = 0
        res_id = super(kemas_level, self).create(cr, uid, vals, context)
        self.pool.get('kemas.collaborator').update_collaborators_level(cr, uid)        
        return res_id
     
    _order = 'points'
    _name = 'kemas.level'
    _columns = {
        'logo': fields.binary('Logo'),
        'logo_large': fields.binary('Large Logo'),
        'logo_medium': fields.binary('Medium Logo'),
        'logo_small': fields.binary('Small Logo'),
        'name': fields.char('Name', size=64, required=True, help='Name of this level.'),
        'previous_id': fields.many2one('kemas.level', 'Previous Level', help='Level that precedes this.'),
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
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'web_site'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_web_site, self).write(cr, uid, [id], vals_write, context)
            
            if vals.has_key('allow_get_avatar'):
                line_obj = self.pool.get('kemas.collaborator.web.site')
                line_ids = line_obj.search(cr, uid, [('web_site_id', '=', id)])
                
                vals = {'allow_get_avatar': vals['allow_get_avatar']}
                if not vals['allow_get_avatar']:
                    vals['get_avatar_from_website'] = False
                line_obj.write(cr, uid, line_ids, vals)
        return result

    def create(self, cr, uid, vals, context={}):
        if vals.get('logo', False):
            path = addons.__path__[0] + '/web/static/src/img/logo' + 'web_site'
            vals['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
            vals['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
            vals['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
        return super(kemas_web_site, self).create(cr, uid, vals, context)
    
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
        
    def on_change_allow_get_avatar(self, cr, uid, ids, allow_get_avatar, context={}):
        values = {}
        if not allow_get_avatar:
            values['get_avatar_method'] = False
        return {'value': values}

    _order = 'name'
    _name = 'kemas.web.site'
    _columns = {
        'logo': fields.binary('Logo'),
        'logo_large': fields.binary('Large Logo'),
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
        now = datetime.strptime(kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
        date_today = "%s-%s-%s" % (kemas_extras.completar_cadena(now.year, 4), kemas_extras.completar_cadena(now.month), kemas_extras.completar_cadena(now.day))
        
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
        return kemas_extras.get_end_date(date_today, int(days), tz, workdays=tuple(workdays))
    
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
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        suspension_ids = self.search(cr, uid, [('state', '=', 'on_going')])
        suspensions = self.read(cr, uid, suspension_ids, ['date_end', 'collaborator_id'])
        count = 0
        for suspension in suspensions:
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            now = datetime.strptime(kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
            end_suspension = datetime.strptime(suspension['date_end'], '%Y-%m-%d %H:%M:%S')
            date_start = now.date().__str__()
            date_end = end_suspension.date().__str__()         
            date_start = DateTime.strptime(date_start, '%Y-%m-%d')
            date_end = DateTime.strptime(date_end, '%Y-%m-%d')
            res = DateTime.Age (date_end, date_start)
            if res.days < 1:
                self.lift_by_collaborator(cr, uid, suspension['collaborator_id'][0])
                count += 1
        print """\n
                 -------------------------------------------------------------------------------------------------------------------------
                 ***************************************************[%d] Suspensions lifted**********************************************
                 -------------------------------------------------------------------------------------------------------------------------\n""" % (count)
        cr.commit()
    
    def _get_days_remaining(self, cr, uid, ids, name, arg, context={}): 
        def get_days_remaining(collaborator):
            if suspension['state'] == 'on_going':
                from datetime import datetime
                tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
                now = datetime.strptime(kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
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
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_create', '>=', range_dates['date_start']))
            args.append(('date_create', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_create', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date_create', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def create(self, cr, uid, vals, *args, **kwargs):
         vals['state'] = 'on_going'
         vals['date_create'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
        'task_assigned_id':fields.many2one('kemas.task.assigned', 'Tarea', help=u'Tarea no cumplida por la cual se realizó la suspensión'),
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
            profile = kemas_extras.get_facebook_info(wsline['url'], 'large')
            if profile:
                vals = {'photo': profile['photo']}
                if profile.get('gender', False):
                    if profile['gender'] == 'male':
                        vals['genre'] = 'Male'
                    else:
                        vals['genre'] = 'Female'
            
        if web_site['get_avatar_method'] == 'gravatar':
            photo = kemas_extras.get_avatar(wsline['url'], 120)
            if photo:
                vals = {'photo': photo}
        
        if vals:
            self.pool.get('kemas.collaborator').write(cr, uid, [wsline['collaborator_id'][0]], vals)
            return True
        else:
            return False
        
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
    
class kemas_ministry(osv.osv):
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'active': False})
        return True
    
    def write(self, cr, uid, ids, vals, context={}):
        result = super(kemas_ministry, self).write(cr, uid, ids, vals, context)
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'ministry'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_ministry, self).write(cr, uid, [id], vals_write, context)
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
        for id in ids:
            if vals.get('logo', False):
                path = addons.__path__[0] + '/web/static/src/img/logo' + 'specialization_course'
                vals_write = {}
                vals_write['logo_large'] = kemas_extras.crop_image(vals['logo'], path, 128)
                vals_write['logo_medium'] = kemas_extras.crop_image(vals['logo'], path, 64)
                vals_write['logo_small'] = kemas_extras.crop_image(vals['logo'], path, 48)
                super(kemas_specialization_course, self).write(cr, uid, [id], vals_write, context)
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
    
class kemas_collaborator_logbook(osv.osv):
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['date'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
    
class kemas_collaborator(osv.osv):
    def change_to_collaborator(self, cr, uid, ids, context={}):
        collaborator = super(kemas_collaborator, self).read(cr, uid, ids[0], ['nick_name', 'name', 'email', 'code', 'photo_large'])
        vals = {
                'type' : 'Collaborator',
                'notified' : 'notified',
                'join_date' : time.strftime("%Y-%m-%d")
                }
        # Crear cuenta de usuario
        groups_obj = self.pool.get('res.groups')
        groups_ids = groups_obj.search(cr, uid, [('name', '=', 'Kemas / Collaborator'), ])
        nick_name = unicode(collaborator['nick_name']).title()
        apellido = unicode(kemas_extras.do_dic(collaborator['name'])[0]).title()
        name = u'''%s %s''' % (nick_name, apellido)
        vals['user_id'] = self.pool.get('kemas.func').create_user(cr, uid, name, collaborator['email'], collaborator['code'], groups_ids[0], collaborator['photo_large'])['user_id']
        super(kemas_collaborator, self).write(cr, uid, ids, vals)
        #----Escribir el historial de puntos-----------------------------------------------------
        description = 'Se incorpora el grupo de colaboradores.'
        change_points = str(self.get_initial_points(cr, uid))
        current_points = str(0)
        new_points = str(change_points)
        #---Escribir puntaje-----
        vals['points'] = new_points
        #------------------------
        summary = "+" + change_points + " Puntos. Antes " + current_points + " ahora " + new_points + " Puntos." 
        self.pool.get('kemas.history.points').create(cr, uid, {
            'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
            'collaborator_id': collaborator['id'],
            'type': 'init',
            'description': description,
            'summary': summary,
            'points': change_points,
            })
        #----Asignar Nivel-----------------------------------------------------------------------
        vals['level_id'] = self.get_first_level(cr, uid)
        vals['state'] = 'Active'
        self.send_join_notification(cr, uid)
        
        super(kemas_collaborator, self).write(cr, uid, ids, vals)
        return True
    
    def do_activate(self, cr, uid, ids, context={}):
        collaborators = super(kemas_collaborator, self).read(cr, uid, ids, ['user_id', 'state', 'type'])
        vals = {
                'state':'Active',
                'end_service': False
                }
        for collaborator in collaborators:
            if collaborator['state'] in ['Active'] or collaborator['type'] in ['Others']:
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
        collaborators = super(kemas_collaborator, self).read(cr, uid, ids, ['user_id', 'state', 'type'])
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        vals = {
                'state':'Inactive',
                'end_service' : kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
                }
        for collaborator in collaborators:
            if collaborator['state'] in ['Inactive'] or collaborator['type'] in ['Others']:
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
        fields = ['id', 'nick_name', 'name']
        if context.get('show_replacements', False):
            replacements_word = self.pool.get('kemas.func').get_translate(cr, uid, _('replacements available'))[0]
            fields.append('replacements')
        reads = super(osv.osv, self).read(cr, uid, ids, fields)
        res = []
        for record in reads:
            nick_name = unicode(record['nick_name']).title()
            apellido = unicode(kemas_extras.do_dic(record['name'])[0]).title()
            if context.get('show_replacements', False):
                name = u'''%s %s (%d %s)''' % (nick_name, apellido, record['replacements'], replacements_word)
            else:
                name = u'''%s %s''' % (nick_name, apellido)
            res.append((record['id'], name))
        return res
    
    def on_change_name(self, cr, uid, ids, name, context={}):
        values = {}
        dic_name = kemas_extras.do_dic(name)
        if len(dic_name) < 4:
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('At least two valid names must be entered.'))[0]
            return {'value':{'name':unicode(name).lower()}, 'warning':{'title':'Error', 'message':msg}}
        else:
            return {'value':{
                             'name':unicode(name).title(),
                             'nick_name':unicode(dic_name[2]).title()
                             }
                    }
    
    def on_change_nick_name(self, cr, uid, ids, name, nick_name, context={}):
        values = {}
        name = unicode(name).lower().strip()
        nick_name = unicode(nick_name).lower().strip()
        if nick_name in name:
            return {'value':{'nick_name':unicode(nick_name).upper()}}
        else:
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('The name entered must be in the long name.'))[0]
            return {'value':{'nick_name':nick_name}, 'warning':{'title':'Error', 'message':msg}}
        
    def on_change_photo(self, cr, uid, ids, photo):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        values = {} 
        if kemas_extras.restrict_size(photo, preferences['max_size_photos']):
            return {'value':{}}
        else:
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('The size of the photo can not be greater than'))[0]
            msg = "%s %s KB..!!" % (msg, str(preferences['max_size_photos']))
            return {'value':{'photo': False}, 'warning':{'title':_('Error!'), 'message':msg}}
                
    def on_change_email(self, cr, uid, ids, email):
        if email:
            if kemas_extras.validate_mail(email):
                return {'value':{}}
            else:
                msg = self.pool.get('kemas.func').get_translate(cr, uid, _('E-mail format invalid..!!'))[0]
                return {'value':{'email':''}, 'warning':{'title':'Error', 'message':msg}}
        else:
            return True
    
    def on_change_im_account(self, cr, uid, ids, chat_account):
        if chat_account:
            if kemas_extras.validate_mail(chat_account):
                return {'value':{}}
            else:
                msg = self.pool.get('kemas.func').get_translate(cr, uid, _('IM account format invalid..!!'))[0]
                return {'value':{'im_account':''}, 'warning':{'title':'Error', 'message':msg}}
        else:
            return True
        
    def fields_get(self, cr, uid, fields=None, context={}, write_access=True): 
        result = super(osv.osv, self).fields_get(cr, uid, fields, context, write_access)
        def_dic = {}
        def_dic['notified'] = 'notified'
        def_dic['genre'] = 'Male'
        def_dic['marital_status'] = 'Single'
        # def_dic['points'] = self.get_initial_points(cr, uid)
        def_dic['points'] = 0
        def_dic['type'] = 'Collaborator'
        def_dic['state'] = 'creating'
        def_dic['photo'] = self.get_photo_male()
        def_dic['level_id'] = self.get_first_level(cr, uid)
        
        self._defaults = def_dic
        return result

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        res = super(osv.osv, self).read(cr, uid, ids, fields, context)
        if fields is None or not list(set(['photo', 'photo_large', 'photo_medium', 'photo_small', 'photo_very_small']) & set(fields)):
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
        elif 'photo_large' in fields:
            photo_field = 'photo_large'
        elif 'photo_medium' in fields:
            photo_field = 'photo_small'
        elif 'photo_small' in fields:
            photo_field = 'photo_small'
            
        if photo_field:
            if type(res).__name__ == 'list':
                for read_dict in res:
                    collaborator = super(osv.osv, self).read(cr, uid, read_dict['id'], ['genre'])
                    if read_dict.has_key(photo_field):
                        if read_dict[photo_field] == False:
                            if collaborator['genre'] == 'Male':
                                read_dict[photo_field] = self.get_photo_male()
                            else:
                                read_dict[photo_field] = self.get_photo_female()
                        else:
                            continue
                    else:
                        if collaborator['genre'] == 'Male':
                            read_dict[photo_field] = self.get_photo_male()
                        else:
                            read_dict[photo_field] = self.get_photo_female()
            else:
                collaborator = super(osv.osv, self).read(cr, uid, ids, ['genre'])
                if res.has_key(photo_field):
                    if res[photo_field] == False:
                        if collaborator['genre'] == 'Male':
                            res[photo_field] = self.get_photo_male()
                        else:
                            res[photo_field] = self.get_photo_female()               
                else:
                    if collaborator['genre'] == 'Male':
                        res[photo_field] = self.get_photo_male()
                    else:
                        res[photo_field] = self.get_photo_female()
        
        #--------FOTO Para la VISTA DE KANBAN----------------------------
        elif 'photo_medium' in fields:
            if type(res).__name__ == 'list':
                for read_dict in res:
                    collaborator = super(osv.osv, self).read(cr, uid, read_dict['id'], ['genre'])
                    if read_dict.has_key('photo_medium'):
                        if read_dict['photo_medium'] == False:
                            if collaborator['genre'] == 'Male':
                                read_dict['photo_medium'] = self.get_photo_small_male()
                            else:
                                read_dict['photo_medium'] = self.get_photo_small_female()
                        else:
                            continue
                    else:
                        if collaborator['genre'] == 'Male':
                            read_dict['photo_medium'] = self.get_photo_small_male()
                        else:
                            read_dict['photo_medium'] = self.get_photo_small_female()
            else:
                collaborator = super(osv.osv, self).read(cr, uid, ids, ['genre'])
                if res.has_key('photo_medium'):
                    if res['photo_medium'] == False:
                        if collaborator['genre'] == 'Male':
                            res['photo_medium'] = self.get_photo_small_male()
                        else:
                            res['photo_medium'] = self.get_photo_small_female()               
                else:
                    if collaborator['genre'] == 'Male':
                        res['photo_medium'] = self.get_photo_small_male()
                    else:
                        res['photo_medium'] = self.get_photo_small_female()
        return res 

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        user_obj = self.pool.get('res.users')
        group_obj = self.pool.get('res.groups')
        user_id = user_obj.search(cr, uid, [('id', '=', uid), ])
        groups_id = user_obj.read(cr, uid, user_id, ['groups_id'])[0]['groups_id']
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
            args.append(('type', '=', 'Collaborator'))
            args.append(('state', 'in', ['Active', 'Suspended']))
            
        if context.has_key('birthday'):
            if context['birthday']:
                args = []
                desde = time.strftime("%Y-%m-") + '01'
                hasta = time.strftime("%Y-%m-") + unicode(kemas_extras.dias_de_este_mes())
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
            nick_name_words = kemas_extras.do_dic(nick_name)
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
        db, pool = pooler.get_db_and_pool(db_name)
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
            
        for collaborator_id in ids:
            process(collaborator_id, description, date_end)
        cr.commit()
            
    def add_remove_points(self, cr, uid, ids, points, description, type='increase'):
        threaded_sending = threading.Thread(target=self._add_remove_points, args=(cr.dbname, uid, ids, points, description, type))
        threaded_sending.start()
        
    def _add_remove_points(self, db_name, uid, ids, points, description, type='increase'):
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        config_obj = self.pool.get('kemas.config')
        def change(collaborator_id, points, description, type):
            current_points = super(osv.osv, self).read(cr, uid, collaborator_id, ['points'])['points']
            suspend_collaborator = int(points)
            
            operator = '-'
            if type == 'add': 
                type == 'increase'
            if type == 'remove': 
                type == 'decrease'
            
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
        for collaborator_id in ids:
            change(collaborator_id, points, description, type)
        cr.commit()        
            
    def send_join_notification(self, cr, uid):
        threaded_sending = threading.Thread(target=self._send_join_notification, args=(cr.dbname , uid))
        threaded_sending.start()
    
    def _send_join_notification(self, db_name, uid):
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        #--------------------------------------------------------------------------------------------
        collaborator_ids = super(osv.osv, self).search(cr, uid, [('notified', 'in', ['no_notified'])])
        count = 0
        for collaborator_id in collaborator_ids:
            count += 1
            self.send_notification(cr, uid, collaborator_id, context={})
        print """\n
                 -------------------------------------------------------------------------------------------------------------------------
                 ***********************************************[%d] Join Notifications was sended****************************************
                 -------------------------------------------------------------------------------------------------------------------------\n""" % (count)
        cr.commit()
        
    def update_collaborators_level(self, cr, uid):
        threaded_sending = threading.Thread(target=self._update_collaborators_level, args=(cr.dbname , uid))
        threaded_sending.start()
        
    def _update_collaborators_level(self, db_name, uid):
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        #--------------------------------------------------------------------------------------------
        collaborator_ids = super(osv.osv, self).search(cr, uid, [('type', 'in', ['Collaborator'])])
        collaborators = super(osv.osv, self).read(cr, uid, collaborator_ids, ['id', 'points'])
        for collaborator in collaborators:
            level_id = self.get_corresponding_level(cr, uid, int(collaborator['points']))
            if level_id:
                vals = {'level_id': level_id}
                super(osv.osv, self).write(cr, uid, [collaborator['id']], vals)
        print """\n
                 -------------------------------------------------------------------------------------------------------------------------
                 ************************************************Collaborator's level was updated*****************************************
                 -------------------------------------------------------------------------------------------------------------------------\n"""                                 
        cr.commit()
          
    def get_corresponding_level(self, cr, uid, points):
        level_obj = self.pool.get('kemas.level')
        level_ids = level_obj.get_order_levels(cr, uid)
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
            if record['type'] == 'Collaborator' and record['state'] in ['Active']:
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
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
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
            
    def create(self, cr, uid, vals, *args, **kwargs):
        vals['email'] = unicode(vals['email']).lower()
            
        if vals.has_key('points'):
            return super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
        
        vals['name'] = unicode(vals['name']).title()
        #----Crear un codigo para la persona que se registre---------------------------------------------
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Collaborator'), ])[0]
        vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        
        photo_path_male = addons.get_module_resource('kemas', 'images', 'male.png')
        photo_male = open(photo_path_male, 'rb').read().encode('base64')
        
        photo_path_female = addons.get_module_resource('kemas', 'images', 'female.png')
        photo_female = open(photo_path_female, 'rb').read().encode('base64')
        if vals['genre'] == 'Male':
            if vals['photo'] == photo_male or vals['photo'] == photo_female:
                vals['photo'] = False
        else:
            if vals['photo'] == photo_male or vals['photo'] == photo_female:
                vals['photo'] = False
                
            
        if vals['type'] == 'Collaborator':
            vals['points'] = self.get_initial_points(cr, uid)
            vals['level_id'] = self.get_corresponding_level(cr, uid, self.get_initial_points(cr, uid))
            #'----Si la persona que se registra es un Colaborador entonces se le agrega un usuario.-----------
            groups_obj = self.pool.get('res.groups')
            groups_ids = groups_obj.search(cr, uid, [('name', '=', 'Kemas / Collaborator'), ])
            
            nick_name = unicode(vals['nick_name']).title()
            apellido = unicode(kemas_extras.do_dic(vals['name'])[0]).title()
            name = u'''%s %s''' % (nick_name, apellido)
            if vals.get('photo', False):
                # Crear una imagen pequeña de la foto del colaborador
                path = addons.__path__[0] + '/web/static/src/img/avatar' + "collaborator"
                vals['photo_large'] = kemas_extras.crop_image(vals['photo'], path, 128)
                vals['photo_medium'] = kemas_extras.crop_image(vals['photo'], path, 64)
                vals['photo_small'] = kemas_extras.crop_image(vals['photo'], path, 48)
                vals['photo_very_small'] = kemas_extras.crop_image(vals['photo'], path, 32)
                photo = vals['photo_large']
            else:
                if vals['genre'] == 'Male':
                    photo = photo_male
                else:
                    photo = photo_female
            
            vals['user_id'] = self.pool.get('kemas.func').create_user(cr, uid, name, vals['email'], vals['code'], groups_ids[0], photo)['user_id']
            # Actualizar los datos del Partner
            partner_obj = self.pool.get('res.partner')
            partner_id = self.pool.get('res.users').read(cr, uid, vals['user_id'], ['partner_id'])['partner_id'][0]
            vals_partner = {
                            'country_id' : vals['born_country'],
                            'state_id' : vals['born_state'],
                            'city' : vals['born_city'],
                            'email' : vals['email'],
                            'image' : photo
                            }
            partner_obj.write(cr, uid, [partner_id], vals_partner)
        else:
            vals['points'] = 0
        vals['state'] = 'Active'
        

        res_id = super(osv.osv, self).create(cr, uid, vals, *args, **kwargs)
        #----Escribir el historial de puntos-----------------------------------------------------------------
        if vals['type'] == 'Collaborator':
            history_points_obj = self.pool.get('kemas.history.points')
            description = 'Se inicializa el registro.'
            points = self.get_initial_points(cr, uid)
            summary = '+' + str(points) + ' Puntos.'
            history_points_obj.create(cr, uid, {
                        'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                        'collaborator_id': res_id,
                        'type': 'init',
                        'description': description,
                        'summary': summary,
                        'points': points,
                        })
            cr.commit()
            self.send_notification(cr, uid, res_id)
        
        # Escribir una linea en la bitacora del Colaborador
        vals = {
                'collaborator_id' : res_id,
                'description' : 'Creacion del Colaborador.',
                'type' : 'important',
                }
        
        self.pool.get('kemas.collaborator.logbook').create(cr, uid, vals)
        return res_id
    
    def write(self, cr, uid, ids, vals, context={}):
        collaborator = super(osv.osv, self).read(cr, uid, ids[0], ['user_id', 'points', 'id', 'name', 'code', 'email'])
        if context.get('is_collaborator', False):
            if uid != collaborator['user_id'][0]:
                raise osv.except_osv(_('Error!'), _('You can not change information that is not yours!'))
            
        zero_points = False
        send_email = False

        #--Si la  persona ya no es colaborador se le quita el usuario------------------------------------
        if vals.has_key('type'):
            history_points_obj = self.pool.get('kemas.history.points')
            users_obj = self.pool.get('res.users')
            
            if vals['type'] == 'Others':
                vals['state'] = 'creating'
                vals['notified'] = 'no_notified'
                try:
                    user_id = collaborator['user_id'][0]
                    users_obj.unlink(cr, uid, [user_id])
                except: None
                #----Escribir el historial de puntos-----------------------------------------------------
                change_points = str(collaborator['points'])
                current_points = str(collaborator['points'])
                new_points = str(0)
                zero_points = True
                #---Escribir puntaje-----
                vals['points'] = new_points
                #------------------------
                description = 'Ya no pertenece al grupo de Colaboradores, por lo tanto se restan todos los puntos.'
                summary = "-" + change_points + " Puntos. Antes " + current_points + " ahora " + new_points + " Puntos."
                history_points_obj.create(cr, uid, {
                    'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    'collaborator_id': collaborator['id'],
                    'type': 'decrease',
                    'description': description,
                    'summary': summary,
                    'points': change_points * -1,
                    })
            else:
                vals['notified'] = 'notified'
                #----Escribir el historial de puntos-----------------------------------------------------
                description = 'Se incorpora el grupo de colaboradores.'
                change_points = str(self.get_initial_points(cr, uid))
                current_points = str(0)
                new_points = str(change_points)
                #---Escribir puntaje-----
                vals['points'] = new_points
                #------------------------
                summary = "+" + change_points + " Puntos. Antes " + current_points + " ahora " + new_points + " Puntos." 
                history_points_obj.create(cr, uid, {
                    'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                    'collaborator_id': collaborator['id'],
                    'type': 'init',
                    'description': description,
                    'summary': summary,
                    'points': change_points,
                    })
                #----Asignar Nivel-----------------------------------------------------------------------
                vals['level_id'] = self.get_first_level(cr, uid)
                vals['state'] = 'Active'
                
                groups_obj = self.pool.get('res.groups')
                groups_ids = groups_obj.search(cr, uid, [('name', '=', 'Kemas / Collaborator'), ])
                
                if vals.has_key('name'):
                    nick_name = unicode(vals['nick_name']).title()
                    apellido = unicode(kemas_extras.do_dic(vals['name'])[0]).title()
                    name = u'''%s %s''' % (nick_name, apellido)
                else:
                    if vals.has_key('nick_name') == False:
                        nick_name = unicode(super(osv.osv, self).read(cr, uid, ids[0], ['nick_name'])['nick_name']).title()
                        apellido = unicode(kemas_extras.do_dic(collaborator['name'])[0]).title()
                    else:
                        nick_name = unicode(vals['nick_name']).title()
                        apellido = unicode(kemas_extras.do_dic(collaborator['name'])[0]).title()
                    name = u'''%s %s''' % (nick_name, apellido)
                    
                vals['user_id'] = self.pool.get('kemas.func').create_user(cr, uid, name, collaborator['email'], collaborator['code'], groups_ids[0])['user_id']
                send_email = True
            
        #----Cambiar el Puntaje y establecer Nivel-------------------------------------------------------
        if vals.has_key('points'):
            vals['level_id'] = self.get_corresponding_level(cr, uid, vals['points'])
            
        # Crear una imagen pequeña de la foto del colaborador
        if vals.get('photo', False):
            photo_path = addons.__path__[0] + '/web/static/src/img/avatar'
            vals['photo_large'] = kemas_extras.crop_image(vals['photo'], photo_path, 128)
            vals['photo_medium'] = kemas_extras.crop_image(vals['photo'], photo_path, 64)
            vals['photo_small'] = kemas_extras.crop_image(vals['photo'], photo_path, 48)
            vals['photo_very_small'] = kemas_extras.crop_image(vals['photo'], photo_path, 32)
            
        res = super(osv.osv, self).write(cr, uid, ids, vals, context)
        if not context is None and context and type(context).__name__ == "dict" and not context.get('no_update_logbook', False):
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
        #----Cambiar el nombre al usuario----------------------------------------------------------------
        collaborator = self.read(cr, uid, ids[0], ['born_country', 'email', 'born_state', 'born_city', 'photo', 'user_id'])
        if not collaborator['user_id']:
            raise osv.except_osv(_('Error!'), _('Este usuario no tiene una cuenta de Usuario asignada!!'))
        
        # Actualizar los datos del USER
        collaborator_name = self.name_get(cr, uid, ids)[0][1]
        user_obj = self.pool.get('res.users')
        vals_user = {
                    'name': collaborator_name,
                    'email' : collaborator['email']
                    }
        if vals.has_key('photo'):
            vals_user['image'] = vals['photo_large']
        user_obj.write(cr, uid, [collaborator['user_id'][0]], vals_user)
        
        # Actualizar los datos del Partner
        partner_obj = self.pool.get('res.partner')
        partner_id = self.pool.get('res.users').read(cr, uid, collaborator['user_id'][0], ['partner_id'])['partner_id'][0]
        vals_partner = {
                        'country_id' : collaborator['born_country'][0],
                        'state_id' : collaborator['born_state'][0],
                        'city' : collaborator['born_city'],
                        }
        vals_partner.update(vals_user)
        partner_obj.write(cr, uid, [partner_id], vals_partner)
                    
        # Enviar correo de Notificacion de Creacion de Cuenta
        if res and send_email:
            cr.commit()
            self.send_notification(cr, uid, ids[0])
        return res


    def _person_age(self, cr, uid, ids, name, arg, context={}):
        result = {}
        collaborators = super(osv.osv, self).read(cr, uid, ids, ['id', 'birth'], context=context)
        for collaborator in collaborators:
            result[collaborator['id']] = kemas_extras.calcular_edad(collaborator['birth'], 3)
        return result
    
    def _dummy_age(self, cr, uid, ids, name, value, arg, context={}):
        return True
       
    def on_change_join_date(self, cr, uid, ids, join_date, context={}):
        values = {}
        values['age_in_ministry'] = kemas_extras.calcular_edad(join_date, 4)
        return {'value':values}
    
    def on_change_birth(self, cr, uid, ids, birth, context={}):
        values = {}
        values['age'] = kemas_extras.calcular_edad(birth, 3)
        return {'value':values}
    
    def get_initial_points(self, cr, uid, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        return int(config_obj.read(cr, uid, config_id, ['default_points'])['default_points'])
    
    def validate_four_names(self, cr, uid, ids):
        collaborator = super(osv.osv, self).read(cr, uid, ids[0], ['name', 'nick_name'])
        nombres = kemas_extras.do_dic(collaborator['name'])
        if len(nombres) < 4:
            raise osv.except_osv(_('Error!'), _('At least four valid names must be entered.'))
        else:
            name = unicode(collaborator['name']).lower().strip()
            nick_name = unicode(collaborator['nick_name']).lower().strip()
            if not nick_name in name:
                raise osv.except_osv(_('Error!'), _('The name entered must be in the long name.'))
            else:
                return True
    
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
            res = kemas_extras.convert_to_tz(res, tz)
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
            collaborator = super(osv.osv, self).read(cr, uid, collaborator_id, ['nick_name', 'name'])
            nick_name = unicode(collaborator['nick_name']).title()
            apellido = unicode(kemas_extras.do_dic(collaborator['name'])[0]).title()
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
                res = kemas_extras.calcular_edad(collaborator['join_date'], 4, collaborator['end_service'])
            else:
                res = kemas_extras.calcular_edad(collaborator['join_date'], 4)
            result[collaborator['id']] = res
        return result
    
    def build_QR_text(self, cr, uid, message, collaborator_id):
        fields = ['code', 'name', 'birth', 'genre', 'marital_status', 'telef1', 'telef2', 'mobile', 'email', 'address', 'join_date', 'type', 'username', 'level_name']
        collaborator = super(osv.osv, self).read(cr, uid, collaborator_id, fields)
        #------------------------------------------------------------------------------------
        message = message
        message = message.replace('%cd', unicode(collaborator['code']))
        message = message.replace('%cl', unicode(collaborator['name']))
        message = message.replace('%bt', kemas_extras.convert_date_to_dmy(unicode(collaborator['birth'])))
        #----Genero-----------------------------------------------------------------
        if collaborator['genre'].lower() == 'male':
            message = message.replace('%gn', 'Hombre')
        else:
            message = message.replace('%gn', 'Mujer')
        #----Estado Civil-----------------------------------------------------------
        if collaborator['marital_status'].lower() == 'single':
            if collaborator['genre'].lower() == 'male':
                message = message.replace('%ms', 'Soltero')
            else:
                message = message.replace('%ms', 'Soltera')
        elif collaborator['marital_status'].lower() == 'married':
            if collaborator['genre'].lower() == 'male':
                message = message.replace('%ms', 'Casado')
            else:
                message = message.replace('%ms', 'Casada')
        elif collaborator['marital_status'].lower() == 'divorced':
            if collaborator['genre'].lower() == 'male':
                message = message.replace('%ms', 'Divorsiado')
            else:
                message = message.replace('%ms', 'Divorsiada')
        elif collaborator['marital_status'].lower() == 'widower':
            if collaborator['genre'].lower() == 'male':
                message = message.replace('%ms', 'Viudo')
            else:
                message = message.replace('%ms', 'Viuda')
        #-------------------------------------------------------------------------
        message = message.replace('%t1', unicode(collaborator['telef1']))
        message = message.replace('%t2', unicode(collaborator['telef2']))
        message = message.replace('%mb', unicode(collaborator['mobile']))
        message = message.replace('%em', unicode(collaborator['email']))
        message = message.replace('%ad', unicode(collaborator['address']))
        message = message.replace('%jd', unicode(kemas_extras.convert_date_to_dmy(collaborator['join_date'])))
        #----Type-----------------------------------------------------------------
        if collaborator['type'].lower() == 'collaborator':
            message = message.replace('%tp', 'Colaborador')
        else:
            message = message.replace('%tp', 'Invitado')
        #-------------------------------------------------------------------------
        message = message.replace('%us', unicode(collaborator['username']))
        message = message.replace('%lv', unicode(collaborator['level_name']))
        #---Fecha y hora---------------------------------------------------------- 
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
        now = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        message = message.replace('%da', unicode(now.strftime("%Y-%m-%d")))
        message = message.replace('%tm', unicode(now.strftime("%H:%M:%S")))
        message = message.replace('%dt', unicode(now.strftime("%Y-%m-%d %H:%M:%S")))
        return unicode(message)
    
    def _get_barcode_image(self, cr, uid, ids, name, arg, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, ['bc_text', 'bc_width', 'bc_height', 'bc_type', 'bc_hr_form'])
        width = preferences['bc_width']        
        height = preferences['bc_height']
        image_type = preferences['bc_type']
        hr_form = preferences['bc_hr_form']
        
        def get_barcode_image(collaborator):
            bc_text = preferences['bc_text'].replace('%id', unicode(collaborator['id']))
            bc_text = preferences['bc_text'].replace('%cd', unicode(collaborator['code']))
            return kemas_extras.get_image_code(bc_text, width, height, hr_form, image_type)

        result = {}
        collaborators = super(osv.osv, self).read(cr, uid, ids, ['id', 'code'])
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
            return kemas_extras.get_image_code(value, width, height, False, "QR")

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
    
    def _create_date(self, cr, uid, ids, name, arg, context={}): 
        from datetime import datetime
        result = {}
        sql = """
                SELECT cl.id,cl.create_date
                FROM kemas_collaborator AS cl
                INNER JOIN res_users AS us ON (cl.create_uid = us.id)
                WHERE cl.id in (%s)
            """ % (kemas_extras.convert_to_tuple_str(ids))
        cr.execute(sql)
        collaborators = cr.fetchall()
        for collaborator in collaborators:
            dt = datetime.strptime(collaborator[1], '%Y-%m-%d %H:%M:%S.%f')
            create_date = "%s %d:%d:%d" % (dt.date().__str__(), dt.hour, dt.minute, dt.second)
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            create_date = kemas_extras.convert_to_tz(create_date, tz)
            result[collaborator[0]] = create_date
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
        now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
        now = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
        start = "%s-%s-%s 00:00:00" % (now.year, kemas_extras.completar_cadena(now.month), '01')
        end = "%s-%s-%s 23:59:59" % (now.year, now.month, kemas_extras.dias_de_este_mes())
        start = kemas_extras.convert_to_UTC_tz(start, tz)
        end = kemas_extras.convert_to_UTC_tz(end, tz)
        
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
            now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
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
            if not kemas_extras.validar_cedula_ruc(personal_id):
                values['personal_id'] = False
                warning = {'title' : u'¡Error!', 'message' : u"Número de Cédula Incorrecto. \nEn el caso de ser un Pasaporte ingrese la 'P' antes del número."}
        return {'value': values , 'warning': warning}
    
    _order = 'name'
    _name = 'kemas.collaborator'
    _columns = {
        'mailing': fields.function(mailing, type='boolean', string='Mailing'),
        'code': fields.char('Code', size=32, help="Code that is assigned to each collaborator"),
        'personal_id' : fields.char('CI/PASS', size=15, help=u"Número de cédula o pasaporte",),
        'photo': fields.binary('Photo', help='The photo of the person'),
        'photo_large': fields.binary('Large Photo'),
        'photo_medium': fields.binary('Medium Photo'),
        'photo_small': fields.binary('Small Photo'),
        'photo_very_small': fields.binary('Very Small Photo'),
        'qr_code': fields.function(_get_QR_image, type='binary', string='QR code data'),
        'bar_code': fields.function(_get_barcode_image, type='binary', string='Bar Code data'),
        'name': fields.char('Name', size=128, required=True, help="Full names of collaborator. Example: Rios Abad Juan David"),
        'nick_name': fields.char('Nick name', size=32, required=True, help="Name you want to use the collaborator."),
        'name_with_nick_name': fields.function(_get_nick_name, type='char', string='Name'),
        'birth': fields.date('Birth', help="Collaborator birthday date."),
        'birthday_date': fields.function(_get_birthday, type='char', string='Name'),
        'birthday': fields.function(_cal_birthday, type='datetime', string='Name'),
        'age': fields.function(_person_age, method=True, fnct_inv=_dummy_age, type='char', string='Age', size='128', help='The age of the collaborator'),
        'genre': fields.selection([('Male', 'Male'), ('Female', 'Female'), ], 'Genre', required=True, help="The genre of the collaborator",),
        'marital_status': fields.selection([('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widower', 'Widower')], 'Marital status', help="Marital Status of the collaborator"),
        'telef1': fields.char('Telefone 1', size=10, help="The number of phone of the collaborator. Example: 072878563"),
        'telef2': fields.char('Telefone 2', size=10, help="The number of phone of the collaborator. Example: 072878563"),
        'mobile': fields.char('Mobile', size=10, help="The number of mobile phone of the collaborator. Example: 088729345"),
        'email': fields.char('E-mail', size=128, required=True, help="The collaborator email."),
        'im_account': fields.char('IM account', size=128, required=False, help="IM account with which you can communicate with your collaborator."),
        'address': fields.char('Address', size=255, required=True, help="The collaborator address."),
        'vision': fields.text('Vision', help="The collaborator vision."),
        'mission': fields.text('Mission', help="The collaborator mission."),
        'web_site_ids': fields.one2many('kemas.collaborator.web.site', 'collaborator_id', 'Web sites', help='Web site of this collaborator'),
        'join_date': fields.date('Join date', help="Date on which the collaborator joined the Ministry."),
        'age_in_ministry': fields.function(_get_ministry_age, method=True, fnct_inv=_dummy_age, type='char', string='Age in ministry', size='128', help='Time the collaborator serves or served the ministry.'),
        'end_service': fields.date('End Service', help="Date on which the collaborator ceased to be an active part of the ministry."),
        'logbook_ids': fields.one2many('kemas.collaborator.logbook', 'collaborator_id', 'Logbook'),
        'state': fields.selection([
            ('creating', 'Creating'),
            ('Inactive', 'Inactive'),
            ('Locked', 'Locked'),
            ('Active', 'Active'),
            ('Suspended', 'Suspended'),
            ], 'State', select=True, help="State in which the collaborator is currently"),
        'type': fields.selection([
            ('Collaborator', 'Collaborator'),
            ('Others', 'Others')], 'Type', help="Type of person to be registered"),
        'born_country': fields.many2one('res.country', 'Born Country', required=False, help="the born country of the collaborator"),
        'born_state': fields.many2one('res.country.state', 'Born State', required=False, help="The born state of the collaborator"),
        'born_city': fields.char('Born City', size=255, required=True, help="The born city of the collaborator"),
        'user_id': fields.many2one('res.users', 'User', help='User assigned to this collaborator'),
        'login': fields.related('user_id', 'login', type='char', store=True, string='Username', readonly=1, help="Name under which the collaborator begins session"),
        'points': fields.integer('Points', help="points you currently have a collaborator"),
        'level_id': fields.many2one('kemas.level', 'Level', help='Level to which it belongs, for the points accumulated.'),
        'notified': fields.selection([
            ('notified', 'Notified'),
            ('no_notified', 'No notified'),
            ], 'Notified', select=True, help="Indicates whether the notification email was sent"),
        'last_connection': fields.function(_last_connection, type='char', string='Ultima Conexion'),
        'progress': fields.function(get_percentage, type='float', string='Progress'),
        'create_date': fields.function(_create_date, type='char', string='Created date'),
        'replacements': fields.function(_replacements, type='integer', string='Replacements avaliable', help="Number of replacements available events this month"),
        'ministry_ids': fields.many2many('kemas.ministry', 'kemas_ministry_collaborator_rel', 'collaborator_id', 'ministry_id', 'Ministerios'),
        'specialization_course_ids': fields.one2many('kemas.specialization.course.line', 'collaborator_id', 'Coursos de especializacion'),
        #Suspensions----------------------------------------------------------------------------------------------------------
        'suspension_ids': fields.one2many('kemas.suspension', 'collaborator_id', 'Suspensions'),
        'day_remaining_suspension': fields.function(_get_days_remaining, type='char', string='Days remaining'),
        #One to Many Relations-----------------------------------------------------------------------------------------------
        'school4d_ids': fields.one2many('kemas.school4d_line', 'collaborator_id', 'Persons'),
        'history_points_ids': fields.one2many('kemas.history.points', 'collaborator_id', 'History points'),
        'attendance_ids': fields.one2many('kemas.attendance', 'collaborator_id', 'Attendances', help='Attendance register'),
        'team_id': fields.many2one('kemas.team', 'Team', help='Equipment to which this Collaborator.'),
        #Many to Many Relations----------------------------------------------------------------------------------------------
        'area_ids': fields.many2many('kemas.area', 'kemas_collaborator_area_rel', 'collaborator_id', 'area_id', 'Areas', help='Areas belonging to this collaborator'),
        #Related-------------------------------------------------------------------------------------------------------------
        'level_name': fields.related('level_id', 'name', type='char', string='Level name', readonly=1, store=False),
        'username': fields.related('user_id', 'login', type='char', string='Login', readonly=1, store=True),
        'password': fields.related('user_id', 'password', type='char', string='Password', readonly=1, store=False),
        }
    
    def get_photo_male(self):
        photo_path = addons.get_module_resource('kemas', 'images', 'male.png')
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_photo_small_male(self):
        photo_path = addons.get_module_resource('kemas', 'images', 'male_small.jpg')
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_photo_female(self):
        photo_path = addons.get_module_resource('kemas', 'images', 'female.png')
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_photo_small_female(self):
        photo_path = addons.get_module_resource('kemas', 'images', 'female_small.jpg')
        return open(photo_path, 'rb').read().encode('base64')
    
    def get_first_level(self, cr, uid, context={}):
        level_obj = self.pool.get('kemas.level')
        level_ids = level_obj.search(cr, uid, [('first_level', '=', True)])
        if level_ids:
            return level_ids[0]

    _constraints = [
        (validate_four_names, 'At least two valid names must be entered.', ['name'])
        ]
    
    _sql_constraints = [
        ('collaborator_code', 'unique (code)', 'This Code already exist!'),
        ('collaborator_name', 'unique (name)', "This Collaborator's already exist!"),
        ('collaborator_user_id', 'unique (user_id)', 'This User already exist!'),
        ]

_TASK_STATE = [('creating', 'Creating'), ('draft', 'New'), ('open', 'In Progress'), ('pending', 'Pending'), ('done', 'Done'), ('cancelled', 'Cancelled')]
class kemas_task_category(osv.osv):
    _name = "kemas.task.category"
    _description = "Category of task, issue, ..."
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
    }
    
class kemas_task_type(osv.osv):
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    _name = 'kemas.task.type'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Stage Name', required=True, size=64, translate=True),
        'description': fields.text('Description'),
        'sequence': fields.integer('Sequence'),
        'case_default': fields.boolean('Default for New Projects',
                        help="If you check this field, this stage will be proposed by default on each new project. It will not assign this stage to existing projects."),
        'state': fields.selection(_TASK_STATE, 'Related Status', required=True,
                        help="The status of your document is automatically changed regarding the selected stage. " \
                            "For example, if a stage is related to the status 'Close', when your document reaches this stage, it is automatically closed."),
        'fold': fields.boolean('Folded by Default',
                        help="This stage is not visible, for example in status bar or kanban view, when there are no records in that stage to display."),
    }
    _defaults = {
        'sequence': 1,
        'state': 'open',
        'fold': False,
        'case_default': False,
    }
    _order = 'sequence'
    
class kemas_task(osv.osv):
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_all', False) == False:
            args.append(('is_active', '=', True))       
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    _name = 'kemas.task'
    _columns = {
        'name': fields.char('Name', size=200, help="Work Name", required=True),
        'points': fields.integer('Points', required=True, help='Points that he will add the collaborator to fulfill the work'),
        'is_active': fields.boolean('Active', required=False, help='Indicates whether this work is active or not'),
        'description': fields.text('Description', required=True),
        }
    _sql_constraints = [
        ('uname', 'unique (name)', 'This name already exist!'),
        ]
    _defaults = {  
        'points': 1000,
        'is_active':True
        }

class kemas_task_assigned(osv.osv):
    def close_tasks(self, cr, uid, context={}):
        task_ids = self.search(cr, uid, [('state', 'in', ['draft', 'open', 'pending']), ('date_limit', '!=', False)])
        tasks = self.read(cr, uid, task_ids, ['date_limit'])
        if task_ids:
            print '    >>Cerrando tareas Caducadas'
            context['tz'] = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            now = unicode(kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), context['tz']))
            for task in tasks:
                date_limit = kemas_extras.convert_to_UTC_tz(task['date_limit'], context['tz'])
                if now > date_limit:
                    self.do_cancel(cr, uid, [task['id']], context, True)        
        return True
    
    def write_log_new(self, cr, uid, task_id, notify_partner_ids=[]):
        state = self.pool.get('kemas.func').get_translate(cr, uid, self.read(cr, uid, task_id, ['state'])['state'])[0].title()
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Tarea Completada'), _('Estado'), state, _('Nuevo'))
        return self.write_log_update(cr, uid, task_id, body, notify_partner_ids)
    
    def write_log_on_going(self, cr, uid, task_id, notify_partner_ids=[]):
        state = self.pool.get('kemas.func').get_translate(cr, uid, self.read(cr, uid, task_id, ['state'])['state'])[0].title()
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Tarea Completada'), _('Estado'), state, _('En Curso'))
        return self.write_log_update(cr, uid, task_id, body, notify_partner_ids)
    
    def write_log_cancelled(self, cr, uid, task_id, notify_partner_ids=[]):
        state = self.pool.get('kemas.func').get_translate(cr, uid, self.read(cr, uid, task_id, ['state'])['state'])[0].title()
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Tarea Completada'), _('Estado'), state, _('Cancelado'))
        collaborator_id = self.read(cr, uid, task_id, ['collaborator_id'])['collaborator_id'][0]
        partner_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, collaborator_id)
        return self.write_log_update(cr, uid, task_id, body, [partner_id])
    
    def write_log_cancelled_by_system(self, cr, uid, task_id, notify_partner_ids=[]):
        state = self.pool.get('kemas.func').get_translate(cr, uid, self.read(cr, uid, task_id, ['state'])['state'])[0].title()
        body = u'''
        <div>
            <span>
                <b>Tarea Cerrada</b>
            </span>
            <div>El tiempo límite de entrega ha terminado</div>
        </div>
        '''
        task = self.read(cr, uid, task_id, ['collaborator_id', 'date_limit', 'task_id'])
        collaborator_id = task['collaborator_id'][0]
        partner_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, collaborator_id)
        
        # Suspender al colaborador
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        
        preferences = self.pool.get('kemas.config').read(cr, uid, self.pool.get('kemas.config').get_correct_config(cr, uid), ['day_to_suspension_task_closed'])
        days = int(preferences['day_to_suspension_task_closed'])
        date_end_suspension = self.pool.get('kemas.suspension').get_end_date(cr, uid, days, True, True, True, True, True, True, True)
        description = '''La tarea '%s' que se te fue asignada no fue entregada a tiempo.''' % task['task_id'][1]
        self.pool.get('kemas.collaborator').suspend(cr, uid, [collaborator_id], date_end_suspension, description, task_id)
        return self.write_log_update(cr, uid, task_id, body, [partner_id])
    
    def write_log_closed(self, cr, uid, task_id, notify_partner_ids=[]):
        state = self.pool.get('kemas.func').get_translate(cr, uid, self.read(cr, uid, task_id, ['state'])['state'])[0].title()
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Tarea Completada'), _('Estado'), state, _('Cerrado'))
        
        collaborator_id = self.read(cr, uid, task_id, ['collaborator_id'])['collaborator_id'][0]
        partner_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, collaborator_id)
        return self.write_log_update(cr, uid, task_id, body, [partner_id])

    
    def write_log_completed(self, cr, uid, task_id, notify_partner_ids=[]):
        state = self.pool.get('kemas.func').get_translate(cr, uid, self.read(cr, uid, task_id, ['state'])['state'])[0].title()
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Tarea Completada'), _('Estado'), state, _('Completado'))
        return self.write_log_update(cr, uid, task_id, body, notify_partner_ids) 
    
    def write_log_update(self, cr, uid, task_id, body, notify_partner_ids=[]):
        # --Escribir un mensaje con un registro de que se paso Estado en Curso
        user_obj = self.pool.get('res.users')
        message_obj = self.pool.get('mail.message')
        
        task_name = self.name_get(cr, uid, [task_id])[0][1]
        partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        vals_message = {
                        'body' : body,
                        'model' : 'kemas.task.assigned',
                        'record_name' : task_name,
                        'res_id' : task_id,
                        'partner_id' : partner_id,
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
    
    def unlink(self, cr, uid, ids, context={}):
        works = self.read(cr, uid, ids, ['state'])
        for work in works:
            if work['state'] in ['confirmed', 'nulled']:
                raise osv.except_osv(_('Error!'), _('You can not delete this work.'))
        return super(osv.osv, self).unlink(cr, uid, ids, context)
    
    def name_get(self, cr, uid, ids, context={}):
        records = self.read(cr, uid, ids, ['id', 'task_id', 'collaborator_id'])
        res = []
        for record in records:
            name = "%s - %s" % (unicode(record['task_id'][1]), unicode(record['collaborator_id'][1]))
            res.append((record['id'], name))  
        return res
        
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('task_id.name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context is None or type(context).__name__ != "dict":
            return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        
        if context.get('is_collaborator', False):
            collaborator_obj = self.pool.get('kemas.collaborator')
            collaborator_ids = super(kemas_collaborator, collaborator_obj).search(cr, uid, [('user_id', '=', uid)])
            args.append(('collaborator_id', 'in', collaborator_ids))
        
        if context.get('search_all', False) == False:
            args.append(('is_active', '=', True))  
            
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_created', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('date_created', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def do_close(self, cr, uid, ids, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        work_obj = self.pool.get('kemas.task')
        works = self.read(cr, uid, ids, ['collaborator_id', 'task_id'])
        for work in works:
            related_work = work_obj.read(cr, uid, work['task_id'][0], ['points', 'description'])
            collaborator_obj.add_remove_points(cr, uid, [work['collaborator_id'][0]], related_work['points'], related_work['description'], 'increase')
        vals = {
                'date_closing' :time.strftime("%Y-%m-%d %H:%M:%S"),
                'state' : 'done',
                'is_active': False
                }
        stage_ids = self.pool.get('kemas.task.type').search(cr, uid, [('state', '=', 'done'), ('name', '!=', 'Completed')])
        if stage_ids:
            vals['stage_id'] = stage_ids[0]

        message_follower_ids = self.read(cr, uid, ids[0], ['message_follower_ids'])['message_follower_ids']
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        if partner_id in message_follower_ids:
            message_follower_ids.remove(partner_id)
        self.write_log_closed(cr, uid, ids[0], message_follower_ids)
        super(osv.osv, self).write(cr, uid, ids, vals)
        
    def do_cancel(self, cr, uid, ids, context={}, bysystem=False):
        vals = {
                'date_cancelled' :time.strftime("%Y-%m-%d %H:%M:%S"),
                'state' : 'cancelled',
                'is_active': False
                }
        stage_ids = self.pool.get('kemas.task.type').search(cr, uid, [('state', '=', 'cancelled')])
        if stage_ids:
            vals['stage_id'] = stage_ids[0]
            
        message_follower_ids = self.read(cr, uid, ids[0], ['message_follower_ids'])['message_follower_ids']
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        if partner_id in message_follower_ids:
            message_follower_ids.remove(partner_id)
        
        if not bysystem:
            self.write_log_cancelled(cr, uid, ids[0], message_follower_ids)
            super(osv.osv, self).write(cr, uid, ids, vals)
        else:
            self.write_log_cancelled_by_system(cr, uid, ids[0], message_follower_ids)
            error = True
            while error:
                try:
                    cr.commit()
                    super(osv.osv, self).write(cr, uid, ids, vals)
                    error = False
                except:
                    error = True
        return False
    
    def write(self, cr, uid, ids, vals, context={}):
        if type(ids).__name__ == 'int' : 
            ids = [ids] 
        for task_assigned in super(osv.osv, self).read(cr, uid, ids, ['state', 'stage_id', 'is_active', 'message_follower_ids']):
            if not task_assigned['is_active']:
                raise osv.except_osv(_('Error!'), _('No se puede modificar una tarea Cerrada o Cancelada.'))
            
            if vals.get('stage_id'):
                stage = self.pool.get('kemas.task.type').read(cr, uid, vals['stage_id'], ['state', 'name'])
                state = stage['state']
                if state in ['done', 'cancelled'] and stage['name'] != 'Completed':
                    raise osv.except_osv(_('Error!'), _('Para cancelar o Cerrar una Tarea hay que dar click en el boton respectivo.'))
                
                if state in ['draft', 'open', 'pending', 'done']:
                    if stage['name'] == 'New':
                        self.write_log_new(cr, uid, task_assigned['id'])
                    elif  stage['name'] == 'On going':
                        vals['date_start'] = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.write_log_on_going(cr, uid, task_assigned['id'])
                    elif stage['name'] == 'Completed':
                        vals['date_end'] = time.strftime("%Y-%m-%d %H:%M:%S")
                        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
                        if partner_id in task_assigned['message_follower_ids']:
                            task_assigned['message_follower_ids'].remove(partner_id)
                        self.write_log_completed(cr, uid, task_assigned['id'], task_assigned['message_follower_ids'])
        
        return super(osv.osv, self).write(cr, uid, ids, vals, context)
     
    def create(self, cr, uid, vals, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        vals['user_id'] = collaborator_obj.read(cr, uid, vals['collaborator_id'], ['user_id'])['user_id'][0]
        vals['date_created'] = time.strftime("%Y-%m-%d %H:%M:%S")
        vals['color'] = random.randint(0, 9)
        return super(osv.osv, self).create(cr, uid, vals, context)
    
    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        stage_ids = self.pool.get('kemas.task.type').search(cr, uid, [('state', '=', 'draft')])
        if stage_ids:
            return stage_ids[0]
        return False
    
    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('kemas.task.type')
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid
        if read_group_order == 'stage_id desc':
            order = '%s desc' % order
        search_domain = []
        # search_domain += [('id', 'in', ids)]
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    def _read_group_user_id(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        res_users = self.pool.get('res.users')
        result = res_users.name_get(cr, access_rights_uid, ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(ids.index(x[0]), ids.index(y[0])))
        return result, {}

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
        'user_id': _read_group_user_id,
    }

    _name = 'kemas.task.assigned'
    _order = "priority, sequence, date_start DESC, task_id, id"
    _date_name = "date_start"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'task_id'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', required=True, help='Collaborator to perform this task.'),
        'task_id': fields.many2one('kemas.task', 'Task', required=True, help='Work name you turned.'),
        'description': fields.text('Description', required=True),
        'priority': fields.selection([('4', 'Very Low'), ('3', 'Low'), ('2', 'Medium'), ('1', 'Important'), ('0', 'Very important')], 'Priority', select=True),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of tasks."),
        'stage_id': fields.many2one('kemas.task.type', 'Stage'),
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=_TASK_STATE, string="Status", readonly=True),
        'categ_ids': fields.many2many('kemas.task.category', string='Tags'),
        'create_date': fields.datetime('Create Date', readonly=True, select=True),
        'notes': fields.text('Notes'),
        'user_id': fields.many2one('res.users', 'Assigned to', track_visibility='onchange'),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'is_active': fields.boolean('Is active', required=False),
        'date_created': fields.datetime('Creation date', help='Date of creation of this task'),
        'date_closing': fields.datetime('Closing date', help='Closing date for This Task'),
        'date_cancelled': fields.datetime('Cancellation date', help='Cancellation date of This Task'),
        'date_start': fields.datetime('Starting Date', select=True),
        'date_end': fields.datetime('Ending Date', select=True),
        'date_limit': fields.datetime('Fecha de entrega', help="Fecha limite de entrega de esta tarea"),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
    
    def _validate(self, cr, uid, ids, context={}): 
        this = self.read(cr, uid, ids[0], ['collaborator_id', 'task_id'])
        args = [('collaborator_id', '=', this['collaborator_id'][0]), ('task_id', '=', this['task_id'][0]), ('state', 'in', ['waiting_for_confirmation'])]
        task_ids = self.search(cr, uid, args)
        if len(task_ids) > 1:
            raise osv.except_osv(_('Error!'), _("You've entered this task and has not yet been confirmed."))
        
    _constraints = [(_validate, 'Error: Invalid Message', ['field_name']), ]
    
    _defaults = {
        'stage_id': _get_default_stage_id,
        'state': 'creating',
        'priority': '2',
        'sequence': 10,
        'is_active': True,
        'user_id': lambda obj, cr, uid, ctx = None: uid,
    }
    
    def set_high_priority(self, cr, uid, ids, *args):
        """Set task priority to high
        """
        return self.write(cr, uid, ids, {'priority' : '0'})

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set task priority to normal
        """
        return self.write(cr, uid, ids, {'priority' : '2'})
    
class kemas_history_points(osv.osv):
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False):
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_history_points, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby)
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
    
    def write_log_create(self, cr, uid, res_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                • <b>Modificacion de Puntos</b>
            </span>
        </div>
        '''
        # Borrar los logs que creados por defecto
        self.pool.get('mail.message').unlink(cr, SUPERUSER_ID, self.pool.get('mail.message').search(cr, uid, [('res_id', '=', res_id)]))
        return self.write_log_update(cr, uid, res_id, body, notify_partner_ids) 
    
    def write_log_update(self, cr, uid, res_id, body, notify_partner_ids=[]):
        # --Escribir un mensaje con un registro de que se paso Estado en Curso
        user_obj = self.pool.get('res.users')
        message_obj = self.pool.get('mail.message')
        
        res_name = self.name_get(cr, uid, [res_id])[0][1]
        partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        vals_message = {
                        'body' : body,
                        'model' : 'kemas.history.points',
                        'record_name' : res_name,
                        'res_id' : res_id,
                        'partner_id' : partner_id,
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
        res_id = super(osv.osv, self).create(cr, uid, vals, context)
        
        partner_id = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        if partner_id in follower_ids:
            follower_ids.remove(partner_id)
        self.write_log_create(cr, uid, res_id, follower_ids)
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
    def do_activate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'is_active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'is_active': False})
        return True
    
    def __fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=True, submenu=False):       
        from lxml import etree
        res = super(kemas_place, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=False, submenu=False)
        if res['type'] == 'form':
            url_map = "https://www.google.com.ec/maps?t=m&amp;ie=UTF8&amp;ll=-2.897671,-78.997305&amp;spn=0.001559,0.002511&amp;z=19&amp;output=embed" 
            map = """
            <iframe width="100%%" height="350" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" src="%s"></iframe>
            <br /><small><a href="%s" style="color:#0000FF;text-align:left" target="blank">Ver mapa más grande</a></small>
            """ % (url_map, url_map)
            res['arch'] = res['arch'].replace('<!-- mapa -->', map.encode('utf-8'))
        return res
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_all', False) == False:
            args.append(('is_active', '=', True))       
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)

    def on_change_photo(self, cr, uid, ids, photo):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        #------------------------------------------------------------------------------------
        values = {} 
        if kemas_extras.restrict_size(photo, preferences['max_size_photos']):
            return {'value':{}}
        else:
            msg = self.pool.get('kemas.func').get_translate(cr, uid, _('The size of the photo can not be greater than'))[0]
            msg = "%s %s KB..!!" % (msg, str(preferences['max_size_photos']))
            return {'value':{'photo': False}, 'warning':{'title':_('Error!'), 'message':msg}}
        
    _order = 'name'
    _name = 'kemas.place'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='The name of the place'),
        'address': fields.text('Address'),
        'Map': fields.text('Mapa'),
        'photo': fields.binary('Photo', help='the photo of the place'),
        'is_active': fields.boolean('Active', required=False, help='Indicates whether this place is active or not'),
        }
    _sql_constraints = [
        ('place_name', 'unique (name)', 'This Name already exist!'),
        ]
    _defaults = {  
        'is_active':True 
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
                        'partner_id' : partner_id,
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
        super(osv.osv, self).write(cr, uid, ids, {'is_active' : True})
        return True
    
    def do_inactivate(self, cr, uid, ids, context={}):
        super(osv.osv, self).write(cr, uid, ids, {'is_active': False})
        return True
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context={}, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_all', False) == False:
            args.append(('is_active', '=', True))       
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)

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
            raise osv.except_osv(_('Error!'), _('The start time must be less than the end time.'))
        #----El tiempo para registro puntual no puede ser mayor al tiempo limite de registro------------------------------------------------------.
        if float(service['time_register']) >= float(service['time_limit']):
            raise osv.except_osv(_('Error!'), _('The time of entry can not be longer than the time limit.'))
        #----La hora de entrada no puede ser mayor a la hora de finalizacion de servicio----------------------------------------------------------.
        if float(service['time_entry']) >= float(service['time_end']):
            raise osv.except_osv(_('Error!'), _('The time of entry can not be longer than the end time.'))
        #----La hora de entrada sumada mas el tiempo para registro puntual no puede ser mayor a la la hora de finalizacion de servicio------------.
        if (float(service['time_entry']) + float(service['time_register'])) >= float(service['time_end']):
            raise osv.except_osv(_('Error!'), _('The time of entry coupled with the time of entry can not be longer than the time end.'))
        #----La hora de entrada sumada mas el tiempo limite registro de asistencia no puede ser mayor a la la hora de finalizacion de servicio----.
        if (float(service['time_entry']) + float(service['time_limit'])) >= float(service['time_end']):
            raise osv.except_osv(_('Error!'), _('The time of entry coupled with the time limit can not be longer than the time end.'))
        return True
    
    _order = 'time_start'
    _name = 'kemas.service'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'time_start': fields.float('Time start', required=True, help='Start time of service'),
        'time_end': fields.float('Time end', required=True, help='End time of service'),
        'time_entry': fields.float('Time entry', required=True, help='End time of service'),
        #----------------------------------------------------------------------------------------------
        'time_register': fields.float('Time register', required=True, help='End time of service'),
        'time_limit': fields.float('Time limit', required=True, help='Limit time to register attendance'),
        'description': fields.text('Description'),
        'is_active': fields.boolean('Active', required=False, help='Indicates whether this service is active or not'),
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
        'is_active':True
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
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False):
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_event_collaborator_line, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby)
        return result
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context={}, count=False):
        if context.get('search_filter', False):
            if context.has_key('search_filter') == 1:
                args.append(('event_id.state', 'in', ['on_going', 'closed', 'draft']))
        
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('event_id.date_start', '>=', range_dates['date_start']))
            args.append(('event_id.date_stop', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('event_id.date_start', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('event_id.date_stop', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    _name = 'kemas.event.collaborator.line'
    _rec_name = 'collaborator_id'
    _columns = {
        'collaborator_id': fields.many2one('kemas.collaborator', 'Collaborator', required=True),
        'event_id': fields.many2one('kemas.event', 'event', required=True, ondelete="cascade"),
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
        'genre': fields.related('collaborator_id', 'genre', type='selection', selection=[('Male', 'Male'), ('Female', 'Female'), ], string='Genre'),
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

                compose_obj = self.pool.get('mail.compose.message')
                partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
                sql = """
                select c.res_id from mail_compose_message c
                join mail_compose_message_res_partner_rel as rel on (rel.wizard_id = c.id)
                where rel.partner_id in (%d) and c.model = 'kemas.event' 
                group by c.res_id
                """ % (partner_id)
                cr.execute(sql)
                l2 = kemas_extras.convert_result_query_to_list(cr.fetchall())
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
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_start', '>=', range_dates['date_start']))
            args.append(('date_start', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_start', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
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
                """ % (collaborator_id, kemas_extras.convert_to_tuple_str(res_ids))
            cr.execute(sql)
            res_ids = list(set(kemas_extras.convert_result_query_to_list(cr.fetchall())))
        
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
                date = str(kemas_extras.convert_to_tz(record.date_start, tz))[:16]
                name = (unicode(record.service_id.name) + ' | ' + date + '-' + str(kemas_extras.convert_float_to_hour_format(record.service_id.time_end)))
            elif record.state in ['creating']:
                date = str(kemas_extras.convert_to_tz(record.date_start, tz))[:16]
                name = name = (unicode(record.service_id.name) + ' | ' + str(date))
            else:                
                date = str(kemas_extras.convert_to_tz(record.rm_date, tz))[:16]
                name = (record.rm_service + ' | ' + str(date) + ' - ' + str(kemas_extras.convert_float_to_hour_format(record.rm_time_end)))
            res.append((record.id, name))
        return res
    
    def send_email(self, cr, uid, ids, context={}):
        config_obj = self.pool.get('kemas.config')
        config_id = config_obj.get_correct_config(cr, uid)
        preferences = config_obj.read(cr, uid, config_id, [])
        if preferences['mailing'] == False or preferences['use_message_event'] == False: 
            raise osv.except_osv(_('Error!'), _('Notifications are disabled.'))
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
            SELECT cl.id,cl.nick_name,cl.name,U.login as username FROM kemas_collaborator AS cl
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
        attendance_list = []
        
        for collaborator in result_query:
            name = "%s %s" % (
                             unicode(collaborator['nick_name']).title(),
                             unicode(collaborator['name']).split()[0].title()
                             )
            collaborator_dic = {
                            'id': collaborator['id'],
                            'name': name,
                            'username': collaborator['username'],
                            'registered': is_registered(event_id, collaborator['id']),
                            }
            collaborators.append(collaborator_dic)
        
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
        now = datetime.strptime(kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz), '%Y-%m-%d %H:%M:%S')
        date_today = "%s-%s-%s %s" % (kemas_extras.completar_cadena(now.year, 4), kemas_extras.completar_cadena(now.month), kemas_extras.completar_cadena(now.day), "00:00:00")
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
            """ % (date_today, kemas_extras.convert_to_tuple_str(except_list))
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
                dt = datetime.strptime(kemas_extras.convert_to_tz(event[2], tz), '%Y-%m-%d %H:%M:%S')
                date_event = "%s-%s-%s %s" % (kemas_extras.completar_cadena(dt.year, 4), kemas_extras.completar_cadena(dt.month), kemas_extras.completar_cadena(dt.day), "00:00:00")
                if date_event == date_today:
                    if event[3] > float(now.hour) + float(now.minute) / 60:
                        valid = True
                    else:
                        valid = False
                        event_ids.append(event[0])
                else:
                    valid = True
        if event:  
            date = datetime.strptime(kemas_extras.convert_to_tz(event[2], tz), '%Y-%m-%d %H:%M:%S')
            time_entry = kemas_extras.convert_float_to_hour_format(event[3], True)
            date = "%s-%s-%s %s" % (kemas_extras.completar_cadena(date.year, 4), kemas_extras.completar_cadena(date.month), kemas_extras.completar_cadena(date.day), time_entry)
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
                if kemas_extras.convert_to_tz(event[1], tz, res=1) == kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz, res=1):
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
            time_entry = kemas_extras.convert_float_to_hour_format(service['time_entry'])
            line_event['time_entry'] = time_entry
            hour = str(time_entry)[:2]
            minutes = str(time_entry)[3:5]
            time_entry = int(minutes) + int(hour) * 60
            line_event['time_entry_int'] = time_entry
            
            #----Hora Limite de Registro a Tiempo------------------------------------------------
            time_register = kemas_extras.convert_float_to_hour_format(service['time_register'])
            line_event['time_register'] = time_register
            hour = str(time_register)[:2]
            minutes = str(time_register)[3:5]
            time_register = int(minutes) + int(hour) * 60
            line_event['time_register_int'] = time_entry + time_register
            
            #----Hora Limite de Registro---------------------------------------------------------
            time_limit = kemas_extras.convert_float_to_hour_format(service['time_limit'])
            line_event['time_limit'] = time_limit
            hour = str(time_limit)[:2]
            minutes = str(time_limit)[3:5]
            time_limit = int(minutes) + int(hour) * 60
            line_event['time_limit_int'] = time_entry + time_limit
            
            #----Hora de Inicio------------------------------------------------------------------
            time_start = kemas_extras.convert_float_to_hour_format(service['time_start'])
            line_event['time_start'] = time_start
            hour = str(time_start)[:2]
            minutes = str(time_start)[3:5]
            time_start = int(minutes) + int(hour) * 60
            line_event['time_start_int'] = time_start
            
            #----Hora de Finalizacion------------------------------------------------------------
            time_end = kemas_extras.convert_float_to_hour_format(service['time_end'])
            line_event['time_end'] = time_end
            hour = str(time_end)[:2]
            minutes = str(time_end)[3:5]
            time_end = int(minutes) + int(hour) * 60
            line_event['time_end_int'] = time_end
            
            current_event = self.get_current_event(cr, uid)
            if event['id'] == current_event:
                line_event['current_event'] = True
            else:
                line_event['current_event'] = False 
            res.append(line_event)
        return res
        
    def get_current_event(self, cr, uid, extra_info=False):
        service_obj = self.pool.get('kemas.service')
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        event_ids = super(osv.osv, self).search(cr, uid, [('date_init', '<=', now), ('date_stop', '>=', now), ('state', '=', 'on_going')])
        if event_ids:
            for event_id in event_ids:
                event = self.read(cr, uid, event_id, ['service_id'])
                service = service_obj.read(cr, uid, event['service_id'][0], [])
                #----Convertir la hora de entrada a Entero---------------------------------------
                time_entry = kemas_extras.convert_float_to_hour_format(service['time_entry'])
                hour = str(time_entry)[:2]
                minutes = str(time_entry)[3:5]
                time_entry = int(minutes) + int(hour) * 60
                #----Convertir la hora actual a Entero-------------------------------------------
                tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
                now = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
                hour = str(now)[11:13]
                minutes = str(now)[14:16]
                now = int(minutes) + int(hour) * 60
                #----Genrar la hora limite-------------------------------------------------------
                time_limit = kemas_extras.convert_float_to_hour_format(service['time_limit'])
                hour = str(time_limit)[:2]
                minutes = str(time_limit)[3:5]
                time_limit = int(minutes) + int(hour) * 60
                #----Genrar la hora para registro puntual de puntos------------------------------
                time_register = kemas_extras.convert_float_to_hour_format(service['time_register'])
                hour = str(time_register)[:2]
                minutes = str(time_register)[3:5]
                time_register = int(minutes) + int(hour) * 60
                #----Validar si el evento es valido para registro de asistencia o no-------------
                if time_entry <= now and (time_entry + time_limit) > now:
                    if extra_info:
                        return {
                                'current_event_id': event_id,
                                'minutes_remaining': (time_entry + time_limit) - now,
                                'time_entry': time_entry,
                                'now': now,
                                'time_limit': time_limit,
                                'time_register': time_register,
                               }
                    else:
                        return event_id
        return None
 
    def write(self, cr, uid, ids, vals, context={}):
        if type(ids[0]).__name__ == 'dict':
            if ids[0].has_key('res_id'):
                ids = [ids[0]['res_id']]
            
        event = super(osv.osv, self).read(cr, uid, ids[0], [])
        if event['sending_emails']:
            raise osv.except_osv(_('Error!'), _('You can not make changes to this event as they send notification e-mails.'))
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
                    raise osv.except_osv(_('Error!'), _(''))
            if stage['sequence'] == 2:  # on_going
                if event['state'] == 'draft':
                    vals['state'] = 'on_going'
                    written = True
                else:
                    raise osv.except_osv(_('Error!'), _(''))
            elif stage['sequence'] == 3:  # closed
                raise osv.except_osv(_('Error!'), _(''))
            elif stage['sequence'] == 4:  # canceled
                raise osv.except_osv(_('Error!'), _('')) 
            else:
                written = True
        if context.has_key('change_service') == False:
            if written:
                cr.commit()
                super(kemas_event, self).write(cr, uid, ids, vals, context)
                cr.commit() 
                return True
            
            if event['state'] == 'closed':raise osv.except_osv(_('Error!'), _('The event has been Closed and can not be changed.'))
            if event['state'] == 'canceled':raise osv.except_osv(_('Error!'), _('The event has been Canceled and can not be changed.'))
            if event['state'] == 'on_going':raise osv.except_osv(_('Error!'), _('The event is on going and can not be changed.'))
        else:
            if context['change_service'] == False:
                if written:
                    cr.commit()
                    super(kemas_event, self).write(cr, uid, ids, vals, context)
                    cr.commit()
                    return True
                if event['state'] == 'closed':raise osv.except_osv(_('Error!'), _('The event has been Closed and can not be changed.'))
                if event['state'] == 'canceled':raise osv.except_osv(_('Error!'), _('The event has been Canceled and can not be changed.'))
                if event['state'] == 'on_going':raise osv.except_osv(_('Error!'), _('The event is on going and can not be changed.'))
        service_obj = self.pool.get('kemas.service')
        #---------------------------------------------------------------------------------------------------------------------------
        #--Change Date start y date stop---------------------------------------------------------------------------------------------
        service = service_obj.read(cr, uid, event['service_id'][0], [])
        if vals.has_key('service_id'):
            if vals['service_id']:
                service = service_obj.read(cr, uid, vals['service_id'], [])   
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        date_start = kemas_extras.convert_to_tz(event['date_start'], tz)
        if vals.has_key('date_start'):
            if vals['date_start']:
                if vals['date_start'] < time.strftime("%Y-%m-%d %H:%M:%S"):
                    raise osv.except_osv(_('Error!'), _('Unable to move an event in a past date.'))
                date_start = vals['date_start']
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        dates_dic = kemas_extras.convert_to_format_date(date_start, service['time_entry'], service['time_start'], service['time_end'], tz)
        vals['date_start'] = dates_dic['date_start']
        vals['date_stop'] = dates_dic['date_stop']
        vals['date_init'] = dates_dic['date_init']
        #----------------------------------------------------------------------------------------------------------------------------
        res = super(osv.osv, self).write(cr, uid, ids, vals, context)
        lines_obj = self.pool.get('kemas.event.collaborator.line')
        collaborator_line_ids = self.read(cr, uid, ids, ['event_collaborator_line_ids'])
        line_ids = []
        for line in collaborator_line_ids:
            line_ids += line['event_collaborator_line_ids']
        lines = lines_obj.read(cr, uid, line_ids, ['collaborator_id'])
        members = []
        for line in lines:
            collaborator_id = line['collaborator_id'][0]
            user_id = super(kemas_collaborator, self.pool.get('kemas.collaborator')).read(cr, uid, collaborator_id, ['user_id'])['user_id'][0]
            members.append(user_id)
        vals = {'members' : [(6, 0, members)]}
        return super(osv.osv, self).write(cr, uid, ids, vals, context)
         
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
        
    def create(self, cr, uid, vals, context={}):
        service_obj = self.pool.get('kemas.service')
        vals['date_create'] = str(time.strftime("%Y-%m-%d %H:%M:%S"))
        vals['state'] = 'draft'
        vals['count'] = 1
        #--Crear Date start y date stop---------------------------------------------------------------------------------------------
        service = service_obj.read(cr, uid, vals['service_id'], [])
        dates_dic = kemas_extras.convert_to_format_date(vals['date_start'], service['time_entry'], service['time_start'], service['time_end'], context['tz'])
        vals['date_start'] = dates_dic['date_start']
        vals['date_stop'] = dates_dic['date_stop']
        vals['date_init'] = dates_dic['date_init']
        # --Evitar que se cree un evento en una fecha pasada-
        if vals['date_start'] < time.strftime("%Y-%m-%d %H:%M:%S"):
            raise osv.except_osv(_('Error!'), _('Unable to create an event in a past date.'))
        
        res_id = super(kemas_event, self).create(cr, uid, vals, context)
        lines_obj = self.pool.get('kemas.event.collaborator.line')
        collaborator_line_ids = self.read(cr, uid, [res_id], ['event_collaborator_line_ids'])
        line_ids = []
        for line in collaborator_line_ids:
            line_ids += line['event_collaborator_line_ids']
        lines = lines_obj.read(cr, uid, line_ids, ['collaborator_id'])
        members = []
        for line in lines:
            collaborator_id = line['collaborator_id'][0]
            user_id = super(kemas_collaborator, self.pool.get('kemas.collaborator')).read(cr, uid, collaborator_id, ['user_id'])['user_id'][0]
            members.append(user_id)
        vals = {'members' : [(6, 0, members)]}
        super(osv.osv, self).write(cr, uid, [res_id], vals)
        
        # Escribir log
        self.write_log_create(cr, uid, res_id)
        return res_id
        return {
            'nodestroy': True,
            'res_id': res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kemas.event',
            'type': 'ir.actions.act_window',
            }
    
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
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        #--------------------------------------------------------------------------------------------
        event_ids = self.get_past_events(cr, uid, False)
        print """\n
                 -------------------------------------------------------------------------------------------------------------------------
                 ***************************************CLOSE PAST EVENTS*****************************************************************"""
        cont = 0
        for event_id in event_ids:
            cont += 1
            self.close_event(cr, uid, event_id)
            event = self.read(cr, uid, event_id, ['id', 'service_id', 'date_start']) 
            event_name = self.name_get(cr, uid, [event_id])[0][1]
            cr.commit()
            print """\t\t\t* Closed: %s """ % (event_name)
        tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        print """
    
                     [%d] Past events successfully closed: %s
                 -------------------------------------------------------------------------------------------------------------------------\n""" % (cont, kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz))
    def close_event(self, cr, uid, event_id, context={}):   
        def send_notifications(self):
            def send(self, db_name, uid):
                db, pool = pooler.get_db_and_pool(db_name)
                cr = db.cursor()
                cr.commit()
                config_obj = self.pool.get('kemas.config')
                count = 0
                for collaborator in noticaciones['collaborators']:
                    count += 1
                    config_obj.send_email_event_completed(cr, uid, noticaciones['service_id'], noticaciones['event_id'], collaborator['id'], collaborator['type'])
                print """\n
                 -------------------------------------------------------------------------------------------------------------------------
                 **********************************************[%d] Event notifications sent over****************************************
                 -------------------------------------------------------------------------------------------------------------------------\n""" % (count)
                cr.commit()
                 
            threaded_sending = threading.Thread(target=send, args=(self, cr.dbname, uid))
            threaded_sending.start()
                  
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
            #---Escribir registro de Asitencia-----
            vals = {}
            seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Attendance'), ])[0]
            summary = 'Inasistencia.'
            
            vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
            vals['collaborator_id'] = inasistente
            vals['type'] = 'absence'
            vals['event_id'] = event_id
            vals['date'] = time.strftime("%Y-%m-%d %H:%M:%S")
            vals['summary'] = summary
            attendance_id = super(osv.osv, attendance_obj).create(cr, uid, vals)
            
            collaborator = collaborator_obj.read(cr, uid, inasistente, ['points'])
            current_points = str(collaborator['points'])
            
            nombre_del_evento = unicode(event['service_id'][1])
            time_start = self.pool.get('kemas.service').read(cr, uid, event['service_id'][0], ['time_start'])['time_start']
            time_start = kemas_extras.convert_float_to_hour_format(time_start)
            description = "Inasistencia al Servicio: '%s' del %s, programado para las %s." % (nombre_del_evento, kemas_extras.convert_date_format_long_str(event['date_start']), time_start)
            new_points = int(current_points) - int(event['not_attend_points'])
            change_points = str(event['not_attend_points'])
            
            #---Escribir puntaje-----
            super(osv.osv, collaborator_obj).write(cr, uid, [inasistente], {
                                'points':int(new_points)
                                })
            #------------------------
            history_summary = '-' + str(change_points) + " Puntos. Antes " + str(current_points) + " ahora " + str(new_points) + " Puntos."
            history_points_obj.create(cr, uid, {
                'date': str(time.strftime("%Y-%m-%d %H:%M:%S")),
                'event_id': event_id,
                'attendance_id': attendance_id,
                'collaborator_id': inasistente,
                'type': 'decrease',
                'description': description,
                'summary': history_summary,
                'points': abs(int(change_points)) * -1,
                })
            #---Agregar un colaborador a la lista de notificationes (Inasistente)
            collaborator = {
                            'id': inasistente,
                            'type':'absence'
                            }
            noticaciones['collaborators'].append(collaborator)
            cr.commit()
        cr.commit()
        self.write_log_closed(cr, uid, event_id, event['message_follower_ids'])
        send_notifications(self)
            
    def cancel_event(self, cr, uid, ids, context={}): 
        event = self.read(cr, uid, ids[0], ['place_id', 'message_follower_ids'])
        service_obj = self.pool.get('kemas.service')
        service_id = self.read(cr, uid, ids[0], ['service_id'])['service_id'][0]
        service = service_obj.read(cr, uid, service_id, [])
        date_start = self.read(cr, uid, ids[0], ['date_start'])['date_start'] 
        
        vals = {
                'state' : 'canceled',
                'color' : 2,
                'date_cancel' : str(time.strftime("%Y-%m-%d %H:%M:%S")),
                #--Summary----------------------------------------------
                'rm_service': service['name'],
                'rm_place': event['place_id'][1],
                'rm_date': date_start,
                'rm_time_start': service['time_start'],
                'rm_time_end': service['time_end'],
                'rm_time_entry': service['time_entry'],
                'rm_time_register': service['time_register'],
                'rm_time_limit': service['time_limit'],
                }
        stage_obj = self.pool.get('kemas.event.stage')
        stage_ids = stage_obj.search(cr, uid, [('sequence', '=', 4)])
        if stage_ids:
            vals['stage_id'] = stage_ids[0]
            
        super(osv.osv, self).write(cr, uid, ids, vals)
        self.write_log_canceled(cr, uid, ids[0], event['message_follower_ids'])
    
    def write_log_delete_replace(self, cr, uid, event_id, collaborator_id, replaced_id, replace_id):
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
        ''' % (_('Reemplazo de Colaboradores'), str(replace_id), _('NULLED'), _('Reemplazo'), collaborator, _('by'), replaced)
        replaced_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, replaced_id)
        collaborator_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, collaborator_id)
        return self.write_log_update(cr, uid, event_id, body, [replaced_id, collaborator_id])
    
    def write_log_replace(self, cr, uid, event_id, collaborator_id, replaced_id, replace_id):
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
        ''' % (_('Reemplazo de Colaboradores'), str(replace_id), _('Reemplazo'), collaborator, _('by'), replaced)
        replaced_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, replaced_id)
        collaborator_id = self.pool.get('kemas.collaborator').get_partner_id(cr, uid, collaborator_id)
        return self.write_log_update(cr, uid, event_id, body, [replaced_id, collaborator_id])
    
    def write_log_create(self, cr, uid, event_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                <b>CREACIÓN</b> del Evento
            </span>
        </div>
        '''
        # Borrar los logs que creados por defecto
        self.pool.get('mail.message').unlink(cr, SUPERUSER_ID, self.pool.get('mail.message').search(cr, uid, [('res_id', '=', event_id)]))
        return self.write_log_update(cr, uid, event_id, body, notify_partner_ids)
    
    def write_log_draft(self, cr, uid, event_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Evento Pausado'), _('Estado'), ('En Curso'), _('Borrador'))
        return self.write_log_update(cr, uid, event_id, body, notify_partner_ids)
    
    def write_log_canceled(self, cr, uid, event_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Este evento fue Cancelado'), _('Estado'), ('En Curso'), _('Cancelado'))
        return self.write_log_update(cr, uid, event_id, body, notify_partner_ids)
    
    def write_log_closed(self, cr, uid, event_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Evento Finalizado'), _('Estado'), ('En Curso'), _('Cerrado'))
        return self.write_log_update(cr, uid, event_id, body, notify_partner_ids)
    
    def write_log_on_going(self, cr, uid, event_id, notify_partner_ids=[]):
        body = u'''
        <div>
            <span>
                %s
            </span>
            <div>     • <b>%s</b>: %s → %s</div>
        </div>
        ''' % (_('Evento en Curso'), _('Estado'), ('Borrador'), _('En Curso'))
        return self.write_log_update(cr, uid, event_id, body, notify_partner_ids)
    
    def write_log_update(self, cr, uid, event_id, body, notify_partner_ids=[]):
        # --Escribir un mensaje con un registro de que se paso Estado en Curso
        user_obj = self.pool.get('res.users')
        message_obj = self.pool.get('mail.message')
        
        event_name = self.name_get(cr, uid, [event_id])[0][1]
        partner_id = user_obj.read(cr, uid, uid, ['partner_id'])['partner_id'][0]
        vals_message = {
                        'body' : body,
                        'model' : 'kemas.event',
                        'record_name' : event_name,
                        'res_id' : event_id,
                        'partner_id' : partner_id,
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
        
    def on_going(self, cr, uid, ids, context={}):
        if type(ids).__name__ in ['int', 'long']:
            ids = list(ids)
            
        records = self.read(cr, uid, ids, ['event_collaborator_line_ids', 'members', 'message_follower_ids', 'code'])
        for record in records:  
            if record['event_collaborator_line_ids']:
                user_obj = self.pool.get('res.users')
                members = user_obj.read(cr, uid, record['members'] + [uid])
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
                super(osv.osv, self).write(cr, uid, ids, vals)
                message_follower_ids = self.read(cr, uid, ids[0], ['message_follower_ids'])['message_follower_ids']
                self.write_log_on_going(cr, uid, ids[0], message_follower_ids)
            else:
                raise osv.except_osv(_('Error!'), _('First add the collaborators assigned to this event.'))
        
    def draft(self, cr, uid, ids, context={}):
        if super(osv.osv, self).read(cr, uid, ids[0], ['sending_emails'])['sending_emails']:
            raise osv.except_osv(_('Error!'), _('You can not make changes to this event as they send notification e-mails.'))
        vals = {}
        vals['state'] = 'draft'
        vals['color'] = 7
        stage_obj = self.pool.get('kemas.event.stage')
        stage_ids = stage_obj.search(cr, uid, [('sequence', '=', 1)])
        if stage_ids:
            vals['stage_id'] = stage_ids[0]
        super(osv.osv, self).write(cr, uid, ids, vals)
        self.write_log_draft(cr, uid, ids[0])
        
    def get_percentage(self, cr, uid, ids, name, arg, context={}):
        def get_percent_progress_event(event_id):
            service_obj = self.pool.get('kemas.service')
            #-----------------------------------------------------------------------------------------------------
            event = self.read(cr, uid, event_id, ['service_id', 'state', 'date_start'])
            service = service_obj.read(cr, uid, event['service_id'][0], ['time_entry', 'time_start', 'time_end'])
            fecha_evento = datetime.datetime.strptime(event['date_start'], '%Y-%m-%d %H:%M:%S')
            tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            # if event['state']=='on_going' and fecha_evento.date().__str__() <= kemas_extras.convert_to_tz(datetime.datetime.now().__str__(),tz,res=1):
            if event['state'] == 'on_going' and fecha_evento.date().__str__() <= datetime.datetime.now().__str__():
                try:
                    total_minutes = service['time_end'] - service['time_start']
                    now_UTC = kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), tz)
                    now_minutes = kemas_extras.convert_hour_format_to_float(now_UTC[-8:])
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
            result[record['id']] = kemas_extras.convert_float_to_hour_format(record['time_start'])
        return result
    
    def _get_time_end_str(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['time_end'])
        for record in records:
            result[record['id']] = kemas_extras.convert_float_to_hour_format(record['time_end'])
        return result
    
    def _get_event_date_str(self, cr, uid, ids, name, arg, context={}): 
        result = {}
        records = super(osv.osv, self).read(cr, uid, ids, ['time_start', 'time_end', 'date_start'])
        for record in records:
            time_start = kemas_extras.convert_float_to_hour_format(record['time_start'])
            time_end = kemas_extras.convert_float_to_hour_format(record['time_end'])
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
            date_start = kemas_extras.convert_to_tz(date_start, self.pool.get('kemas.func').get_tz_by_uid(cr, uid))
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
        'stage_id': fields.many2one('kemas.event.stage', 'Stage'),
        'photo_place': fields.related('place_id', 'photo', type='binary', store=True, string='photo'),
        'members': fields.many2many('res.users', 'event_user_rel', 'event_id', 'uid', 'Event Members', help=""),
        # Campos para cuando un evento finalice alamacer los datos que tenia el servicio en ese entoces
        'time_start_str': fields.function(_get_time_start_str, type='char', string='Time Start'),
        'time_end_str': fields.function(_get_time_end_str, type='char', string='Time end'),
        'event_date_str': fields.function(_get_event_date_str, type='char', string='Event date'),
        'event_day': fields.function(_event_day, type='char', string='Dia del evento'),
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
        event = self.read(cr, uid, ids[0], ['team_id', 'line_ids', 'min_points'])
        collaborator_obj = self.pool.get('kemas.collaborator')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        line_ids = line_obj.search(cr, uid, [('event_id', '=', ids[0])])
        line_obj.unlink(cr, uid, line_ids)
        args = []
        args.append(('type', '=', 'Collaborator'))
        args.append(('points', '>', int(event['min_points'])))
            
        if event['team_id']:
            args.append(('team_id', '=', event['team_id'][0]))
        
        collaborator_ids = collaborator_obj.search(cr, uid, args, context=context)
        for collaborator_id in collaborator_ids:
            vals = {
                    'collaborator_id': collaborator_id,
                    'event_id':ids[0]
                    }
            line_obj.create(cr, uid, vals) 
        self.write(cr, uid, ids, {'collaborators_loaded':True}, context)
        line_ids = line_obj.search(cr, uid, [('event_id', '=', ids[0])])
        collaborator_ids = line_obj.read(cr, uid, line_ids, ['collaborator_id'])
        self.write(cr, uid, ids, {'line_ids':collaborator_ids}, context)       
    
    _defaults = {
        'state':'creating',
        'attend_on_time_points':get_default_attend_on_time_points,
        'late_points':get_default_late_points,
        'not_attend_points':get_default_not_attend_points,
        'progress':200,
        
        'priority': '2',
        'stage_id': 1,
        'color':6,
        'collaborators_loaded': True,
        'min_points':1,
        }
    def validate_date(self, cr, uid, ids):
        event = self.read(cr, uid, ids[0], [])
        event_ids = self.search(cr, uid, [('date_start', '<=', event['date_start']), ('date_stop', '>=', event['date_start']), ('state', 'in', ['on_going'])])
        if event_ids and event_ids != ids:
            raise osv.except_osv(_('Error!'), _('This event is crossed with another.'))
        
        event_ids = self.search(cr, uid, [('date_start', '<=', event['date_stop']), ('date_stop', '>=', event['date_stop']), ('state', 'in', ['on_going'])])
        if event_ids and event_ids != ids:
            raise osv.except_osv(_('Error!'), _('This event is crossed with another.'))
        # tz = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
        # if kemas_extras.convert_to_tz(event['date_start'],tz) <= kemas_extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"),tz)[:10] + ' 00:00:00': 
        #    raise osv.except_osv(_('Error!'), _('Unable to create an event in a past date.')) 
        
        return True
    _constraints = [
        (validate_date, 'inconsistent data.', ['date_start'])
        ] 
    
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
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context={}, orderby=False):
        res_ids = self.search(cr, uid, domain, context=context)
        result = super(kemas_attendance, self).read_group(cr, uid, domain + [('id', 'in', res_ids)], fields, groupby, offset, limit, context, orderby)
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
    
    def register_attendance(self, cr, uid, username, password, context={}):
        '''
        r_1    Error en logeo
        r_2    Logueo correcto pero este Usuario no pertenece a un Colaborador
        r_3    El colaborador no esta asignado para este evento
        r_4    No hay eventos para registrar la asistencia
        '''
        collaborator_obj = self.pool.get('kemas.collaborator')
        #--------------------------------------------------------------------------------------
        sql = """
                select id,login, password from res_users
                where login = '%s'
              """ % (username)
        cr.execute(sql)
        result_query = cr.fetchall()
        if result_query:
            user = {
                    'id' : result_query[0][0],
                    'login' : result_query[0][1],
                    'password' : result_query[0][2],
                    }
            if password == user['password']:
                collaborator_ids = super(kemas_collaborator, collaborator_obj).search(cr, uid, [('user_id', '=', user['id']), ('state', '=', 'Active'), ('type', '=', 'Collaborator'), ])
                if collaborator_ids:
                    vals = {'collaborator_id': collaborator_ids[0]}
                    res = self.create(cr, uid, vals, context)
                    if res == 'no event':
                        _logger.error("'%s' no has events for regsiter attedance. %s" % (username, "REGISTER ATTENDANCE"))
                        return 'r_4'
                    elif res == 'no envolved':
                        _logger.error("'%s' Username not envolved in this event. %s" % (username, "REGISTER ATTENDANCE"))
                        return 'r_3'
                    elif res == 'already register':
                        _logger.error("'%s' Username already register. %s" % (username, "REGISTER ATTENDANCE"))
                        return 'r_5'
                    elif res == 'already checkout':
                        _logger.error("'%s' Username already checkout. %s" % (username, "REGISTER ATTENDANCE"))
                        return 'r_6'
                    else:
                        _logger.info("Register attendance '%s' OK. %s" % (username, "REGISTER ATTENDANCE"))
                        return res
                else:
                    return 'r_2'
            else:
                _logger.warning("'%s' Incorrect Password. %s" % (username, "REGISTER ATTENDANCE"))
                return 'r_1'
        else:
            _logger.warning("'%s' Username don't exist. %s" % (username, "REGISTER ATTENDANCE"))
            return 'r_1'
    
    def create(self, cr, uid, vals, context={}):
        event_obj = self.pool.get('kemas.event')
        event_collaborator_line_obj = self.pool.get('kemas.event.collaborator.line')

        res_current_event = event_obj.get_current_event(cr, uid, True)
        #---No hay eventos para registrar la asistencia---------------------------------------------
        if res_current_event == None: return 'no event'
        #-------------------------------------------------------------------------------------------
        atributes_read = ['current_event_id', 'service_id', 'date_start', 'attend_on_time_points', 'attend_on_time_points', 'late_points']
        event = event_obj.read(cr, uid, res_current_event['current_event_id'], atributes_read)
        kemas_event_collaborator_line_obj = self.pool.get('kemas.event.collaborator.line')
        event['event_collaborator_line_ids'] = super(kemas_event_collaborator_line, kemas_event_collaborator_line_obj).search(cr, uid, [('event_id', '=', res_current_event['current_event_id'])])
        collaborators_involved_ids = event['event_collaborator_line_ids']
        collaborators_involved_list = []

        for collaborators_involved_id in collaborators_involved_ids:
            collaborator_id = event_collaborator_line_obj.read(cr, uid, collaborators_involved_id, ['collaborator_id'])['collaborator_id'][0]
            collaborators_involved_list.append(collaborator_id)
        
        #---Este colaborador ya registro asistencia
        checkin_id = False
        search_args = [('collaborator_id', '=', vals['collaborator_id']), ('event_id', '=', res_current_event['current_event_id']), ('register_type', '=', 'checkin')]
        attendance_ids = super(osv.osv, self).search(cr, uid, search_args)
        if attendance_ids:
            preferences = self.pool.get('kemas.config').read(cr, uid, self.pool.get('kemas.config').get_correct_config(cr, uid), ['allow_checkout_registers'])
            if preferences['allow_checkout_registers']:
                last_register = self.read(cr, uid, attendance_ids[0], ['checkout_id'])
                if last_register['checkout_id']:
                    return 'already checkout'
                else:
                    checkin_id = attendance_ids[0]
            else:
                return 'already register'
        
        #---El Colaborador ho esta entre los colaboradores desginados para este evento--------------   
        if not vals['collaborator_id'] in collaborators_involved_list: return 'no envolved'
        #-------------------------------------------------------------------------------------------
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name', '=', 'Kemas Attendance'), ])[0]
        vals['code'] = str(self.pool.get('ir.sequence').get_id(cr, uid, seq_id))
        vals['count'] = 1
        vals['user_id'] = uid
        vals['date'] = time.strftime("%Y-%m-%d %H:%M:%S")
        vals['event_id'] = res_current_event['current_event_id']
        
        if checkin_id:
            vals['checkin_id'] = checkin_id
            vals['register_type'] = 'checkout'
        else:
            vals['register_type'] = 'checkin'
        
        #---------Verificar tipo de Asistencia------------------------------------------------------
        time_entry = res_current_event['time_entry']
        now = res_current_event['now']
        time_register = res_current_event['time_register']
        time_limit = res_current_event['time_limit']
        
        type = 'just_time'
        summary = 'Asistencia Puntual.'
        if (time_entry + time_register) < now:
            type = 'late'
            minutos_tarde = now - (time_entry + time_register)
            tiempo_de_atraso = kemas_extras.convert_minutes_to_hour_format(minutos_tarde)
            summary = "Asistencia Inpuntual, %s minutos tarde." % (tiempo_de_atraso)
        
        vals['type'] = type
        vals['summary'] = summary
        
        #----Escribir el historial de puntos-----------------------------------------------------
        collaborator_obj = self.pool.get('kemas.collaborator')
        collaborator = collaborator_obj.read(cr, uid, vals['collaborator_id'], ['points'])
        history_points_obj = self.pool.get('kemas.history.points')
        current_points = str(collaborator['points'])
        history_type = 'increase'
        operator = '+'
        
        nombre_del_evento = unicode(event['service_id'][1])
        time_start = self.pool.get('kemas.service').read(cr, uid, event['service_id'][0], ['time_start'])['time_start']
        time_start = kemas_extras.convert_float_to_hour_format(time_start)
        description = "Asistencia Puntual al Servicio: '%s' del %s, programado para las %s." % (nombre_del_evento, kemas_extras.convert_date_format_long_str(event['date_start']), time_start)
                    
        new_points = int(current_points) + int(event['attend_on_time_points'])
        change_points = abs(int(event['attend_on_time_points']))
        if type != 'just_time':
            history_type = 'decrease'
            operator = '-'
            description = unicode("""Asistencia Inpuntual,%s minutos tarde al Servicio:'%s' del %s.""", 'utf-8') % (tiempo_de_atraso, unicode(event['service_id'][1]), kemas_extras.convert_date_format_long_str(event['date_start']))
            new_points = int(current_points) - int(event['late_points'])
            change_points = abs(int(event['late_points'])) * -1
            
        #---Escribir puntaje-----
        current_level_id = collaborator_obj.get_corresponding_level(cr, uid, int(new_points))
        super(osv.osv, collaborator_obj).write(cr, uid, [vals['collaborator_id']], {
                            'points':int(new_points),
                            'level_id':current_level_id,
                            })
        
        res_id = super(osv.osv, self).create(cr, uid, vals, context)
        #------------------------
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
            range_dates = kemas_extras.get_dates_range_this_month(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = kemas_extras.get_dates_range_this_week(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = kemas_extras.get_dates_range_today(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = kemas_extras.get_dates_range_yesterday(context['tz'])
            args.append(('datetime', '>=', range_dates['date_start']))
            args.append(('datetime', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = kemas_extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('datetime', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = kemas_extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
                        args.append(('datetime', '<=', end))
                        items_to_remove.append(arg)
                except:None
            for item in items_to_remove:
                args.remove(item)
        return super(osv.osv, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def unlink(self, cr, uid, ids, context={}): 
        records = self.read(cr, uid, ids, ['event_collaborator_line_id', 'collaborator_id', 'collaborator_replacement_id', 'event_id'])
        event_obj = self.pool.get('kemas.event')
        line_obj = self.pool.get('kemas.event.collaborator.line')
        attendace_obj = self.pool.get('kemas.attendance')        
        for record in records:
            event = event_obj.read(cr, uid, record['event_id'][0], ['state'])
            if event['state'] not in ['on_going']:                
                raise osv.except_osv(_('Error!'), _('Can not delete a replacement from an event that is not ongoing!!'))
            else:
                args = [('event_id', '=', record['event_id'][0]), ('collaborator_id', '=', record['collaborator_replacement_id'][0])]
                if attendace_obj.search(cr, uid, args):
                    raise osv.except_osv(_('Error!'), _('Can not delete a replacement from a collaborator and attendance record.'))
                collaborator_id = record['collaborator_id'][0]
                replace_id = record['collaborator_replacement_id'][0]
                vals = {
                        'collaborator_id' : collaborator_id
                        }
                
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
                
                line_obj.write(cr, uid, record['event_collaborator_line_id'][0], vals)
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
         vals['datetime'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
        'user_id': fields.many2one('res.users', 'User', help='Person performing the replacement'),
        'datetime': fields.datetime('Date'),
        'description': fields.text('Description'),
        # Campos para buscar entre fechas
        'search_start': fields.date('Desde', help='Buscar desde'),
        'search_end': fields.date('Hasta', help='Buscar hasta'),
        }
# vim:expandtab:smartind:tabstop=4:softtabstop=4:shiftwidth=4:
