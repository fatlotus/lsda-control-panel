from gevent.pywsgi import WSGIServer

import os.path, sys; sys.path.append(os.path.dirname(__file__))
from main import app as application

WSGIServer(('', 8082), application).serve_forever()
