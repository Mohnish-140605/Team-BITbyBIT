import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import subprocess

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Hardcoded user credentials for demo
users = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return redirect(url_for('home'))

# Signup Page
@app.route('/home', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('User already exists!', 'error')
        else:
            users[username] = password
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('home'))
    return render_template('home.html')

# Login Page
@app.route('/about', methods=['GET', 'POST'])
def about():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            flash('Login Successful!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid Credentials. Please try again.', 'error')
    return render_template('about.html')


# PDF Upload Page

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            try:
                # Run the combined.py script and pass the uploaded file path
                result = subprocess.check_output(['python', 'combined.py', file_path], text=True)

                # Show the result on the webpage
                return render_template('upload.html', content=result)

            except subprocess.CalledProcessError as e:
                flash(f"Error running combined.py: {e.output}", 'error')
                return redirect(request.url)

        else:
            flash('Only PDF files are allowed!', 'error')
    return render_template('upload.html', content=None)


if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True,port=5001)
