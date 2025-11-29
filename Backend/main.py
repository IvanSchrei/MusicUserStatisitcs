import os #für pfade und weiters
from flask import Flask, request, jsonify, g, current_app #Flask für API
from flask_cors import CORS #Cross Origin Ressource sharing
from dotenv import load_dotenv #.env variable
import bcrypt #zum hashen des userpasswordes für die datenbank
from email_validator import validate_email, EmailNotValidError #zum checken und clearen der Email
import jwt #für jwt tokens (Json Web Token)
import datetime #für gultigkeitsdauer des JWT
from functools import wraps #für decorator
import psycopg2 #für Datenbank Connection (PostgreSQL auf Neon gehostet)
from psycopg2.extras import RealDictCursor
import time #zum überprüfen, ob spotify auth token noch gültig ist

#Diese Bibliothek wird für OAuth2 gebraucht
from requests_oauthlib import OAuth2Session

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

DATABASE_URL = os.environ.get("DATABASE_URL")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

app = Flask("3Legged_OAuth2_Example")
CORS(app)

#---------------Datenbank Methoden-----------------

#Methode, um Datenbank verbindung zu holen
def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(DATABASE_URL, sslmode='require')
    return g.db

#Methode, um Datenbank verbindung zu schließen
@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

#Methode, um Datenbank zu erstellen
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid SERIAL PRIMARY KEY,
            uemail TEXT NOT NULL UNIQUE,
            upassword TEXT NOT NULL,
            uoauth_access_token TEXT,
            uoauth_refresh_token TEXT,
            uoauth_expires_at REAL
        )
    ''')
    
    conn.commit()
    conn.close()

with app.app_context():
    init_db()

#----------------Decorators------------------  


#Decorator Methode, die es erlaubt einen endpoint so zu verändern, dass er ein gültiges JWT token braucht
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if('Authorization' in request.headers):
            auth_header = request.headers['Authorization']
            try:
                #geht davon aus, dass das Jwt token so im Header der Request gesendet wird: "Bearer ikjadlkjdlkfdjfksdjf"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify(error="Token is missing or invalid format"), 401
        if(not token):
            return jsonify(error="Token is missing"), 401
        
        #Übergebenen Token decodieren / validieren
        try:
            secret_key = os.environ.get("JWT_SECRET")
            data = jwt.decode(token, secret_key, algorithms="HS256")
            current_user_email = data.get("sub")
            print("data: ", data)
            print("current user: ", current_user_email)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(current_user=current_user_email, *args, **kwargs)
    return decorated

#Decorator, der dafür sorgt, dass Spotify token übergeben werden muss
def spotify_client_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user:
            return jsonify(error="User context missing"), 401

        token_info = get_user_spotify_tokens(current_user)
        
        if not token_info:
            return jsonify(error="Spotify account not linked. Please authorize via /api/spotify/link first."), 403

        #schaune ob token noch aktiv, 60 sekunden buffer
        if time.time() > (token_info['expires_at'] - 60):
            print(f"Token for {current_user} expired. Refreshing...")
            
            extra = {
                'client_id': SPOTIFY_CLIENT_ID,
                'client_secret': SPOTIFY_CLIENT_SECRET,
            }

            spotify = OAuth2Session(SPOTIFY_CLIENT_ID, token=token_info)
            
            try:
                #Token refreshen
                new_token = spotify.refresh_token(
                    token_url="https://accounts.spotify.com/api/token",
                    refresh_token=token_info['refresh_token'],
                    **extra
                )
                
                #neuen Token in DB speichern
                if 'refresh_token' not in new_token:
                    new_token['refresh_token'] = token_info['refresh_token']
                
                saveTokensToDB(current_user, new_token)

                token_info = new_token
                
            except Exception as e:
                print("Error refreshing token:", e)
                return jsonify(error="External authorization expired. Please link Spotify again."), 401

        spotify_client = OAuth2Session(SPOTIFY_CLIENT_ID, token=token_info)

        return f(spotify_client=spotify_client, *args, **kwargs)

    return decorated

#----------------API Endpoints------------------  

@app.route("/api/register", methods=['POST'])
def register():
    if not request.is_json:
        return jsonify(error="Request must be JSON"), 415
    
    data = request.get_json()

    email = data.get("email")
    raw_password = data.get("password")

    cleaned_email = checkEmail(email)
    if(cleaned_email == None):
        return jsonify(error="Incorrect Email Format"), 400
    
    response = createUser(cleaned_email, raw_password)
    if(not response):
        return jsonify(error = "Failed to create new User"), 400
    return jsonify(message = "User created successfully"), 200

#Enpoint für User Login in Unsere Seite, bei erfolgreichem Login wird an Soundcloud Login weitergeleitet
@app.route("/api/login", methods=['POST'])
def login():
    if not request.is_json:
        return jsonify(error="Request must be JSON"), 415
    
    data = request.get_json()

    email = data.get("email")
    raw_password = data.get("password")

    cleaned_email = checkEmail(email)
    if(cleaned_email == None):
        return jsonify(error="Incorrect Email Format"), 400

    if(user_Exists(cleaned_email)):
        #Login
        userpass = getUserPass(cleaned_email)
        if(userpass == None):
            return jsonify(error="Error getting User Password from DB"), 400
        if(checkPassword(raw_password, userpass)):
            jwt_token = createJwt(cleaned_email)
            return jsonify(token=jwt_token), 200
    else:
        #User existiert nicht
        return jsonify(error="User with this email doesn't exist, maybe try creating one if you haven't already"), 400

#TODO
#Enpoint um Spotify Link an Frontend zu senden
@app.route("/api/spotify/link")
@token_required
def get_spotify_link(current_user):
    redirect_uri = "https://remarkable-custard-0d3bbf.netlify.app/content.html"
    spotify_session = OAuth2Session(SPOTIFY_CLIENT_ID, redirect_uri=redirect_uri, scope=['user-top-read'])
    authorization_url, state = spotify_session.authorization_url("https://accounts.spotify.com/authorize")
    return jsonify(url = authorization_url), 200

#Endpoint um code aus dem Frontend, gegen Authtoken von Spotify auszutauschen
@app.route("/api/callback", methods = ['POST'])
@token_required
def callback(current_user):
    if not request.is_json:
        return jsonify(error="Request must be JSON"), 415
    
    data = request.get_json()
    code = data.get("code")

    if not code:
        return jsonify(error="No code provided"), 400
    
    redirect_uri = "https://remarkable-custard-0d3bbf.netlify.app/content.html"

    spotify_session = OAuth2Session(SPOTIFY_CLIENT_ID, redirect_uri=redirect_uri)

    try:
        token_data = spotify_session.fetch_token(
            token_url="https://accounts.spotify.com/api/token",
            client_secret=SPOTIFY_CLIENT_SECRET,
            code=code
        )
    except Exception as e:
        return jsonify(error = "Failed to get Spotify's Auth token")
    
    saveTokensToDB(current_user, token_data)

    return jsonify(message = "Spotify Auth token successfully saved to Backend.")


#Endpoint, der verwendet wird, um Wrapped Daten abzufragen, dafür muss der User eingelogt sein und ein JWT haben
@app.route("/api/get-wrapped", methods = ['GET'])
@token_required
@spotify_client_required
def get_wrapped(current_user, spotify_client):
    try:
        response = spotify_client.get("https://api.spotify.com/v1/me/top/tracks?limit=5")
        
        if response.status_code != 200:
            return jsonify(error="Failed to fetch data from Spotify", details=response.json()), response.status_code

        data = response.json()
        return jsonify(message="Success", data=data), 200
        
    except Exception as e:
        return jsonify(error=str(e)), 500

#----------------Utility------------------

#Methode, die überprüft ob der Benutzer bereits angelegt ist.
def user_Exists(email):
    db = get_db()
    c = db.cursor()
    query = 'SELECT uid FROM users WHERE uemail = %s'
    c.execute(query, (email, )) 
    row = c.fetchone()
    c.close()
    if row:
        return True
    else:
        return False
    
#Methode, um einen neuen Benutzer anzulegen
def createUser(email, password):
    hashed_password = hashPassword(password)
    try:
        db = get_db()
        c = db.cursor()
        query = 'INSERT INTO users(uemail, upassword) VALUES(%s, %s)'
        c.execute(query, (email, hashed_password))
        db.commit()
        c.close()
        return True
    except psycopg2.Error as e:
        # Important: If an error occurs, you must rollback 
        db.rollback()
        return False

#Methode, um Password des Benutzers zu hashen
def hashPassword(password):
    password_bytes = password.encode('utf-8')

    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password_bytes, salt)
    hashed_password_string = hashed_password.decode('utf-8')
    return hashed_password_string

#Methode, die das übergebene Password mit dem übergebenen Password Hash vergleicht
def checkPassword(given_pass, db_hash):
    password_bytes = given_pass.encode('utf-8')
    db_hash_bytes = db_hash.encode('utf-8')
    return bcrypt.checkpw(password_bytes, db_hash_bytes)

#Methode, die das Password des Benutzers mit der übergebenen Email holt
def getUserPass(email):
    try:
        db = get_db()
        c = db.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT upassword FROM users WHERE uemail = %s"
        c.execute(query, (email, ))
        row = c.fetchone()
        c.close()
        
        if row:
            return row['upassword']
        else:
            return None
    except psycopg2.Error:
        return None

#Methode, um Benutzereingabe zu überprüfen. Auch Strings bereinigen, um SQL-Injections zu vermeiden, true wenn alles richtig
def checkEmail(email):
    try:
        email_info = validate_email(email, check_deliverability=False)
        cleaned_email = email_info.normalized
        return cleaned_email
    except EmailNotValidError:
        return None

#Methode um ein Jwt Token mit der userEmail zu erstellen
def createJwt(email):

    payload = {
        'sub': email,
        'exp': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30))
    }

    secret_key = os.environ.get("JWT_SECRET")
    
    token = jwt.encode(payload,secret_key, algorithm='HS256')

    return token

def saveTokensToDB(user_email, token_data):
    db = get_db()
    c = db.cursor()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    expires_at = datetime.datetime.now().timestamp() + token_data.get('expires_in', 3600)

    query = """
        UPDATE users
        SET uoauth_access_token = %s,
            uoauth_refresh_token = %s,
            uoauth_expires_at = %s
        WHERE uemail = %s
    """

    try:
        c.execute(query, (access_token, refresh_token, expires_at, user_email))
        db.commit()
    except Exception as e:
        print("DB error saving spotify auth tokens: ", e)
        db.rollback()
    finally:
        c.close()
    
def get_user_spotify_tokens(user_email):
    try:
        db = get_db()
        c = db.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT uoauth_access_token, uoauth_refresh_token, uoauth_expires_at 
            FROM users WHERE uemail = %s
        """
        c.execute(query, (user_email, ))
        row = c.fetchone()
        c.close()

        if not row or not row['uoauth_access_token']:
            return None
            
        return {
            'access_token': row['uoauth_access_token'],
            'refresh_token': row['uoauth_refresh_token'],
            'expires_at': row['uoauth_expires_at'],
            'token_type': 'Bearer'
        }
    except psycopg2.Error as e:
        print("DB Error:", e)
        return None

#Main Methode
if __name__ == "__main__":
    app.run(debug=True)