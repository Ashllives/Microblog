#!flask/bin/python
import os
import sys
if sys.platform == 'win32':
    pybabel = 'microblog\\Scripts\\pybabel'
else:
    pybabel = 'microblog/bin/pybabel'
os.system(pybabel + ' extract -F babel.cfg -k lazy_gettext -o messages.pot app')
os.system(pybabel + ' update -i messages.pot -d app/translations')
os.unlink('messages.pot')