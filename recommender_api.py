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
print(f"[DB_URL] {DB_URL}")

conn = None
try:
    conn = psycopg2.connect(DB_URL, sslmode='require')
    conn.autocommit = True
    print("✅ Successfully connected to the database.")
except Exception as e:
    print("❌ Database connection error:", e)

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
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500

    data = request.get_json()
    print(f"[SIGNUP] Received data: {data}")

    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_str = hashed_password.decode('utf-8')

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_str))
        return jsonify({'message': 'User created successfully'}), 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        print("[SIGNUP ERROR] Username already exists.")
        return jsonify({'error': 'Username already exists'}), 400
    except Exception as e:
        conn.rollback()
        print(f"[SIGNUP ERROR] {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cursor.close()

@app.route('/login', methods=['POST'])
def login():
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500

    data = request.get_json()
    print(f"[LOGIN] Received data: {data}")

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        result = cursor.fetchone()

        if result:
            stored_hash = result[0].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                print("[LOGIN SUCCESS]")
                return jsonify({'message': 'Login successful'}), 200
            else:
                print("[LOGIN ERROR] Incorrect password.")
                return jsonify({'error': 'Invalid username or password'}), 401
        else:
            print("[LOGIN ERROR] Username not found.")
            return jsonify({'error': 'Invalid username or password'}), 401

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cursor.close()

# Recommendation system
user_movie_matrix = None
movie_stats = None

def load_data():
    global user_movie_matrix, movie_stats
    if user_movie_matrix is None or movie_stats is None:
        print("[DATA] Loading recommendation data...")
        user_movie_matrix = pd.read_csv('user_movie_matrix_updated.csv.gz', compression='gzip', index_col=0)
        movie_stats = pd.read_csv('movie_stats_updated.csv', index_col=0)
        print("[DATA] Recommendation data loaded.")

@app.route('/recommend', methods=['GET'])
def recommend():
    load_data()
    title = request.args.get('title')
    num = request.args.get('num')
    print(f"[RECOMMEND] Requested title: {title} | Count: {num}")
    
    num = int(num) if num and num.isdigit() else 5

    if title not in user_movie_matrix.columns:
        print(f"[RECOMMEND ERROR] Movie '{title}' not found.")
        return jsonify({'error': 'Movie not found'}), 404

    movie_ratings = user_movie_matrix[title]
    similar_movies = user_movie_matrix.corrwith(movie_ratings)

    corr_df = pd.DataFrame(similar_movies, columns=['Correlation'])
    corr_df.dropna(inplace=True)
    corr_df = corr_df.join(movie_stats['count'])
    corr_df = corr_df.drop(index=title, errors='ignore')

    recommendations = corr_df[corr_df['count'] > 100].sort_values('Correlation', ascending=False)
    top_movies = list(recommendations.head(num).index)

    print(f"[RECOMMEND] Top recommendations: {top_movies}")
    return jsonify(top_movies)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    load_data()
    query = request.args.get('q', '').lower()
    print(f"[AUTOCOMPLETE] Query: {query}")
    
    if not query:
        return jsonify([])

    matching_titles = [title for title in user_movie_matrix.columns if title.lower().startswith(query)]
    return jsonify(matching_titles[:10])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
