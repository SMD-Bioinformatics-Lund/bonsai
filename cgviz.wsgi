activate_this = '/var/www/cgviz/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import sys

sys.path.append('/var/www/cgviz')
 
from cgviz import app as application