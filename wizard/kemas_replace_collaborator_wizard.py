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

class kemas_replace_collaborator_wizard(osv.osv_memory):
    def on_change_collaborator_id(self, cr, uid, ids, collaborator_id, context={}):
        collaborator_obj = self.pool.get('kemas.collaborator')
        replacements = collaborator_obj.read(cr,uid,collaborator_id,['replacements'])['replacements']
        if replacements > 0:
            return {'value':{}}
        else:
            msg = _('The selected collaborator already exceeded the limit of replacements available for this month')
            return {'value':{'collaborator_id': False}, 'warning':{'title':'Error', 'message' : msg}}
        
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=True, submenu=False):       
        res = {}
        event_obj = self.pool.get('kemas.event')
        event = event_obj.read(cr,uid,context['active_id'],['state','event_collaborator_line_ids'])
        error = False
        msg_error = ''
        collaborator_ids = self.pool.get('kemas.collaborator').search(cr,uid,[('user_id','=',uid)])
        if collaborator_ids:
            collaborator_id = collaborator_ids[0]
            if event['state'] in ['draft','creating']:
                error = True
                msg_error = _('You can not replace anyone in this event because it is not On Going.')
                msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
            elif event['state'] in ['closed']:
                error = True
                msg_error = _('You can not replace anyone in this event because it was Closed.')
                msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
            elif event['state'] in ['closed']:
                error = True
                msg_error = _('You can not replace anyone in this event because it was Canceled.')
                msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
            else:
                lines = self.pool.get('kemas.event.collaborator.line').read(cr,uid,event['event_collaborator_line_ids'],['collaborator_id','replacement_id'])
                for line in lines:
                    if line['collaborator_id'][0] == collaborator_id:
                        error = True
                        if line['replacement_id']:
                            msg_error = _('You can not replace anyone in this event because you replaced ')
                            msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
                            msg_error = "%s %s"%(msg_error,line['replacement_id'][1])
                        else:
                            msg_error = _('You can not replace anyone in this event because and those Included in this event.')
                            msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
                    elif line['replacement_id']:
                        if line['replacement_id'][0] == collaborator_id:
                            error = True
                            msg_error = _('You can not replace anyone in this event because were replaced by')
                            msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
                            msg_error = "%s %s"%(msg_error,line['collaborator_id'][1])
                        
        else:
            error = True
            msg_error = _('This wizard is only for collaborators.')
            msg_error = self.pool.get('kemas.func').get_translate(cr,uid,msg_error)[0]
                
        if error:
            ok_str = self.pool.get('kemas.func').get_translate(cr, uid, _('Ok'))[0]
            xml='''
            <form string="" version="7.0">
                <div align="center" class="box_warning">
                   <img src="/web/static/src/img/icons/gtk-dialog-warning.png"/>
                   <label string="%s"/>
                </div>
                <footer>
                   <button string="%s" class="oe_link" special="cancel"/>
               </footer>
            </form>
            '''%(msg_error,ok_str)
        else:            
            or_str = self.pool.get('kemas.func').get_translate(cr, uid, _('or'))[0]
            tip = self.pool.get('kemas.func').get_translate(cr,uid,_('Here you can replace one of the collaborators, you can only replace collaborators who have not yet been replaced and do not exceed the limit of replacements this month.'))[0]
            confirm = self.pool.get('kemas.func').get_translate(cr,uid,_('Are you sure to replace this contributor now?'))[0]
            xml='''
            <form string="" version="7.0">
               <div align="center" class="box_tip">
                   <img src="/web/static/src/img/icons/gtk-info.png"/>
                   <i>
                       <label string="%s"/>
                   </i>
               </div>
               <separator string="%s" colspan="20"/>
               <group>
                   <field name="collaborator_id" on_change="on_change_collaborator_id(collaborator_id)" context="{'event_id' : context['event_id'], 'exclude_replaceds' : True, 'show_replacements' : True, 'all_collaborators' : True}" default_focus="1" placeholder="collaborator_to_replace ..." options='{"no_open": True}'/>
                   <field name="description" placeholder="%s"/>
               </group>
              <footer>
                   <button string="%s" name="replace" type="object" class="oe_highlight" confirm="%s"/>
                   <label string="%s"/>
                   <button string="%s" class="oe_link" special="cancel"/>
               </footer>
            </form>
            '''%(tip,_('SELECT COLLABORATOR'),_('Enter the reason for replacement...'),_('Replace'),confirm,or_str,_('Cancel'))
        doc = etree.fromstring(xml.encode('utf8'))
        xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
        res['arch'] = xarch
        res['fields'] = xfields
        return res
    
    def replace(self,cr,uid,ids,context=None):
        this = self.read(cr,uid,ids[0])
        replacement_obj = self.pool.get('kemas.event.replacement')
        event_line_obj = self.pool.get('kemas.event.collaborator.line')
        collaborator_ids = self.pool.get('kemas.collaborator').search(cr,uid,[('user_id','=',uid)])
        collaborator_id = collaborator_ids[0]
        replace_id = this['collaborator_id'][0]
        event_id = context['active_id']
        vals = {
                'collaborator_id' : replace_id,
                'collaborator_replacement_id' : collaborator_id,
                'event_id' : event_id,
                'description' : this['description'],
                }
        replacement_id = replacement_obj.create(cr,uid,vals)
        replaceds = [{'collaborator_id' : replace_id,'replace_id' : collaborator_id, 'record_id' : replacement_id}]
        #Cambiar la linea de colaborador en el evento indicando que ya fue reemplazado
        args = [('event_id','=',event_id),('collaborator_id','=',replace_id)]
        line_ids = event_line_obj.search(cr, uid, args)
        vals = {
                'replacement_id' : replacement_id,
                'collaborator_id' : collaborator_id,
                }
        event_line_obj.write(cr,uid,line_ids,vals)  
        self.pool.get('kemas.event').replace_collaborators(cr,uid,event_id,replaceds)
        return True
          
    _name='kemas.replace.collaborator.wizard'
    _columns={
        'collaborator_id': fields.many2one('kemas.collaborator','Collaborator', context={'all_collaborators' : True},ondelete='cascade', required=True, help='Collaborator to replace'),
        'description': fields.text('Description', required=True),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

