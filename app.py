from flask import Flask, request, render_template,make_response, redirect, url_for
import sqlite3
import time
import re
import bcrypt
import secrets

app = Flask(__name__)

tokens = {}
incercari = {}
maxim = 3

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

        #parola trebuie sa aibe cel putin 8 caractere, o litera mica, o litera mare si o cifra .
        if len(password) < 8 or not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password) or not re.search(r"[0-9]", password):
            return "<h3>Eroare: Parola prea slaba!</h3><a href='/register'>Inapoi</a>"

        #hash-uim parola
        password_in_bytes = password.encode('utf-8')
        
        # creem has-ul
        salt = bcrypt.gensalt()
        parola_hashuita = bcrypt.hashpw(password_in_bytes, salt)

        conn = connect_to_database()
        try:
         #inseram utilizatorul in baza de date
            conn.execute('INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)', (email, parola_hashuita.decode('utf-8'), 'USER'))
            conn.commit()
            conn.close()
            return "<h3>Cont creat cu succes!</h3><a href='/register'>Inapoi</a>"
        except sqlite3.IntegrityError:
            # singura problema de inserare ar fi daca emailul exista deja (UNIQUE)
            conn.close()
            return "<h3>Eroare: Email deja existent!</h3><a href='/register'>Inapoi</a>"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = connect_to_database()
        
        #verificam daca exista in tabela users un user cu acest email
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        # aici daca emailul nu exista zicem ca nu exista
        if user is None:
            return "<h3>Eroare: Logare invalida sau cont blocat!</h3><a href='/login'>Incearca din nou</a>"
        
        #daca emailul a fost incercat de 3 ori il blocam
        if user and user['locked']:
            conn.close()
            return "<h3>Eroare: Logare invalida sau cont blocat!</h3><a href='/login'>Incearca din nou</a>"

        if user:
            password_in_bytes = password.encode('utf-8')
            parola_hashuita = user['password_hash'].encode('utf-8')
            
            #vedem daca parolele sunt la fel
            if bcrypt.checkpw(password_in_bytes, parola_hashuita):
                incercari[email] = 0
                
               
                 #aici creem cookiul 

                raspuns = make_response(redirect(url_for('dashboard')))
                raspuns.set_cookie(
                    'AuthX_USER', 
                    email, 
                    httponly=True,      
                    samesite='Strict',  
                    max_age=3600        
                )

                conn.execute('''
                    INSERT INTO audit_logs (user_id, action, resource, ip_address) 
                    VALUES (?, ?, ?, ?)
                ''', (user['id'], 'LOGIN', 'authentification', request.remote_addr))
                conn.commit()

                conn.close()
                return raspuns
            else:
                #daca parola e gresit numarul de incercari creste
                incercari[email] = incercari.get(email, 0) + 1
                
                #blocam contul
                if incercari[email] >= maxim:
                    conn.execute('UPDATE users SET locked = 1 WHERE email = ?', (email,))
                    conn.commit()

                conn.close()

                return "<h3>Eroare: Logare invalida sau cont blocat!</h3><a href='/login'>Incearca din nou</a>"

    # pentru get
    return render_template('login.html')

@app.route('/dashboard',methods=['GET', 'POST'])
def dashboard():
    # verificam daca utiilziatorul are cookie-ul din sesiune
    user_email = request.cookies.get('AuthX_USER')
    
    #daca nu l are il trimitem la login
    if not user_email:
        return redirect(url_for('login'))
    conn = connect_to_database()
    
    #obtinem id-ul utilizatorului din sesiune
    user = conn.execute('SELECT id FROM users WHERE email = ?', (user_email,)).fetchone()
        
    id = user['id']

    # pt formularul de trimitere tiket
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        severity = request.form['severity']
        
        conn.execute('''
            INSERT INTO tickets (title, description, severity, status, owner_id) VALUES (?, ?, ?, ?, ?)
        ''', (title, description, severity, 'OPEN', id))
        conn.commit()
        
        conn.execute('''
            INSERT INTO audit_logs (user_id, action, resource) 
            VALUES (?, ?, ?)
        ''', (id, 'CREATE_TICKET', 'ticket'))
        conn.commit()
        return redirect(url_for('dashboard'))

    
    tickets = conn.execute('SELECT * FROM tickets WHERE owner_id = ?', (id,)).fetchall()
    conn.close()
        
    return render_template('dashboard.html', tickets = tickets)


@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = connect_to_database()

        #verificam daca exista emailul in baza de date
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user:
            t = secrets.token_urlsafe(32)
            
            #expira in 5 min
            expira = time.time() + 300
            
            tokens[t] = {'email': email, 'expira': expira}
            
            link = f"http://127.0.0.1:5000/reset/{t}"
            return f"<h3>Token trimis!!</h3><p>Expira in 5 min : <a href='{link}'>{link}</a></p>"
        else:
            return "<h3>Eroare: EMailul nu exista</h3><a href='/forgot'>Inapoi</a>"

    #pt get        
    return render_template('forgot.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # veririfcam daca token ul exista
    if token not in tokens:
        return "<h3>Eroare: Token gresit!</h3>"
        
    token_data = tokens[token]

    # vedem daca token-ul este expirat
    if time.time() > token_data['expira']:
        del tokens[token] 
        return "<h3>Eroare: Token expirat.</h3>"

    email = token_data['email']

    if request.method == 'POST':
        new_password = request.form['new_password']
        
        # aaceasi regula ca la parola de inregistrare
        if len(new_password) < 8 or not re.search(r"[a-z]", new_password) or not re.search(r"[A-Z]", new_password) or not re.search(r"[0-9]", new_password):
            return "<h3>Eroare: Parola prea slaba!</h3><a href='/register'>Inapoi</a>"
        
        # hashuim parola
        password_in_bytes = new_password.encode('utf-8')
        salt = bcrypt.gensalt()
        parola_hashuita = bcrypt.hashpw(password_in_bytes, salt)
        
        conn = connect_to_database()
        conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (parola_hashuita.decode('utf-8'), email))
        conn.commit()
        conn.close()
        
        del tokens[token]
        
        return "<h3>Parola resetata!</h3><a href='/login'>Mergi la Login</a>"
        
    return render_template('reset.html', token=token)


@app.route('/logout')
def logout():
    raspuns = make_response(redirect(url_for('login')))
    raspuns.set_cookie('AuthX_USER', '', expires=0, httponly=True, samesite='Strict')
    return raspuns

@app.errorhandler(Exception)
def handle_exception(e):

    return "<h3>EROARE</h3>"



if __name__ == '__main__':
    app.run(debug=True)