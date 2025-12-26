
from flask import Flask, render_template, request
import io
from contextlib import redirect_stdout
from sec_pass.tester import make_whmcs_request, set_server_id

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    output = None
    server_id = None
    if request.method == 'POST':
        server_id = request.form.get('server_id')
        if server_id:
            # We still capture stdout for now so you don't have to 
            # rewrite all of tester.py, but we clean it up for the UI
            f = io.StringIO()
            with redirect_stdout(f):
                set_server_id(server_id)
                make_whmcs_request()
            output = f.getvalue()
    
    return render_template('index.html', output=output, server_id=server_id)

if __name__ == "__main__":
    # Internal port 8000 is correct for Gunicorn/Docker
    app.run(host='0.0.0.0', port=8000)
