# -*- coding: utf-8 -*-
##############################################################################
# Verticalización de Sistema de Gestión Académica
# OpenERP Alliance Ecuador
# Multics Cia. Ltda. - InfoStudio Cia. Ltda.
# 2011-2012
# ver 1.2 Con personalización para instituciones de Educación Superior.
#
##############################################################################
from osv import fields, osv
from tools.translate import _

class kemas_message_wizard(osv.osv_memory):
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context={}, toolbar=False, submenu=False):
        message = context.get('message','')
        result = {}
        ok_str = self.pool.get('kemas.func').get_translate(cr, uid, _('Ok'))[0]
        xml = """
                <form string="" version="7.0">
                    <div align="center">
                        <img src="/web/static/src/img/icons/gtk-info.png"/> 
                        <b>
                            <label string="%s"/>
                        </b>
                    </div>
                    <footer>
                        <button string="%s" class="oe_link" special="cancel"/>
                    </footer> 
                </form>
                """%(message,ok_str)
        result['fields'] = self.fields_get(cr, uid, None, context)
        result['arch'] = xml
        return result
        

    _name = 'kemas.message.wizard'
    _columns = {
        'name' : fields.text('Name', readonly=True),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
