from flask import Flask, request, jsonify, render_template
import pandas as pd
from flask_cors import CORS 
import psycopg2
import bcrypt
import dotenv
import os


app = Flask(__name__)
CORS(app)

dotenv.load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


conn = psycopg2.connect(
    dbname = DB_NAME,
    user = DB_USER, 
    password = DB_PASSWORD,
    host = DB_HOST,
    port = DB_PORT
)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/signup-page')
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods = ['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_str = hashed_password.decode('utf-8')  # convert to string for DB

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_str))
        conn.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        cursor.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        result = cursor.fetchone()

        if result:
            stored_hash = result[0].encode('utf-8')  # already in bytes (BYTEA)
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):  # ✅ compare with bytes
                return jsonify({'message': 'Login successful'}), 200
            else:
                return jsonify({'error': 'Invalid username or password'}), 401
        else:
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return jsonify({'error': 'Internal server error'}), 500

    finally:
        cursor.close()


user_movie_matrix = pd.read_csv('user_movie_matrix.csv', index_col=0)
movie_stats = pd.read_csv('movie_stats.csv', index_col=0)

@app.route('/recommend', methods=['GET'])
def recommend():
    title = request.args.get('title')
    num = request.args.get('num')
    num = int(num) if num and num.isdigit() else 5

    if title not in user_movie_matrix.columns:
        return jsonify({'error': 'Movie not found'}), 404

    movie_ratings = user_movie_matrix[title]
    similar_movies = user_movie_matrix.corrwith(movie_ratings)

    corr_df = pd.DataFrame(similar_movies, columns=['Correlation'])
    corr_df.dropna(inplace=True)
    corr_df = corr_df.join(movie_stats['count'])

    corr_df = corr_df.drop(index=title, errors='ignore')

    recommendations = corr_df[corr_df['count'] > 100].sort_values('Correlation', ascending=False)
    top_movies = list(recommendations.head(num).index)

    return jsonify(top_movies)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    matching_titles = [title for title in user_movie_matrix.columns if title.lower().startswith(query)]

    
    return jsonify(matching_titles[:10])


if __name__ == '__main__':
    app.run(debug=True)
