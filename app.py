from flask import Flask, render_template, request
import io
import sys
from contextlib import redirect_stdout
from sec_pass.tester import make_whmcs_request, set_server_id

app = Flask(__name__)

# --- 1. PROXY MIDDLEWARE START ---
class PrefixMiddleware(object):
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        # This checks if the request starts with /secpass
        if environ['PATH_INFO'].startswith(self.prefix):
            # Strip the prefix before passing it to Flask routes
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            # If someone hits the container directly without the prefix, 
            # we return a 404 to stay consistent with the proxy behavior.
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b"Not Found"]

# Wrap the app with the /secpass prefix
app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='/secpass')
# --- PROXY MIDDLEWARE END ---

@app.route('/', methods=['GET', 'POST'])
def index():
    output = None
    server_id = None
    
    if request.method == 'POST':
        raw_input = request.form.get('server_id', '')
        server_id = raw_input.strip()
        
        if server_id:
            f = io.StringIO()
            with redirect_stdout(f):
                set_server_id(server_id)
                make_whmcs_request()
            output = f.getvalue()
        else:
            output = "Error: Please enter a valid Server ID."
    
    return render_template('index.html', output=output, server_id=server_id)

if __name__ == "__main__":
    # Internal port 8000 for Gunicorn/Docker
    app.run(host='0.0.0.0', port=8000)
