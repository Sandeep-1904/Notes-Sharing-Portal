import os
from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB setup
def init_db():
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        subject TEXT,
        year TEXT,
        semester TEXT,
        description TEXT,
        filename TEXT,
        uploaded_at TEXT
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    selected_year = request.args.get('year', 'all')
    
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    
    # Get available years for filter dropdown
    c.execute("SELECT DISTINCT year FROM notes ORDER BY year")
    available_years = [row[0] for row in c.fetchall()]
    
    # Get notes based on selected filter
    if selected_year == 'all':
        c.execute("SELECT * FROM notes ORDER BY year, semester, uploaded_at DESC")
    else:
        c.execute("SELECT * FROM notes WHERE year = ? ORDER BY semester, uploaded_at DESC", (selected_year,))
    
    notes = c.fetchall()
    conn.close()
    
    return render_template('index.html', 
                         notes=notes, 
                         is_admin=session.get('admin'),
                         selected_year=selected_year,
                         available_years=available_years)

# Admin login
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    valid_passwords = ['test', 'password']  # ← Add your passwords here

    if request.method == 'POST':
        password = request.form['password']
        if password in valid_passwords:
            session['admin'] = True
            return redirect('/')
        else:
            return "<h3>Incorrect password. <a href='/admin'>Try again</a></h3>"
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('admin'):
        return redirect('/admin')  # Force login if not admin

    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        year = request.form['year']
        semester = request.form['semester']
        description = request.form['description']
        file = request.files['file']

        if file and file.filename.endswith('.pdf'):
            # Include year and semester in filename to prevent conflicts
            filename = f"{year}_{semester}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            conn = sqlite3.connect('notes.db')
            c = conn.cursor()
            c.execute("""INSERT INTO notes 
                        (title, subject, year, semester, description, filename, uploaded_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (title, subject, year, semester, description, filename, 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return redirect('/')

    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if not session.get('admin'):
        return redirect('/admin')  # Only allow admins to delete
    
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    
    # Get the filename before deleting
    c.execute("SELECT filename FROM notes WHERE id = ?", (note_id,))
    result = c.fetchone()
    
    if result:
        filename = result[0]
        # Delete from database
        c.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        
        # Delete the file
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
    
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
   # app.run(host='0.0.0.0', port=5000, debug=True)
