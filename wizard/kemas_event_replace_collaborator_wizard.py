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
import time
from osv import fields, osv
from lxml import etree
from tools.translate import _
import addons
import datetime
from datetime import datetime
import time
import kemas
from kemas import kemas_extras
import copy

class kemas_event_replace_collaborator_wizard(osv.osv_memory):
    def load_collaborators(self, cr, uid, ids, context={}):
        line_obj = self.pool.get('kemas.event_replace_collaborator.wizard.line')
        line_obj.unlink(cr,uid,line_obj.search(cr,uid,[('wizard_id','in',ids)]))
        event_obj = self.pool.get('kemas.event')
        config_obj = self.pool.get('kemas.config')
        collaborator_obj = self.pool.get('kemas.collaborator')
        replacement_obj = self.pool.get('kemas.event.replacement')
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        wizard = self.read(cr, uid, ids[0], ['event_id'])
        event = event_obj.read(cr, uid, wizard['event_id'][0],['event_collaborator_line_ids'])
        lines = event_line_obj.read(cr, uid, event['event_collaborator_line_ids'], ['id','collaborator_id','replacement_id'])
        except_ids = []
        preferences = config_obj.get_correct_config(cr,uid, ['number_replacements'])
        for line in lines:
            except_ids.append(line['collaborator_id'][0])
            if line['replacement_id']:
                replacement = replacement_obj.read(cr,uid,line['replacement_id'][0],['collaborator_replacement_id','description'])
                collaborator_replacement_id = replacement['collaborator_replacement_id'][0]
                except_ids.append(collaborator_replacement_id)
            
        self.write(cr,uid,ids,{'collaborator_ids':str(except_ids)})
        for line in lines:
            replacements = super(kemas.kemas.kemas_collaborator,collaborator_obj).read(cr,uid,line['collaborator_id'][0],['replacements'])['replacements']        
            vals = {
                    'except_ids':except_ids,
                    'wizard_id':ids[0],
                    'replacements' : replacements,
                    'collaborator_id':line['collaborator_id'][0],
                    'event_collaborator_line_id': line['id']
                    }
            if line['replacement_id']:
                replacement = replacement_obj.read(cr,uid,line['replacement_id'][0],['collaborator_replacement_id','collaborator_id','description'])
                vals['replaced'] = True
                vals['collaborator_replacement_id'] = replacement['collaborator_replacement_id'][0]
                vals['collaborator_id'] = replacement['collaborator_id'][0]
                vals['description'] = replacement['description']
            
            #Verificar que el colaborador aun no haya registrado asistencia
            attendace_obj = self.pool.get('kemas.attendance')
            if attendace_obj.search(cr,uid,[('event_id','=',wizard['event_id'][0]),('collaborator_id','=',line['collaborator_id'][0])]):
                vals['replaced'] = True
            
            line_obj.create(cr, uid, vals)
        wizard_title = self.pool.get('kemas.func').get_translate(cr, uid, _('Replace colaborators'))[0]
        return{            
            'context': "{}",
            'res_id' : ids[0],
            'name' : wizard_title,
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'kemas.event_replace_collaborator.wizard', 
            'type': 'ir.actions.act_window', 
            'target':'new',
            }
        
    def save(self, cr, uid, ids, context={}):
        this = self.read(cr, uid, ids[0])
        replaceds = []
        collaborator_replacement_ids = []
        line_obj = self.pool.get('kemas.event_replace_collaborator.wizard.line')
        replacement_obj = self.pool.get('kemas.event.replacement')
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        try:
            collaborator_replacement_ids += eval(this['collaborator_ids'])
        except:None
        for line_id in this['line_ids']:
            line = line_obj.read(cr,uid,line_id,[])
            if line['collaborator_replacement_id'] and line['replaced']==False:
                if line['collaborator_replacement_id'][0] not in collaborator_replacement_ids:
                    collaborator_replacement_ids.append(line['collaborator_replacement_id'][0])
                else:
                    raise osv.except_osv(_('Error!'), _('One of the collaborators replacement is repeated.'))
                #Crear el registro de reemplazo
                collaborator_id = line['collaborator_id'][0]
                replace_id = line['collaborator_replacement_id'][0]
                vals = {
                        'collaborator_id' : collaborator_id,
                        'collaborator_replacement_id' : replace_id,
                        'event_id' : this['event_id'][0],
                        'description' : line['description'],
                        'event_collaborator_line_id' : line['event_collaborator_line_id']
                        }
                replacement_id = replacement_obj.create(cr,uid,vals)
                replaceds.append({'collaborator_id' : collaborator_id,'replace_id' : replace_id, 'record_id' : replacement_id})
                #Cambiar la linea de colaborador en el evento indicando que ya fue reemplazado
                args = [('event_id','=',this['event_id'][0]),('collaborator_id','=',line['collaborator_id'][0])]
                line_ids = event_line_obj.search(cr, uid, args)
                vals = {
                        'replacement_id' : replacement_id,
                        'collaborator_id' : line['collaborator_replacement_id'][0],
                        }
                event_line_obj.write(cr,uid,line_ids,vals)
        self.pool.get('kemas.event').replace_collaborators(cr,uid,this['event_id'][0],replaceds)            
        mensaje = _('The registers was saved correctly.')
        return{            
            'context': "{'message':'"+mensaje+"'}",
            'view_type': 'form', 
            'view_mode': 'form', 
            'res_model': 'kemas.message.wizard', 
            'type': 'ir.actions.act_window', 
            'target':'new',
            }
        
    _name='kemas.event_replace_collaborator.wizard'
    _rec_name = 'event_id'
    _columns={
        'event_id':fields.many2one('kemas.event','Event', required=True,ondelete='cascade', help='Event which will replace collaborators.'),
        'logo': fields.binary('img'),
        'line_ids': fields.one2many('kemas.event_replace_collaborator.wizard.line', 'wizard_id', 'Lines',help=''),
        'collaborator_ids': fields.text('collaborator_id'),
        }
    def _get_logo(self, cr, uid, context=None):
        photo_path = addons.get_module_resource('kemas','images','update.png')
        return open(photo_path, 'rb').read().encode('base64')
    _defaults = {  
        'logo': _get_logo,
        }

class kemas_event_replace_collaborator_wizard_line(osv.osv_memory):
    _name='kemas.event_replace_collaborator.wizard.line'
    _columns={
        'wizard_id':fields.many2one('kemas.event_replace_collaborator.wizard','Wizard parent',ondelete='cascade', help='Event which will replace collaborators.'),
        'collaborator_id':fields.many2one('kemas.collaborator','Collaborator',ondelete='cascade', help=''),
        'collaborator_replacement_id':fields.many2one('kemas.collaborator','Replacement',ondelete='cascade', help='Collaborator replacement'),
        'replacements': fields.integer('Replacements',help='Number of replacements available'),
        'except_ids': fields.text('except_ids'),
        'replaced':fields.boolean('Replaced'),
        'description': fields.text('Description'),
        'event_collaborator_line_id': fields.integer('event_collaborator_line_id')
        }   
    _defaults = {  
        'replaced': False, 
        } 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

