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

DB_URL = os.getenv("DB_URL")

def get_db_connection():
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        print(f"[ERROR] Could not connect to database: {e}")
        return None

try:
    user_movie_matrix = pd.read_csv('user_movie_matrix_updated.csv.gz', compression='gzip', index_col=0)
    movie_stats = pd.read_csv('movie_stats_updated.csv', index_col=0)
except FileNotFoundError:
    user_movie_matrix = pd.DataFrame()
    movie_stats = pd.DataFrame()
    print("[WARNING] CSV files not found. Recommend and autocomplete will not work.")

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/signup-page')
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_str = hashed_password.decode('utf-8')  # Convert to string for DB

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

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
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        result = cursor.fetchone()

        if result:
            stored_hash = result[0].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
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
        conn.close()

@app.route('/recommend', methods=['GET'])
def recommend():
    if user_movie_matrix.empty:
        return jsonify({'error': 'Recommendation system unavailable'}), 503

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
    if user_movie_matrix.empty:
        return jsonify([])

    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    matching_titles = [title for title in user_movie_matrix.columns if title.lower().startswith(query)]
    return jsonify(matching_titles[:10])

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

