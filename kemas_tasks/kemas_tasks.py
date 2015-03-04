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
import random
import time

from openerp.addons.kemas import kemas_extras as extras
from openerp.osv import fields, osv
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class kemas_config(osv.osv):
    _inherit = 'kemas.config'
    _columns = {
        'day_to_suspension_task_closed': fields.integer(u'Dia de suspensión', required=False, help=u"Días que se van a suspender a un colaborador por no haber entregado una tarea a tiempo"),
    }
    _defaults = {  
        'day_to_suspension_task_closed': 10 
        }
    
class kemas_suspension(osv.osv):
    _inherit = 'kemas.suspension'
    _columns = {
        'task_assigned_id':fields.many2one('kemas.task.assigned', 'Tarea', help=u'Tarea no cumplida por la cual se realizó la suspensión'),
    }

_TASK_STATE = [('creating', 'Creating'), ('draft', 'New'), ('open', 'In Progress'), ('pending', 'Pending'), ('done', 'Done'), ('cancelled', 'Cancelled')]
class kemas_task_category(osv.osv):
    _name = "kemas.task.category"
    _description = "Category of task, issue, ..."
    _columns = {
        'name': fields.char('Nombre', size=64, required=True, translate=True),
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
    
    _name = 'kemas.task'
    _columns = {
        'name': fields.char('Name', size=200, help="Nombre de la tarea", required=True),
        'points': fields.integer('Points', required=True, help='Points that he will add the collaborator to fulfill the work'),
        'active': fields.boolean('Active', required=False, help='Indicates whether this work is active or not'),
        'description': fields.text('Description', required=True),
        }
    _sql_constraints = [
        ('uname', 'unique (name)', 'This name already exist!'),
        ]
    _defaults = {  
        'points': 1000,
        'active':True
        }

class kemas_task_assigned(osv.osv):
    def close_tasks(self, cr, uid, context={}):
        task_ids = self.search(cr, uid, [('state', 'in', ['draft', 'open', 'pending']), ('date_limit', '!=', False)])
        tasks = self.read(cr, uid, task_ids, ['date_limit'])
        if task_ids:
            print '    >>Cerrando tareas Caducadas'
            context['tz'] = self.pool.get('kemas.func').get_tz_by_uid(cr, uid)
            now = unicode(extras.convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"), context['tz']))
            for task in tasks:
                date_limit = extras.convert_to_UTC_tz(task['date_limit'], context['tz'])
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
                raise osv.except_osv(u'¡Operación no válida!', _('You can not delete this work.'))
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
            collaborator_ids = super(collaborator_obj.__class__, collaborator_obj).search(cr, uid, [('user_id', '=', uid)])
            args.append(('collaborator_id', 'in', collaborator_ids))
        
        # Busqueda de registros en el caso de que en el Contexto llegue algunos de los argumentos: Ayer, Hoy, Esta semana o Este mes
        if context.get('search_this_month', False):
            range_dates = extras.get_dates_range_this_month(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))    
        elif context.get('search_this_week', False):
            range_dates = extras.get_dates_range_this_week(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))
        elif context.get('search_today', False):
            range_dates = extras.get_dates_range_today(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))  
        elif context.get('search_yesterday', False):
            range_dates = extras.get_dates_range_yesterday(context['tz'])
            args.append(('date_created', '>=', range_dates['date_start']))
            args.append(('date_created', '<=', range_dates['date_stop']))  
        
        # Busqueda de registros entre fechas en el Caso que se seleccione "Buscar desde" o "Buscar hasta"
        if context.get('search_start', False) or context.get('search_end', False):
            items_to_remove = []
            for arg in args:
                try:
                    if arg[0] == 'search_start':
                        start = extras.convert_to_UTC_tz(arg[2] + ' 00:00:00', context['tz'])
                        args.append(('date_created', '>=', start))
                        items_to_remove.append(arg)
                    if arg[0] == 'search_end':
                        end = extras.convert_to_UTC_tz(arg[2] + ' 23:59:59', context['tz'])
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
                'active': False
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
                'active': False
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
        for task_assigned in super(osv.osv, self).read(cr, uid, ids, ['state', 'stage_id', 'active', 'message_follower_ids']):
            if not task_assigned['active']:
                raise osv.except_osv(u'¡Operación no válida!', _('No se puede modificar una tarea Cerrada o Cancelada.'))
            
            if vals.get('stage_id'):
                stage = self.pool.get('kemas.task.type').read(cr, uid, vals['stage_id'], ['state', 'name'])
                state = stage['state']
                if state in ['done', 'cancelled'] and stage['name'] != 'Completed':
                    raise osv.except_osv(u'¡Operación no válida!', _('Para cancelar o Cerrar una Tarea hay que dar click en el boton respectivo.'))
                
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
        return super(kemas_task_assigned, self).create(cr, uid, vals, context)
    
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
        'notes': fields.text('Notes'),
        'user_id': fields.many2one('res.users', 'Assigned to', track_visibility='onchange'),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'active': fields.boolean('Is active', required=False),
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
            raise osv.except_osv(u'¡Operación no válida!', _("You've entered this task and has not yet been confirmed."))
        
    _constraints = [(_validate, 'Error: Invalid Message', ['field_name']), ]
    
    _defaults = {
        'stage_id': _get_default_stage_id,
        'state': 'creating',
        'priority': '2',
        'sequence': 10,
        'active': True,
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
# vim:expandtab:smartind:tabstop=4:softtabstop=4:shiftwidth=4:
