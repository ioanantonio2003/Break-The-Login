from flask import Flask, request, render_template,make_response, redirect, url_for
import sqlite3
import time

app = Flask(__name__)

tokens = {}

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

        #aici creem cookiul dar foarte slab
        raspuns = make_response(redirect(url_for('dashboard')))
        raspuns.set_cookie('AuthX_USER', email) # cookie slab
        return raspuns

    # pentru get
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # verificam daca utiilziatorul are cookie-ul din sesiune
    user_email = request.cookies.get('AuthX_USER')
    
    #daca nu l are il trimitem la login
    if not user_email:
        return redirect(url_for('login'))
        
    return render_template('dashboard.html')


@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = connect_to_database()

        #verificam daca exista emailul in baza de date
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user:
            # token predicitibil -> timpul curent 
            token = str(int(time.time()))
            tokens[token] = email #adaugam token pt email respectiv care nu expira niciodata si e reutilizabil
            
            link = f"http://127.0.0.1:5000/reset/{token}"
            return f"<h3>Token trimis!</h3><p>Intra pe link-ul: <a href='{link}'>{link}</a></p>"
        else:
            return "<h3>Eroare: EMailul nu exista</h3><a href='/forgot'>Inapoi</a>"

    #pt get        
    return render_template('forgot.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # veririfcam daca token ul exista
    if token not in tokens:
        return "<h3>Eroare: Token gresit!</h3>"
        
    email = tokens[token]

    if request.method == 'POST':
        new_password = request.form['new_password']
        
        conn = connect_to_database()

        #actuliazam parola
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_password, email))
        conn.commit()
        conn.close()
        
        #dupa ce token-ul a fost utilizat nu il stergem in dictionar
        return "<h3>Parola resetata</h3><a href='/login'>Login</a>"
        
    return render_template('reset.html', token=token)



if __name__ == '__main__':
    app.run(debug=True)