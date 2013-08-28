# -*- coding: utf-8 -*-
##############################################################################
# Verticalización de Sistema de Gestión Académica
# OpenAlliance Ecuador
# Protelcotelsa.
# 2011-2012
# ver 2.0
#
##############################################################################
from mx import DateTime
import unicodedata
import copy
from unicodedata import normalize
from datetime import datetime
from datetime import *
from dateutil import tz
import pytz
from pytz import timezone
import time
import calendar
import re
import threading
import os
import base64

try:
    from reportlab.graphics.barcode import createBarcodeDrawing, \
            getCodes
except :
    print "ERROR IMPORTING REPORT LAB"

def get_dates_range_today(tz):
    fecha_actual = unicode(convert_to_tz(time.strftime("%Y-%m-%d %H:%M:%S"),tz,res=1))
    date_start = convert_to_UTC_tz(fecha_actual + ' 00:00:00',tz)
    date_stop = convert_to_UTC_tz(fecha_actual + ' 23:59:59',tz)  
    return {'date_start' : date_start, 'date_stop' : date_stop}

def get_dates_range_this_week(tz):
    import datetime
    now = datetime.datetime.now()
    day_number = int(now.strftime('%u'))
    date_start = (now - timedelta(days=day_number - 1)).date().__str__()
    date_stop = (now + timedelta(days=7 - day_number)).date().__str__()
    date_start = convert_to_UTC_tz(date_start + ' 00:00:00',tz)
    date_stop = convert_to_UTC_tz(date_stop + ' 23:59:59',tz)
    return {'date_start' : date_start, 'date_stop' : date_stop}

def get_dates_range_this_month(tz):
    import datetime
    now = datetime.datetime.now()
    year = completar_cadena(now.year,4)
    month = completar_cadena(now.month)
    
    days = dias_de_un_mes(now.year,now.month)
    date_start = "%s-%s-01"%(year,month)
    date_stop = "%s-%s-%s"%(year,month,days)
    
    date_start = convert_to_UTC_tz(date_start + ' 00:00:00',tz)
    date_stop = convert_to_UTC_tz(date_stop + ' 23:59:59',tz)  
    return {'date_start' : date_start, 'date_stop' : date_stop}

def validate_mail(email):
    if len(email) > 7:
        if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) != None: 
            return 1
    return 0

#Extraer numero de una cadena
def extraer_numeros(cadena):
    nuevacadena = ''

    for letra in cadena:
        if letra == '1':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '2':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '3':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '4':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '5':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '6':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '7':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '8':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '9':
            nuevacadena = str(nuevacadena) + str(letra)
        if letra == '0':
            nuevacadena = str(nuevacadena) + str(letra)
    return nuevacadena

#Validar la Cedula de una Persona
def validar_cedula(cedula):
    pares = [];
    impares = [];
    
    if len(extraer_numeros(cedula)) != 10:
        return False

    for i in range (9):
        if i % 2 != 0:
            pares.append(int(cedula[i]));
        else:
            impares.append(int(cedula[i]));

    suma_pares = 0;
    for num in pares:
        suma_pares = suma_pares + num;

    suma_impares = 0;
    for num in impares:
        producto = 0;
    
        producto = num * 2;

        if producto > 9:
            producto = producto - 9;

        suma_impares = suma_impares + producto;

    suma_total = suma_pares + suma_impares;
    limite_superior = ''
    
    limite_superior = int(str(int(str(suma_total)[0]) + 1) + '0')
    if int(limite_superior - suma_total) == int(cedula[9]):
        return True
    else:
        return False
    
#Validar la Cedula y RUC de una persona
def validar_cedula_ruc(cedula_ruc):
    ced_ruc=cedula_ruc
    if cedula_ruc:
        if len(cedula_ruc)==10 and cedula_ruc.isdigit() and cedula_ruc:
            string = ""
            resultado = 0
            for i in range (0, 10):
                string += ced_ruc[i] + " "
            lista = string.split()
            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            for j in range(0, len(coeficientes)):
                valor = int(lista[j]) * coeficientes[j]
                if valor >= 10:
                    str1 = str(valor)
                    suma = int(str1[0]) + int(str1[1])
                    resultado += suma
                else:
                    resultado += int(lista[j]) * coeficientes[j]
            residuo = resultado%10
            if residuo != 0:
                verificador = 10 - residuo
            else:
                verificador = residuo
            if verificador == int(lista[9]):
                return True
            else:
                return False
        elif not cedula_ruc.isdigit():
            if cedula_ruc[0]=='P':
                return True    
            #result['value']={'personal_id':cedula_ruc}
        else:
            return False
    else:
        return False

'''-----------------------------------------------------------------------------------Generar un Username a partir del nombre'''    
def delete_except_word(lista):
    exceptions = ['el', 'la', 'los', 'las', 'de', 'del', '', ' ']
    nueva_lista = copy.copy(lista)
    for palabra in nueva_lista:
        for exception in exceptions:
            if unicode(palabra).lower() == unicode(exception).lower():
                lista.remove(palabra)
                continue
    return lista
    
def do_dic(cad, type_case='lower'):
    palabras = []
    
    palabra = ''
    try:
        cad = list(cad)
    except: 
        cad = []
    for letra in cad:
        if letra == ' ':
            if len(palabra.lstrip(' ').lower()) > 1:
                word = palabra.lstrip(' ')
                if str(type_case).lower() =='lower':
                    palabras.append(unicode(word).lower())
                elif str(type_case).lower() =='upper':
                    palabras.append(unicode(word).upper())
                else:
                    palabras.append(word)
            palabra = ''
        else:
            palabra += unicode(letra)
    if len(palabra.lstrip(' ').lower()) > 1:
        word = palabra.lstrip(' ')
        if str(type_case).lower() =='lower':
            palabras.append(unicode(word).lower())
        elif str(type_case).lower() =='upper':
            palabras.append(unicode(word).upper())
        else:
            palabras.append(word)
    
    return delete_except_word(palabras)
        
def quitar_acentos(cadena):
    try:
        cadena=unicode(cadena, 'utf-8')
    except:
        cadena = cadena
    return normalize('NFKD',cadena).encode('ASCII', 'ignore')
   
def buid_username(names):
    dic_name = do_dic(names)
    num_words = len(dic_name)
    username = ''
    if num_words == 2:
        username = unicode(dic_name[1][0]) + unicode(dic_name[0])
    elif num_words == 3:
        username = unicode(dic_name[1][0]) + unicode(dic_name[2][0]) + unicode(dic_name[0])
    else:
        username = unicode(dic_name[2][0]) + unicode(dic_name[3][0]) + unicode(dic_name[0] + unicode(dic_name[1][0]))
    return username

def convert_hour_format_to_float(hour_str, seconds=False):
    hour = hour_str[:2]
    minutes = hour_str[3:5]
    return float(hour) + float(float(minutes) / 60) 
    
def convert_float_to_hour_format(hour_float, seconds=False):
    hora = str(int(hour_float))
    minutos = float(hour_float) - float(hora)
    minutos = int(round(minutos * 60, 0))
        
    if len(str(hora)) == 1:
        hora = '0' + str(hora)
    
    if len(str(minutos)) == 1:
        minutos = '0' + str(minutos)
    if seconds:
        return str(hora) + ':' + str(minutos) + ':00'
    else:
        return str(hora) + ':' + str(minutos)

def convert_minutes_to_hour_format(minutes, separator="H"):
    horas = completar_cadena(int(minutes) / 60)
    minutos = completar_cadena(minutes % 60)
    return "%s%s%s"%(horas,separator, minutos)
    
def completar_cadena(cadena, num=2):
    cadena = unicode(cadena)
    while len(cadena) < int(num):
        cadena = '0' + str(cadena)
    return str(cadena)

def convert_to_datetime(date):
    try:
        date = datetime.strptime(date, '%Y-%m-%d %H')
    except:
        try:
            date = datetime.strptime(date, '%Y-%m-%d %H:%M')
        except:
            try:
                date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            except:
                try:
                    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    return False
    return date

def convert_to_UTC_tz(date, tz,res=0):
    date = convert_to_datetime(date)
    tzutc = timezone('UTC')
    tzlocal = timezone(tz)
    local_dt = tzlocal.localize(date, is_dst=False)
    local_utc = local_dt.astimezone(tzutc)
    date_result = local_utc
    if res==1:
        return date_result.date().__str__()
    elif res==2:
        return date_result.time().__str__()
    else:
        return "%s %s"%(date_result.date().__str__(), date_result.time().__str__())
    
def convert_to_tz(date, tz,res=0):
    date = convert_to_datetime(date)
    tzutc = timezone('UTC')
    tzlocal = timezone(tz)
    utc_dt = tzutc.localize(date, is_dst=False)
    local_dt = utc_dt.astimezone(tzlocal)
    date_result = local_dt
    if res==1:
        return date_result.date().__str__()
    elif res==2:
        return date_result.time().__str__()
    else:
        return "%s %s"%(date_result.date().__str__(), date_result.time().__str__())
    
def _convert_UTC_to_GMT(date,dd_mm_yyyy=False,res=0):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    try:
        utc = datetime.strptime(date, '%Y-%m-%d %H:%M')
    except:
        try:
            utc = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        except:
            utc = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    utc = utc.replace(tzinfo=from_zone)
    result = utc.astimezone(to_zone)
    idate = str(result.year) + '-' + completar_cadena(str(result.month)) + '-' + completar_cadena(str(result.day))
    if dd_mm_yyyy:
        idate = completar_cadena(str(result.day)) + '-' + completar_cadena(str(result.month)) + '-' + str(result.year)
    itime = completar_cadena(str(result.hour)) + ':' + completar_cadena(str(result.minute)) + ':' + completar_cadena(str(result.second))
    if res==0:
        return idate + ' ' + itime
    elif res == 1:
        return idate
    elif res == 2:
        return itime

def _convert_GMT_to_UTC(date,dd_mm_yyyy=False,res=0):
    to_zone = tz.tzutc()
    from_zone = tz.tzlocal()
    try:
        gmt = datetime.strptime(date, '%Y-%m-%d %H:%M')
    except:
        try:
            gmt = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        except:
            gmt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
            
    gmt = gmt.replace(tzinfo=from_zone)
    result = gmt.astimezone(to_zone)
    idate = str(result.year) + '-' + completar_cadena(str(result.month)) + '-' + completar_cadena(str(result.day))
    if dd_mm_yyyy:
        idate = completar_cadena(str(result.day)) + '-' + completar_cadena(str(result.month)) + '-' + str(result.year)
    itime = completar_cadena(str(result.hour)) + ':' + completar_cadena(str(result.minute)) + ':' + completar_cadena(str(result.second))
    if res==0:
        return idate + ' ' + itime
    elif res == 1:
        return idate
    elif res == 2:
        return itime

def convert_to_format_date(date, time_init, time_start, time_end, tz):
    time_start = convert_float_to_hour_format(time_start)
    time_end = convert_float_to_hour_format(time_end)
    time_init = convert_float_to_hour_format(time_init)
    date = str(date)[:10]
    date_start = convert_to_UTC_tz(date + ' ' + time_start,tz)
    date_stop = convert_to_UTC_tz(date + ' ' + time_end,tz)
    date_init = convert_to_UTC_tz(date + ' ' + time_init,tz)
    return {'date_init':date_init, 'date_start':date_start, 'date_stop':date_stop}
    
def convert_month_to_string_format(month):
    month = int(month)
    if month==1:
        return 'Enero'
    elif month==2:
        return 'Febrero'
    elif month==3:
        return 'Marzo'
    elif month==4:
        return 'Abril'
    elif month==5:
        return 'Mayo'
    elif month==6:
        return 'Junio'
    elif month==7:
        return 'Julio'
    elif month==8:
        return 'Agosto'
    elif month==9:
        return 'Septiembre'
    elif month==10:
        return 'Octubre'
    elif month==11:
        return 'Noviembre'
    elif month==11:
        return 'Diciembre'
    else:
        return None
    
def convert_date_format_long_ymd(year, month, day):
    return unicode(day) + ' de ' + unicode(convert_month_to_string_format(month)) + ' del ' + unicode(year)
    
def convert_date_format_long_str(str_date):
    str_year = str_date[:4]
    str_month = str_date[5:7]
    str_day = str_date[8:10]
    return convert_date_format_long_ymd(str_year, str_month, str_day)

def convert_date_format_short_str(str_date):
    str_year = str_date[:4]
    str_month = str_date[5:7]
    str_day = str_date[8:10]
    return str_day + '-' +  str_month + '-' + str_year

def dias_de_un_mes(year, month):
    cal = calendar.Calendar()
    return [x for x in cal.itermonthdays(int(year), int(month)) if x][-1]

def dias_de_este_mes():
    year = time.strftime("%Y")
    month = time.strftime("%m")
    return dias_de_un_mes(year, month)

def get_standard_names(names):
    dic_name = do_dic(names)
    num_words = len(dic_name)
    username = ''
    if num_words == 2:
        username = unicode(dic_name[1]).title() + ' ' +  unicode(dic_name[0]).title()
    elif num_words == 3:
        username = unicode(dic_name[2]).title() + ' '+ unicode(dic_name[0]).title()
    else:
        username = unicode(dic_name[2]).title() + ' '+ unicode(dic_name[0]).title()
        
    return username

def convert_date_format_long(str_date):
    str_year = str_date[:4]
    str_month = str_date[5:7]
    str_day = str_date[8:10]
    
    t = (int(str_year),int(str_month),int(str_day),00,00,00,00,00,00)
    t = time.mktime(t)
    return time.strftime('%A %d de %B de %Y', time.gmtime(t))

def percentage_elapsed_of_period(date_start, date_end):
    date_start_year = str_date[:4]
    date_start_month = str_date[5:7]
    date_start_day = str_date[8:10]
    
    date_start = datetime.strptime(date_start, '%Y-%m-%d')
    date_end = datetime.strptime(date_end, '%Y-%m-%d')
    total_days = (date_end - date_start).days
    after_days = (datetime.now() - date_start).days
    
    return float(after_days * 100) / float(total_days)

def restrict_size(binarty_file, max_kb):
    max_size = max_kb * 1024
    try:
        binarty_file = base64.b64decode(binarty_file)
        bytes_size = len(binarty_file)
        print best_unit_size(bytes_size)
    except: bytes_size = 0
    if bytes_size < max_size:
        return True
    else:
        return False
    
def photo_valid_size(photo):
    res = {}
    res['max_size'] = 50
    res['valid'] = restrict_size(photo, res['max_size'])
    return res

def best_unit_size(bytes_size):
    """Get a size in bytes & convert it to the best IEC prefix for readability.

    Return a dictionary with three pair of keys/values:

    "s" -- (float) Size of path converted to the best unit for easy read
    "u" -- (str) The prefix (IEC) for s (from bytes(2^0) to YiB(2^80))
    "b" -- (int / long) The original size in bytes

    """
    for exp in range(0, 90 , 10):
        bu_size = abs(bytes_size) / pow(2.0, exp)
        if int(bu_size) < 2 ** 10:
            unit = {0:"bytes", 10:"KiB", 20:"MiB", 30:"GiB", 40:"TiB", 50:"PiB",
                    60:"EiB", 70:"ZiB", 80:"YiB", 90:"BiB"}[exp]
            break
    return {"s":bu_size, "u":unit, "b":bytes_size}
    
def convert_date_to_dmy(date, separator='/'):
    try:
        res = DateTime.strptime(date,'%Y-%m-%d %H:%M:%S')
    except:
        res = DateTime.strptime(date,'%Y-%m-%d')
    return completar_cadena(res.day, 2)  + separator + completar_cadena(res.month, 2) + separator + completar_cadena(res.year, 4)
    
def calcular_edad(date_start, format=1, date_end="now"):
    try:
        if date_end == "now":
            date_end=DateTime.now()
        else:
            date_end = DateTime.strptime(date_end,'%Y-%m-%d')
        dob=DateTime.strptime(date_start,'%Y-%m-%d')
        delta=DateTime.Age (date_end, dob)
    
        if format == 1:
            return str(delta.years)
        elif format == 2:
            return str(delta.years) +" A/"+ str(delta.months) +" M"
        elif format == 3:
            return str(delta.years) +" A/"+ str(delta.months) +" M/"+ str(delta.days)+" D "
        elif format == 4:
            str_year = ""
            if delta.years < 1:
                str_year = u""
            elif delta.years == 1:
                str_year = u"%s %s" %(str(delta.years),u'año')
                if delta.months > 0:
                    str_year= str_year + ','
            else:
                str_year = u"%s %s" %(str(delta.years),u'años')
                if delta.months > 0:
                    str_year= str_year + ','
                
            str_month = ""
            if delta.months < 1:
                str_month = ""
            else:
                if delta.months == 1:
                    str_month = u"%s %s" %(str(delta.months),u'mes')
                else:
                    str_month = u"%s %s" %(str(delta.months),u'meses')
                
            str_day = ""
            if (delta.days < 1 and delta.months > 0) or (delta.days < 1 and delta.years > 0):
                str_day = ""
            else:
                if delta.days == 1:
                    str_day = u"%s %s" %(str(delta.days),u'día')
                else:
                    str_day = u"%s %s" %(str(delta.days),u'días')
                    
                if delta.months > 0 or delta.years > 0:
                    str_day =  'y ' + str_day
            
            res =  "%s %s %s"%(str_year,str_month,str_day)
            return res.strip()
    except: return "0"
    
def convert_to_tuple_str(list, cero=False):
    if cero:
        res = '(0)'
    else:
        res = '()'
    if len(list) > 0:
        if len(list) == 1:
            res = '(%s)'%str(list[0])
        else:
            res = str(tuple(list))
    return res

def convert_result_query_to_list(result_query, sigle_column=False):
    res = []
    if sigle_column:
        for tpl in result_query:
            res.append(tpl[0])
    else:
        for tpl in result_query:
            row = []
            for cell in tpl:
                row.append(cell)
            res.append(row)
    return res

#Dar TimeOut! a un Proceso
def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = default
        def run(self):
            self.result = func(*args, **kwargs)
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return it.result
    else:
        return it.result

def get_image_code(value, width, height, hr=False, code='QR'):
    """ genrating image for barcode """
    options = {}
    if width:options['width'] = width
    if height:options['height'] = height
    if hr:options['humanReadable'] = hr
    try:
        ret_val = createBarcodeDrawing(code, value=unicode(value), **options)
    except Exception, e:
        raise osv.except_osv('Error', e)
    return base64.encodestring(ret_val.asString('jpg'))

def addworkdays(date_start, days,tz,holidays=(), workdays=('LUN','MAR','MIE','JUE','VIE')):
    avalible_days = []
    for workday in workdays:
        if workday == 'MON' or workday == 'LUN' or workday == 'LUNES' or workday == 'MONDAY':avalible_days.append(0)
        if workday == 'TUE' or workday == 'MAR' or workday == 'MARTES' or workday == 'TUESDAY':avalible_days.append(1)
        if workday == 'WED' or workday == 'MIE' or workday == 'MIERCOLES' or workday == 'WEDNESDAY':avalible_days.append(2)
        if workday == 'THU' or workday == 'JUE' or workday == 'JUEVES' or workday == 'THURSDAY':avalible_days.append(3)
        if workday == 'FRI' or workday == 'VIE' or workday == 'VIERNES' or workday == 'FRIDAY':avalible_days.append(4)
        if workday == 'SAT' or workday == 'SAB' or workday == 'SABADO' or workday == 'SATURDAY':avalible_days.append(5)
        if workday == 'SUN' or workday == 'DOM' or workday == 'DOMINGO' or workday == 'SUNDAY':avalible_days.append(6)
    if workdays==False:
        avalible_days=[1]
    if type(date_start).__name__ != 'datetime':
        try:date_start = datetime.strptime(date_start, '%Y-%m-%d')
        except:
            try:date_start = datetime.strptime(date_start, '%Y-%m-%d %H:%M:%S')
            except: return None
    sum_days = 0
    business_days = 0
    while business_days < days:
        weekday = 10
        while not weekday in avalible_days:
            res_date = (date_start + timedelta(days=sum_days))
            weekday = res_date.weekday()
            sum_days += 1
        business_days += 1
    res_days = sum_days
    if holidays:
        for day in range(sum_days):
            res_date = (date_start + timedelta(days=day))
            if res_date.weekday() in avalible_days:
                current_date = "%s/%s/%d"%(completar_cadena(res_date.day), completar_cadena(res_date.month), res_date.year)
                try:
                    for holiday in holidays:
                        if len(holiday) == 5:
                            holiday = "%s/%d"%(holiday,res_date.year)
                        else:
                            holiday = datetime.strptime(holiday, '%d-%m-%Y')
                            holiday = "%s/%s/%d"%(completar_cadena(holiday.day), completar_cadena(holiday.month), holiday.year)
                        if current_date == holiday: res_days += 1
                except:None
    res_days -= 1
    if days < 1 or res_days < 1:
        res_days = 0
    res = date_start + timedelta(days=res_days)
    res = convert_to_UTC_tz(res.__str__(),tz)
    return res
    
def get_end_date(date_start, days,tz, holidays=(), workdays=('LUN','MAR','MIE','JUE','VIE')):
    date_start = datetime.strptime(date_start, '%Y-%m-%d')
    res = addworkdays(date_start, days, tz, holidays, workdays)
    return res.__str__()

def resize_image(photo, photo_path,size_base=64,remove_file=True):
    from PIL import Image
    import StringIO
    try:
        photo = base64.b64decode(photo)
    except:
        if not photo or photo is None:
            return False
    output = open(photo_path, 'wb')
    output.write(photo)
    output.close()
    foto = Image.open(photo_path)
    
    width = foto.size[0]
    height = foto.size[1]
    format = str(foto.format).lower()
    if width != height:
        if width < height:
            width = width * size_base / height
            height = size_base
        else:
            height = height * size_base / width
            width = size_base
    else:
        height = size_base
        width = size_base
    foto = foto.resize((width,height), Image.ANTIALIAS)
    foto.save(photo_path,format=format)
    res_image = base64.encodestring(open(photo_path,"rb").read())
    if remove_file:
        os.remove(photo_path)
    return res_image