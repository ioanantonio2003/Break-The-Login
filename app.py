from flask import Flask, request, render_template
import sqlite3

app = Flask(__name__)

# ne conectam la baza de date
def connect_to_database():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

#functia pentru inregistrare
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        #acum lasam parola sa fie oricat de slaba si scurta
        #nu hashuim parola si o lasam in clar
        
        conn = connect_to_database()
        try:
            #inseram utilizatorul in baza de date
            conn.execute('INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)', (email, password, 'USER'))
            conn.commit()
            conn.close()
            return "<h3>Cont creat cu succes!</h3><a href='/register'>Inapoi</a>"
        except sqlite3.IntegrityError:
            # singura problema de inserare ar fi daca emailul exista deja (UNIQUE)
            conn.close()
            return "<h3>Eroare: Email deja existent!</h3><a href='/register'>Inapoi</a>"

    # pt get 
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = connect_to_database()
        
        #verificam daca exista in tabela users un user cu acest email
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        # aici daca emailul nu exista zicem ca nu exista
        if user is None:
            return "<h3>Eroare: Email-ul nu exista în baza de date!</h3><a href='/login'>Incearca din nou</a>"
        
        #daca email-ul exista dar parola e gresita zicem ca parola e gresita
        if user['password_hash'] != password:
            return "<h3>Eroare: Parola este gresita pentru acest email!</h3><a href='/login'>Incearca din nou</a>"

        return "<h3>Logare cu succes!</h3>"

    # pentru get
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)