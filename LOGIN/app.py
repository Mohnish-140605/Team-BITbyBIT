import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import subprocess
import json
from groq import Groq
from flask import Flask, request, jsonify, render_template
from deepgram import DeepgramClient, PrerecordedOptions
import os
import webbrowser
from threading import Timer
import json
from groq import Groq
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = 'users_logins.db'

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

# Check allowed file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/mock')
def mock():
    return render_template('mock.html')


# Signup Page
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

# Login Page
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

# Home Page
@app.route('/home')
def home():
    if 'username' not in session:
        flash('You must log in first!', 'error')
        return redirect(url_for('login'))
    return render_template('home.html')

# About Page
@app.route('/about')
def about():
    if 'username' not in session:
        flash('You must log in first!', 'error')
        return redirect(url_for('login'))
    return render_template('about.html')

# PDF Upload Page
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
                result = subprocess.check_output(['python', 'combined.py', file_path,job_board], text=True)

                # Show the result on the webpage
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


client = Groq(api_key="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")
TRANSCRIPTIONS_DIR = "transcriptions"
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)

# Folder to save uploaded audio files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Folder to save transcription results
TRANSCRIPTION_FOLDER = 'transcriptions'
if not os.path.exists(TRANSCRIPTION_FOLDER):
    os.makedirs(TRANSCRIPTION_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSCRIPTION_FOLDER'] = TRANSCRIPTION_FOLDER

# Your Deepgram API key
DEEPGRAM_API_KEY = '4f1dce172a29010ed40aeaa3e0972d300b5f40b7'
QUESTIONS_FILE_PATH = "questions.txt"

@app.route("/generate_final_report", methods=["POST"])

def generate_final_report():
    try:
        # Check if the file exists
        if not os.path.exists(QUESTIONS_FILE_PATH):
            return jsonify({"report": "Error: 'questions.txt' file not found."}), 404

        # Read the contents of questions.txt file
        with open(QUESTIONS_FILE_PATH, "r") as file:
            final_report_data = file.read()

        # Return the contents of the file as a report
        return jsonify({"report": final_report_data})

    except Exception as e:
        # In case of an error, return an error message
        return jsonify({"report": f"Error generating the final report: {str(e)}"}), 500


@app.route('/get_report', methods=['GET'])
def get_report():
    file_path = 'questions.txt'
    
    try:
        with open(file_path, 'r') as file:
            questions = file.readlines()
            questions = [q.strip() for q in questions]  # Clean up the newlines and extra spaces
        return jsonify({"questions": questions})
    except FileNotFoundError:
        return jsonify({"error": f"The file {file_path} was not found."}), 404

# Handle audio upload and transcription
@app.route("/get_transcription", methods=["GET"])
def get_transcription():
    # Read the transcription file
    transcription_filename = os.path.join(TRANSCRIPTIONS_DIR, "transcription.txt")
    if os.path.exists(transcription_filename):
        with open(transcription_filename, "r") as f:
            transcription = f.read()
        return jsonify({"transcription": transcription})
    else:
        return jsonify({"error": "Transcription file not found"}), 404

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


def transcribe_audio(file_path):
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)

    with open(file_path, 'rb') as buffer_data:
        payload = {'buffer': buffer_data}

        options = PrerecordedOptions(
            smart_format=True, model="nova-2", language="en-US"
        )

        try:
            response = deepgram.listen.prerecorded.v('1').transcribe_file(payload, options)
            return response.to_json(indent=4)  # Return transcription as JSON
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None



def extract_text_from_json(transcription):
    """Extracts the text from the transcription JSON."""
    # Debug: Print the transcription structure to inspect
    print("Transcription JSON (raw):", transcription)

    # Parse the JSON string into a dictionary
    try:
        transcription = json.loads(transcription)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return ""

    # Check if the necessary keys exist in the transcription
    if not transcription or 'results' not in transcription or 'channels' not in transcription['results']:
        print("Error: Invalid transcription structure")
        return ""

    text = ""
    try:
        for channel in transcription['results']['channels']:
            for alternative in channel.get('alternatives', []):
                text += alternative.get('transcript', '') + '\n'
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""
    file_path = 'questions.txt'

    try:
        with open(file_path, 'r') as file:
            questions = file.readlines()  # Read all lines from the file
            questions = [question.strip() for question in questions]  # Remove newline characters
        
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    prompt = f"""
Please review the following questions and answers:

Questions:
{questions}

Answers:
{text}

Now, please analyze both the questions and answers, and provide a summary of your analysis. Specifically, check:
1. Whether the answers correctly address the questions.
2. If any answers lack depth or detail.
3. Whether any answers are missing or require further elaboration.
4. Overall quality of the answers in relation to the questions.

Provide a quick report on the accuracy, completeness, and clarity of the answers. Thank you!
"""

    report = extract_skills_groq(prompt)
    with open(file_path, 'w') as file:
        
            file.write(report + '\n')


    return report


def extract_skills_groq(promt):
   
    # Call the function from groqsorting.py
    skills  = client.chat.completions.create(
            messages=[{"role": "user", "content": promt}],
            model="llama3-8b-8192"
        )
    return skills.choices[0].message.content
# Handle role selection
@app.route('/handle_role', methods=['POST'])
def handle_role():
    """Handle role selection and return a response."""
    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({"error": "Role not provided"}), 400

    role = data['role']
    # if role == "Software Engineer":
    #     message = "You selected the Software Engineer role. Resources are being prepared."
    #     return jsonify({"message": message, "resources": ["Resource A", "Resource B", "Resource C"]})
    # elif role == "Web Development":
    #     message = "You selected the Web Development role. Resources are being prepared."
    #     return jsonify({"message": message, "resources": ["Resource X", "Resource Y", "Resource Z"]})
    # else:
    #     return jsonify({"error": "Invalid role selected"}), 400
    prompt ="generate 4-5 questions for the given job tite let the questions be set a little bit difficult like the indsutry standrads. Do not give mcqs "+role
    questions =extract_skills_groq(prompt)
    if isinstance(questions, str):  # If the questions are returned as a string, convert them into an array
        questions = questions.split('\n')  
    file_path = 'questions.txt'
    
    # Ensure file is in write mode and write the questions
    with open(file_path, 'w') as file:
        for question in questions:
            file.write(question + '\n')
    return jsonify({"questions": questions})


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
