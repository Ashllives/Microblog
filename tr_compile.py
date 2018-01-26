#!flask/bin/python
import os
import sys
if sys.platform == 'win32':
    pybabel = 'microblog\\Scripts\\pybabel'
else:
    pybabel = 'microblog/bin/pybabel'
os.system(pybabel + ' compile -d app/translations')