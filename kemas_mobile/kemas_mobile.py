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

from openerp.addons.kemas import kemas_extras as extras
from openerp.osv import fields, osv


_logger = logging.getLogger(__name__)

class kemas_config(osv.osv): 
    _columns = {
        'mobile_background': fields.binary('Fondo', help='Es la imagen que estla como fndo en el menu de Colaboradores.'),
        'mobile_background_text_color':fields.char('Color de la letra', size=64, help='Color del texto del Menu.'),
        }
    
    _inherit = 'kemas.config' 
    
class kemas_event(osv.osv): 
    def get_count_events_to_mobile_app(self, cr, uid, params, context={}):
        collaborator_id = params['collaborator_id']
        state = " and E.state in ('on_going', 'closed')"
        if params.get("state", False):
            state = "and E.state = '" + str(params['state']) + "'"
        sql = """
            SELECT count(E.id) FROM kemas_event as E
            JOIN kemas_service as S on (S.id = E.service_id)
            WHERE E.id in (
                select event_id from kemas_event_collaborator_line
                where collaborator_id = %d %s
            )
            """ % (collaborator_id, state)
        cr.execute(sql)
        return cr.fetchall()[0][0]
    
    def get_events_to_mobile_app(self, cr, uid, params, context={}):
        offset = params.get('offset', 0)
        limit = params.get('limit', 10)
        order = params.get('order', 'E.date_start DESC, E.id DESC')
        limit_avatars = params.get('limit_avatars', 3)
        
        collaborator_id = params['collaborator_id']
        state = " and E.state in ('on_going', 'closed')"
        if params.get("state", False):
            state = "and E.state = '" + str(params['state']) + "'"
            
        sql = """
            SELECT E.id, S.name as service, E.state, E.date_start, E.date_stop FROM kemas_event as E
            JOIN kemas_service as S on (S.id = E.service_id)
            WHERE E.id in (
                select event_id from kemas_event_collaborator_line
                where collaborator_id = %d %s
            )
            ORDER BY %s
            OFFSET %d LIMIT %d
            """ % (collaborator_id, state, order, offset, limit)
        cr.execute(sql)
        
        result = []
        
        for event in cr.fetchall():
            sql = """
                select count(id) from kemas_event_collaborator_line
                where event_id = %d
                """ % (event[0])
            cr.execute(sql)
            num_collaborators = cr.fetchall()[0][0]
            
            sql = """
                select C.photo_very_small from kemas_event_collaborator_line as CL
                join kemas_collaborator as C on (C.id = CL.collaborator_id)
                where event_id = %d
                limit %d
            """ % (event[0], limit_avatars)
            cr.execute(sql)
            collaborators = []
            for collaborator in cr.dictfetchall():
                collaborators.append(unicode(collaborator['photo_very_small']))
            event = list(event) + [num_collaborators] + [collaborators]
            result.append(event)
        return result

    _inherit = 'kemas.event'
    
class kemas_history_points(osv.osv): 
    def get_count_points_to_mobile_app(self, cr, uid, search_args, context={}):
        collaborator_id = search_args['collaborator_id']
        points = ""
        if search_args.get("type", False):
            points = "and H.type = '" + str(search_args['type']) + "'"
            
        sql = """
            SELECT count(H.id) FROM kemas_history_points as H
            WHERE H.collaborator_id = %d %s
            """ % (collaborator_id, points)
        cr.execute(sql)
        return cr.fetchall()[0][0]
    
    def get_points_to_mobile_app(self, cr, uid, search_args, offset, limit, context={}):
        collaborator_id = search_args['collaborator_id']
        points = ""
        if search_args.get("type", False):
            points = "and H.type = '" + str(search_args['type']) + "'"
            
        sql = """
            SELECT H.id, H.points, H.type, H.date FROM kemas_history_points as H
            WHERE H.collaborator_id = %d %s
            ORDER BY H.date DESC, H.id DESC
            OFFSET %d LIMIT %d
            """ % (collaborator_id, points, offset, limit)
        cr.execute(sql)
        return cr.fetchall()

    _inherit = 'kemas.history.points'
    
class kemas_attendance(osv.osv): 
    def get_count_attendances_to_mobile_app(self, cr, uid, search_args, context={}):
        collaborator_id = search_args['collaborator_id']
        attendances = ""
        if search_args.get("type", False):
            attendances = "and A.type = '" + str(search_args['type']) + "'"
        
        sql = """
            SELECT count(A.id) FROM kemas_attendance as A
            WHERE A.register_type = 'checkin' and A.collaborator_id = %d %s
            """ % (collaborator_id, attendances)
        cr.execute(sql)
        return cr.fetchall()[0][0]
    
    def get_attendances_to_mobile_app(self, cr, uid, search_args, offset, limit, context={}):
        collaborator_id = search_args['collaborator_id']
        attendances = ""
        if search_args.get("type", False):
            attendances = "and A.type = '" + str(search_args['type']) + "'"
        sql = """
            SELECT A.id, S.name, A.type, A.date, A.checkout_id FROM kemas_attendance as A
            JOIN kemas_event as E ON (E.id = A.event_id)
            JOIN kemas_service as S ON (S.id = E.service_id)
            WHERE A.register_type = 'checkin' and A.collaborator_id = %d %s
            ORDER BY A.date DESC, A.id DESC
            OFFSET %d LIMIT %d
            """ % (collaborator_id, attendances, offset, limit)
        cr.execute(sql)
        
        result = [] 
        for record in cr.fetchall(): 
            checkout = False
            record = list(record)
            if not record[4] is None:
                record = list(record)
                sql = """
                    SELECT A.date FROM kemas_attendance as A
                    where A.id = %d
                    """ % record[4]
                cr.execute(sql)
                checkout = cr.fetchall()[0][0]
            record[4] = checkout
            result.append(record)
                
        return result

    _inherit = 'kemas.attendance' 

class kemas_collaborator(osv.osv):
    def get_collaborator_event(self, cr, uid, collaborator_id, context={}):
        sql = """
            SELECT P.name, C.photo_very_small as photo_small FROM kemas_collaborator as C
            JOIN res_users AS U ON (U.id = C.user_id)
            JOIN res_partner AS P ON (P.id = U.partner_id)
            WHERE C.id = %d
            """ % collaborator_id
        cr.execute(sql)
        collaborator = cr.dictfetchall()[0]
        collaborator['photo_small'] = unicode(collaborator['photo_small'])
        return collaborator
        
    def get_collaborator(self, cr, uid, collaborator_id, context={}):
        def build_image(image):
            result = ''
            if not image is None and type(image).__name__ == 'buffer':
                try:
                    result = unicode(image)
                except: None
            return result
                
        sql = """
            SELECT 
                Cl.id, Cl.personal_id, CL.code,CL.name,Cl.nick_name,P.birthdate as birth,Cl.marital_status,P.street as address,
                P.mobile,P.phone,P.phone,P.email,P.email,
                Cl.join_date,CL.points,LV.name as level, CL.team_id, Cl.gender
            FROM kemas_collaborator as CL
            JOIN res_users as U on (Cl.user_id = U.id)
            JOIN res_partner as P on (U.partner_id = P.id)
            JOIN kemas_level as LV on(CL.level_id = LV.id)
            WHERE Cl.id = %d
            """ % collaborator_id
        cr.execute(sql)
        collaborators = cr.dictfetchall()
        if collaborators:
            collaborator = collaborators[0]
            # Obtener el listado de Areas de Colaboracion
            sql = """
                SELECT id,name FROM kemas_area as A
                JOIN kemas_collaborator_area_rel as REL ON (REL.area_id = A.id)
                WHERE REL.collaborator_id = %s
                """ % str(collaborator['id'])
            cr.execute(sql)
            collaborator['areas'] = cr.dictfetchall()
            
            # Obtener el equipo
            if collaborator['team_id']:
                sql = """
                    SELECT id,name FROM kemas_team
                    WHERE id = %s
                    """ % str(collaborator['team_id'])
                cr.execute(sql)
                collaborator['team'] = cr.dictfetchall()[0]
            else:
                collaborator['team'] = ''
            collaborator.pop('team_id')
            
            # Poner en español el estado civil
            lgender = {'Male': 'o', 'Female': 'a'}
            if collaborator['marital_status'] == 'single':
                collaborator['marital_status'] = 'Soleter' + lgender[collaborator['gender']]
            else:
                collaborator['marital_status'] = 'Casad' + lgender[collaborator['gender']]
                    
            # Calcular la edad
            collaborator['age'] = extras.calcular_edad(collaborator['birth'])
            collaborator['birth'] = extras.convert_date_format_short_str(collaborator['birth'])
            
            # Calcular edad en el ministerio
            collaborator['age_in_ministry'] = extras.calcular_edad(collaborator['join_date'], 4)
            collaborator['join_date'] = extras.convert_date_format_short_str(collaborator['join_date'])
            
            
            for field in collaborator:
                if collaborator[field] is None:
                    collaborator[field] = ' -- '
                    
            return collaborator
        else:
            return False
        
    def get_info_for_navigation(self, cr, uid, collaborator_id, context={}):
        def build_image(image):
            result = ''
            if not image is None and type(image).__name__ == 'buffer':
                try:
                    result = unicode(image)
                except: None
            return result
        
        result = {}
        sql = """
            SELECT P.name,CL.photo_medium as image, CL.team_id
            FROM kemas_collaborator as CL
            JOIN res_users as U on (Cl.user_id = U.id)
            JOIN res_partner as P on (U.partner_id = P.id)
            WHERE Cl.id = %d
            """ % collaborator_id
        cr.execute(sql)
        collaborators = cr.dictfetchall()
        if collaborators:
            result = {}
            collaborator = collaborators[0]
            collaborator['image'] = build_image(collaborator['image'])
            # Obtener el equipo
            if collaborator['team_id']:
                sql = """
                    SELECT name FROM kemas_team
                    WHERE id = %s
                    """ % str(collaborator['team_id'])
                cr.execute(sql)
                collaborator['team'] = cr.dictfetchall()[0]['name']
            else:
                collaborator['team'] = ''
            collaborator.pop('team_id')
            result.update(collaborator)
            
            sql = """
                select mobile_background,mobile_background_text_color from kemas_config
                """
            cr.execute(sql)
            config = cr.dictfetchall()[0]
            config['mobile_background'] = build_image(config['mobile_background'])
            result.update(config)
        return result
        
    _inherit = 'kemas.collaborator' 
    
# vim:expandtab:smartind:tabstop=4:softtabstop=4:shiftwidth=4:
