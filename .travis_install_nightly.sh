#!/bin/bash
# Install the nightly version of OpenERP

cd ..
sudo apt-get -ym install python-dateutil python-docutils python-feedparser python-gdata python-jinja2 python-ldap python-lxml python-mako python-mock python-openid python-psycopg2 python-psutil python-pybabel python-pychart python-pydot python-pyparsing python-reportlab python-simplejson python-tz python-unittest2 python-vatnumber python-vobject python-webdav python-werkzeug python-xlwt python-yaml python-zsi python-imaging bzr

sudo apt-get install -y python-dateutil python-feedparser python-gdata python-ldap python-libxslt1 python-lxml python-mako python-openid python-psycopg2  python-pybabel python-pychart python-pydot python-pyparsing python-reportlab python-simplejson python-tz python-vatnumber python-vobject python-webdav python-xlwt python-yaml python-zsi python-docutils python-psutil bzr wget python-unittest2 python-mock python-jinja2 python-soappy python-setuptools wkhtmltopdf

git clone --depth=50 https://github.com/syleam/openerp.git -b ocb-addons/7.0 addons
git clone --depth=50 https://github.com/syleam/openerp.git -b ocb-server/7.0 server
git clone --depth=50 https://github.com/syleam/openerp.git -b ocb-web/7.0 web

# copy all module in server/openerp/addons
cp -a openerp-postgresql/ ./server/openerp/addons/postgresql
cp -a web/addons ./server/openerp
cp -a addons ./server/openerp

# install it as python package
cd server
python setup.py --quiet install
cd ..

