from flask import Flask, render_template, request
import io
import sys
from contextlib import redirect_stdout
from sec_pass.tester import make_whmcs_request, set_server_id

app = Flask(__name__)

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
