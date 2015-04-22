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

from openerp.osv import fields, osv
from lxml import etree
from openerp.tools.translate import _
from openerp.addons.kemas import kemas_extras
#from kemas import kemas_extras

class kemas_register_attendance_wizard(osv.osv_memory):
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=True, submenu=False):
        event_obj = self.pool.get('kemas.event')
        service_obj = self.pool.get('kemas.service')
        current_event_res = event_obj.get_current_event(cr, uid, True)
        #-----------------------------------------------------------------------------------------------------------------
        res = super(kemas_register_attendance_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=False, submenu=False)
        xml='''<form string="Register Attedance" version="7.0">'''
        if current_event_res:
            current_event_id = current_event_res['current_event_id']
            current_event = event_obj.read(cr, uid, current_event_id,[])
            service = service_obj.read(cr, uid, current_event['service_id'][0],[])
            time_start = str(kemas_extras.convert_float_to_hour_format(service['time_start']))
            time_end = str(kemas_extras.convert_float_to_hour_format(service['time_end']))
            
            or_str = self.pool.get('kemas.func').get_translate(cr, uid, _('or'))[0]
            cancel_str = self.pool.get('kemas.func').get_translate(cr, uid, _('Cancel'))[0]
            buttons = '''
            <button string="%s" name="save" type="object" class="oe_highlight"/>
            %s
            <button string="%s" class="oe_link" special="cancel"/>
            '''%(_('Register Attendance'),or_str,cancel_str)
            
            xml+='''
                    <div align="center">
                        <separator string="%s" colspan="4" />
                    </div>
                    <br/>
            '''%(unicode(service['name']).upper() + ' | ' + time_start + ' - ' + time_end + ' | '+ str(current_event_res['minutes_remaining']) + ' ' + _('Minutes remaining for record attendance') )
            xml+='''<group colspan="4" col="4">
                        <field name="username" colspan="2"/>
                        <group colspan="2"/>
                        <field name="password" colspan="2" password="True"/>
                        <group colspan="2"/>
                    </group>
                    '''
            xml+='''<separator string="" colspan="4"/>
                    <footer>
                       %s
                    </footer>'''%(buttons)
        else:
            ok_str = self.pool.get('kemas.func').get_translate(cr, uid, _('Ok'))[0]
            xml+='''<div align="center">
                        <img src="/web/static/src/img/icons/gtk-info.png"/> 
                        <b>  <label string="%s"/></b>
                    </div>
                    <footer>
                       <button string="%s" class="oe_link" special="cancel"/>
                    </footer>
                '''%(_("There are no services for record attendance."),ok_str)  
        xml+='''</form>'''
        
        doc = etree.fromstring(xml.encode('utf8'))
        xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
        res['arch'] = xarch
        res['fields'] = xfields
        return res
    
    def save(self,cr,uid,ids,context=None):
        '''
        r_1    Error en logeo
        r_2    Logueo correcto pero este Usuario no pertenece a un Colaborador
        r_3    El colaborador no esta asignado para este evento
        r_4    No hay eventos para registrar la asistencia
        r_5    El usuario ya registro su asistencia
        '''
        wizard = self.read(cr, uid, ids[0],[])
        attendance_obj = self.pool.get('kemas.attendance')
        #--------------------------------------------------------------------------------------
        res = attendance_obj.register_attendance(cr, uid, wizard['username'],  wizard['password'])
        if res == 'r_1':
            raise osv.except_osv(u'¡Operación no válida!', _('Invalid username or password.'))
        elif res == 'r_2':
            raise osv.except_osv(u'¡Operación no válida!', _('This user name does not belong to any collaborator. Contact the administrator'))
        elif res == 'r_3':
            raise osv.except_osv(u'¡Operación no válida!', _("You are not in the list of designated staff for this service."))
        elif res == 'r_4':
            raise osv.except_osv(u'¡Operación no válida!', _('There are no services for record attendance.'))
        elif res == 'r_5':
            raise osv.except_osv(u'¡Operación no válida!', _('This collaborator has registered their attendance at this event!'))
        elif res == 'r_6':
            raise osv.except_osv(u'¡Operación no válida!', _('Este Colaborador ya marco el registro de salida!'))
        else:
            mensaje = 'OK.'
            return{            
                'context': "{'message':'"+mensaje+"'}",
                'view_type': 'form', 
                'view_mode': 'form', 
                'res_model': 'kemas.message.wizard', 
                'type': 'ir.actions.act_window', 
                'target':'new',
                }

    _name='kemas.register.attendance.wizard'
    _columns={
        'username': fields.char('Username',size=255,required=True),
        'password': fields.char('Password',size=255,required=True),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

