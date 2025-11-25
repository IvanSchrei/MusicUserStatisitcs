import os #für pfade und weiters
from flask import Flask, request, jsonify, g #Flask für API
from flask_cors import CORS #Cross Origin Ressource sharing
from dotenv import load_dotenv #.env variable
import sqlite3 #datenbank
import bcrypt #zum hashen des userpasswordes für die datenbank
from email_validator import validate_email, EmailNotValidError #zum checken und clearen der Email
import jwt #für jwt tokens (Json Web Token)
import datetime #für gultigkeitsdauer des JWT
from functools import wraps #für decorator

#Diese Bibliothek wird für OAuth2 gebraucht
from requests_oauthlib import oauth2_session

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask("3Legged_OAuth2_Example")
CORS(app)

#---------------Datenbank Methoden-----------------

#Methode, um Datenbank verbindung zu holen
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

#Methode, um Datenbank verbindung zu schließen
@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

#Methode, um Datenbank zu erstellen
def init_db():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY AUTOINCREMENT,
            uemail TEXT NOT NULL UNIQUE,
            upassword TEXT NOT NULL UNIQUE
        )
    ''')
    db.commit()
    db.close()

if not os.path.exists(DB_PATH):
    init_db()

#----------------Decorator------------------  

#Decorator Methode, die es erlaubt einen endpoint so zu verändern, dass er ein gültiges JWT token braucht
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if('Authorization' in request.headers):
            auth_header = request.headers['Authorization']
            try:
                #geht davon aus, dass das Jwt token so im Header der Request gesendet wird: Bearer ikjadlkjdlkfdjfksdjf
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify(error="Token is missing or invalid format"), 401
        if(not token):
            return jsonify(error="Token is missing"), 401
        
        #Übergebenen Token decodieren / validieren
        try:
            secret_key = os.environ.get("JWT_SECRET")
            data = jwt.decode(token, secret_key, algorithms="HS256")
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(*args, **kwargs)
    return decorated

#----------------API Endpoints------------------  

#Enpoint für User Login in Unsere Seite, bei erfolgreichem Login wird an Soundcloud Login weitergeleitet
@app.route("/api/login", methods=['POST'])
def login():
    if not request.is_json:
        return jsonify(error="Request must be JSON"), 415
    
    data = request.get_json()

    email = data.get("email")
    raw_password = data.get("password")

    cleaned_email = checkEmail(email)
    if(isinstance(cleaned_email, dict) or isinstance(cleaned_email, list)):
        return jsonify(error="Incorrect Email Format"), 400

    if(user_Exists(cleaned_email)):
        #Login
        if(checkPassword(raw_password, getUserPass(cleaned_email))):
            jwt_token = createJwt(cleaned_email)
            return jsonify(token=jwt_token), 200
    else:
        #Create user
        response = createUser(cleaned_email, raw_password)
        if(response[1] != 200):
            return jsonify(error="Failed to create User"), 400
        
        jwt_token = createJwt(cleaned_email)
        return jsonify(token=jwt_token), 200
        

#Endpoint den Soundcloud verwendet um zu Antworten
@app.route("/api/callback")
def callback():
    pass

#Endpoint, der verwendet wird, um Wrapped Daten abzufragen, dafür muss der User eingelogt sein und ein JWT haben
@app.route("/api/get-wrapped", methods = ['GET'])
@token_required
def get_wrapped():
    return jsonify(message="erfolgrech get-wrapped gecallt!"), 200

#----------------Utility------------------

#Methode, die überprüft ob der Benutzer bereits angelegt ist.
def user_Exists(email):
    db = get_db()
    c = db.cursor()
    query = 'SELECT uid FROM users WHERE uemail = ?'
    c.execute(query, (email, )) 
    row = c.fetchone()
    if(row):
        return True
    else:
        return False
    
#Methode, um einen neuen Benutzer anzulegen
def createUser(email, password):
    hashed_password = hashPassword(password)
    try:
        db = get_db()
        c = db.cursor()
        query = 'INSERT INTO users(uemail, upassword) VALUES(?, ?)'
        c.execute(query, (email, hashed_password))
        db.commit()
        return jsonify(message = "User created Successfully"), 200
    except sqlite3.Error:
        return jsonify(error = "Error creating User"), 400

#Methode, um Password des Benutzers zu hashen
def hashPassword(password):
    password_bytes = password.encode('utf-8')

    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password_bytes, salt)

    return hashed_password

#Methode, die das übergebene Password mit dem übergebenen Password Hash vergleicht
def checkPassword(given_pass, db_hash):
    password_bytes = given_pass.encode('utf-8')
    print("db_hash: ", db_hash, " type: " , type(db_hash))
    return bcrypt.checkpw(password_bytes, db_hash)

#Methode, die das Password des Benutzers mit der übergebenen Email holt
def getUserPass(email):
    try:
        db = get_db()
        c = db.cursor()
        query = "SELECT upassword FROM users WHERE uemail = ?"
        c.execute(query, (email, ))
        row = c.fetchone()
        print("userPass from DB: ", row)
        if(row):
            return row['upassword']
        else:
            print("error getting Users password from database")
            return jsonify(error = "Couldn't find User Password in DB")
    except sqlite3.Error as e:
        print("error getting Users password from database 2: ", e)
        return jsonify(error = "Error getting Users Password from DB")

#Methode, um Benutzereingabe zu überprüfen. Auch Strings bereinigen, um SQL-Injections zu vermeiden, true wenn alles richtig
def checkEmail(email):
    try:
        email_info = validate_email(email, check_deliverability=False)
        cleaned_email = email_info.normalized
        return cleaned_email
    except EmailNotValidError:
        return jsonify(error = "Invalid Email")

#Methode um ein Jwt Token mit der userEmail zu erstellen
def createJwt(email):

    payload = {
        'sub': email,
        'exp': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30))
    }

    secret_key = os.environ.get("JWT_SECRET")
    
    token = jwt.encode(payload,secret_key, algorithm='HS256')

    return token



#Main Methode
if __name__ == "__main__":
    #HTTPS ist normalerweise verpflichtend bei OAuth2, mit dieser Zeile deaktivieren
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True)