import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import subprocess
import json
from deepgram import DeepgramClient, PrerecordedOptions
from groq import Groq
import webbrowser
from threading import Timer

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# File upload configuration
UPLOAD_FOLDER = 'uploads'
TRANSCRIPTION_FOLDER = 'transcriptions'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSCRIPTION_FOLDER'] = TRANSCRIPTION_FOLDER

# Database configuration
DATABASE = 'users_logins.db'
DEEPGRAM_API_KEY = '4f1dce172a29010ed40aeaa3e0972d300b5f40b7'
QUESTIONS_FILE_PATH = "questions.txt"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPTION_FOLDER, exist_ok=True)

# Initialize Groq client
client = Groq(api_key="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")

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database
def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home page
@app.route('/')
def index():
    return redirect(url_for('login'))

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        with get_db_connection() as conn:
            try:
                conn.execute(
                    'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                    (username, email, password)
                )
                conn.commit()
                flash('Signup successful! Please login.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('User or email already exists!', 'error')
    return render_template('signup.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ? AND password = ?',
                (username, password)
            ).fetchone()
            if user:
                flash('Login successful!', 'success')
                session['username'] = username
                return redirect(url_for('home'))
            else:
                flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

# Home page after login
@app.route('/home')
def home():
    if 'username' not in session:
        flash('You must log in first!', 'error')
        return redirect(url_for('login'))
    return render_template('home.html')

# About page
@app.route('/about')
def about():
    if 'username' not in session:
        flash('You must log in first!', 'error')
        return redirect(url_for('login'))
    return render_template('about.html')

# PDF Upload page
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        flash('You must log in first!', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        job_board = request.form['job_board']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            try:
                # Run the combined.py script and pass the uploaded file path
                result = subprocess.check_output(['python', 'combined.py', file_path, job_board], text=True)
                return render_template('upload.html', content=result)
            except subprocess.CalledProcessError as e:
                flash(f"Error running combined.py: {e.output}", 'error')
                return redirect(request.url)
        else:
            flash('Only PDF files are allowed!', 'error')
    return render_template('upload.html', content=None)

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# Audio Upload page
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No file part"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the audio file
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file.filename)
    audio_file.save(audio_path)

    # Send the audio file to Deepgram for transcription
    transcription = transcribe_audio(audio_path)
    if transcription:
        # Save the transcription to a file
        transcription_filename = f"{os.path.splitext(audio_file.filename)[0]}.json"
        transcription_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], transcription_filename)

        with open(transcription_path, 'w') as f:
            json.dump(transcription, f, indent=4)

        # Extract text from the transcription and save it to a txt file
        text_filename = f"{os.path.splitext(audio_file.filename)[0]}.txt"
        text_path = os.path.join(app.config['TRANSCRIPTION_FOLDER'], text_filename)

        # Extracting text from the transcription
        transcription_text = extract_text_from_json(transcription)

        # Save the extracted text to a txt file
        with open(text_path, 'w') as text_file:
            text_file.write(transcription_text)

        return jsonify({"message": "Audio file uploaded and transcribed successfully", "transcription_file": transcription_filename, "text_file": text_filename})
    else:
        return jsonify({"error": "Failed to transcribe audio"}), 500
@app.route('/mock')
def mock():
    return render_template('mock.html')

def transcribe_audio(file_path):
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)
    with open(file_path, 'rb') as buffer_data:
        payload = {'buffer': buffer_data}
        options = PrerecordedOptions(smart_format=True, model="nova-2", language="en-US")
        try:
            response = deepgram.listen.prerecorded.v('1').transcribe_file(payload, options)
            return response.to_json(indent=4)
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

def extract_text_from_json(transcription):
    try:
        transcription = json.loads(transcription)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return ""

    text = ""
    try:
        for channel in transcription['results']['channels']:
            for alternative in channel.get('alternatives', []):
                text += alternative.get('transcript', '') + '\n'
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""
    
    return text

# Role selection and question generation
@app.route('/handle_role', methods=['POST'])
def handle_role():
    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({"error": "Role not provided"}), 400

    role = data['role']
    prompt = f"generate 4-5 questions for the given job title, set a little bit difficult like industry standards. Do not give mcqs. {role}"
    questions = extract_skills_groq(prompt)
    if isinstance(questions, str):
        questions = questions.split('\n')
    file_path = 'questions.txt'
    with open(file_path, 'w') as file:
        for question in questions:
            file.write(question + '\n')
    return jsonify({"questions": questions})

def extract_skills_groq(promt):
    skills = client.chat.completions.create(
        messages=[{"role": "user", "content": promt}],
        model="llama3-8b-8192"
    )
    return skills.choices[0].message.content

# Open browser automatically when the app starts
def open_browser():
    if not app.debug:
        webbrowser.open('http://127.0.0.1:5000/')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
