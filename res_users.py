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
from compiler.pycodegen import EXCEPT
import base64
import openerp
import tools
import tools7
import math
from dateutil.parser import  *
    
_logger = logging.getLogger(__name__)

class res_users(osv.osv):
    def register_login(self, db_name, user_id, user_agent_env):
        threaded_sending = threading.Thread(target=self._register_login, args=(db_name, user_id, user_agent_env))
        threaded_sending.start()
    
    def _register_login(self, db_name, user_id, user_agent_env):
        db, pool = pooler.get_db_and_pool(db_name)
        cr = db.cursor()
        if user_id:
            collaborator_obj = self.pool.get('kemas.collaborator')
            collaborator_ids = collaborator_obj.search(cr, user_id, [('user_id', '=', user_id)])
            if collaborator_ids:
                vals_login = {
                              'collaborator_id' : collaborator_ids[0],
                              'base_location' : user_agent_env['base_location'],
                              'remote_address' : user_agent_env['REMOTE_ADDR'],
                              }
                self.pool.get('kemas.collaborator.logbook.login').create(cr, 1, vals_login)
        cr.commit()
                
    def authenticate(self, db, login, password, user_agent_env):
        uid = super(res_users, self).authenticate(db, login, password, user_agent_env)
        self.register_login(db, uid, user_agent_env)
        return uid

    _inherit = 'res.users'
    
# vim:expandtab:smartind:tabstop=4:softtabstop=4:shiftwidth=4:
