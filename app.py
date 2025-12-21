from flask import Flask, render_template, request
import io
import sys
from contextlib import redirect_stdout
from sec_pass.tester import make_whmcs_request, set_server_id # We will tweak tester.py slightly

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    output = ""
    if request.method == 'POST':
        server_id = request.form.get('server_id')
        if server_id:
            # Capture the print statements from your script
            f = io.StringIO()
            with redirect_stdout(f):
                # Pass the ID to your existing logic
                set_server_id(server_id)
                make_whmcs_request()
            output = f.getvalue()
    
    return render_template('index.html', output=output)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
