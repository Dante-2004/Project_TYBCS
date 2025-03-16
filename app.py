import requests
import psycopg2
import pandas as pd
import bcrypt
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, request, jsonify, render_template, redirect, session
import os

app = Flask(__name__)

# Set secret key for sessions
app.secret_key = os.urandom(24)

# Database connection settings
DB_SETTINGS = {
    "host": "localhost",
    "database": "moviesdb",
    "user": "postgres",
    "password": "2004"
}

# TMDb API Key and Base URLs
TMDB_API_KEY = "b3eb1222fee62dfa74a275ab01a6d357"  # Replace with your TMDb API key
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Function to fetch movie poster from TMDb
def fetch_movie_poster(movie_title):
    try:
        response = requests.get(
            TMDB_SEARCH_URL,
            params={"api_key": TMDB_API_KEY, "query": movie_title}
        )
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        
        # Check if results exist
        if data["results"]:
            poster_path = data["results"][0].get("poster_path")
            return f"{TMDB_POSTER_BASE_URL}{poster_path}" if poster_path else None

        return None  # Return None if no poster is found
    except Exception as e:
        print(f"Error fetching poster for {movie_title}: {e}")
        return None

# Connect to the database and fetch movie data
def fetch_movies():
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        query = "SELECT movie_id, title, overview, genres, keywords, tags FROM movies;"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Convert any NaN values to empty strings
        df = df.fillna("")

        # Convert all columns to string (to prevent NoneType errors)
        for col in ["overview", "genres", "keywords", "tags"]:
            df[col] = df[col].astype(str)

        # Debugging: Print the available columns
        print("Available columns in DataFrame:", df.columns.tolist())

        return df
    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if error occurs

# Generate recommendations (existing endpoint)
@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    if not data or "movie" not in data:
        return jsonify({"error": "Missing movie title in request body."}), 400

    movie_title = data["movie"]
    movies_df = fetch_movies()
    # Content-based recommendation using tags
    vectorizer = CountVectorizer(stop_words="english")
    count_matrix = vectorizer.fit_transform(movies_df["tags"])
    cosine_sim = cosine_similarity(count_matrix)

    try:
        idx = movies_df[movies_df["title"].str.lower() == movie_title.lower()].index[0]
    except IndexError:
        return jsonify({"error": "Movie not found in database."}), 404

    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    top_movies = []
    for i in sim_scores[1:11]:  # Get top 10 similar movies (skipping the first)
        movie_data = movies_df.iloc[i[0]]
        poster_url = fetch_movie_poster(movie_data["title"]) or "https://via.placeholder.com/200x300.png?text=No+Image"
        top_movies.append({
            "title": movie_data["title"],
            "overview": movie_data["overview"],
            "image_url": poster_url
        })

    return jsonify({"recommendations": top_movies}), 200

# Routes for login, index, registration (existing endpoints) ...
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/index.html", methods=["GET"])
def index():
    if not session.get("user_id"):
        return redirect("/")
    return render_template("index.html")

@app.route("/index.html", methods=["POST"])
def login_authenticate():
    email = request.form.get("email")
    password = request.form.get("password")
    
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor()
        cur.execute("SELECT id, email, password FROM users WHERE email = %s;", (email,))
        user = cur.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            return render_template("index.html")
        else:
            return render_template("login.html", error="Invalid email or password.")
    except Exception as e:
        print(f"Login error: {e}")
        return render_template("login.html", error="An error occurred during login.")

@app.route("/register.html", methods=["GET"])
def show_register():
    return render_template("register.html")

@app.route("/register.html", methods=["POST"])
def register_user():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s);", (username, email, hashed_password))
        conn.commit()
        conn.close()
        return redirect("/")
    except Exception as e:
        print(f"Registration error: {e}")
        return render_template("register.html", error="Registration failed. Try again.")

# ────────────────────────────────────────────────
# Updated Endpoint: Personalized Recommendations (based on mood)
# ────────────────────────────────────────────────
# Render the personalized recommendations page
@app.route("/personalized.html", methods=["GET"])
def personalized_page():
    return render_template("personalized.html")

# API endpoint for mood-based recommendations
@app.route("/api/personalized", methods=["POST"])
def personalized_api():
    data = request.get_json()
    mood = data.get("mood", "").lower().strip()

    if not mood:
        return jsonify({"error": "Mood not provided."}), 400

    try:
        movies_df = fetch_movies()

        # Debugging: Print the first few rows to check if genres, tags, and keywords exist
        print("DataFrame Preview:\n", movies_df.head())

        # Ensure necessary columns exist before filtering
        required_columns = ["tags", "genres", "keywords", "overview"]
        for col in required_columns:
            if col not in movies_df.columns:
                return jsonify({"error": f"Missing column: {col}"}), 500

        # Search for the mood in multiple columns
        filtered = movies_df[
            movies_df.apply(
                lambda x: (
                    mood in x["tags"].lower() or
                    mood in x["genres"].lower() or
                    mood in x["keywords"].lower() or
                    mood in x["overview"].lower()
                ), axis=1
            )
        ]

        if filtered.empty:
            return jsonify({"error": "No movies found for this mood."}), 404

        recommendations = []
        for _, row in filtered.head(10).iterrows():
            poster_url = fetch_movie_poster(row["title"]) or "https://via.placeholder.com/200x300.png?text=No+Image"
            recommendations.append({
                "title": row["title"],
                "overview": row["overview"],
                "image_url": poster_url
            })

        return jsonify({"recommendations": recommendations})
    
    except Exception as e:
        print(f"Error fetching personalized recommendations: {e}")
        return jsonify({"error": "Failed to fetch personalized recommendations."}), 500

# ────────────────────────────────────────────────
# New Endpoint: Top Trending Movies (using TMDb Trending API)
# ────────────────────────────────────────────────
# Render the trending page (HTML)
@app.route("/trending.html", methods=["GET"])
def trending_page():
    return render_template("trending.html")

# API endpoint to fetch trending movies (returns JSON)
# API endpoint to fetch trending movies (returns JSON)
@app.route("/api/trending", methods=["GET"])
def trending_api():
    try:
        trending_url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API_KEY}"
        response = requests.get(trending_url)
        if response.status_code != 200:
            # Log and return the status code error for debugging
            error_msg = f"Failed to fetch trending movies. Status code: {response.status_code}"
            print(error_msg)
            return jsonify({"error": error_msg}), response.status_code
        data = response.json()
        movies = data.get("results", [])[:10]
        recommendations = []
        for movie in movies:
            title = movie.get("title")
            overview = movie.get("overview", "No overview available.")
            poster_path = movie.get("poster_path")
            image_url = f"{TMDB_POSTER_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/200x300.png?text=No+Image"
            recommendations.append({
                "title": title,
                "overview": overview,
                "image_url": image_url
            })
        return jsonify({"recommendations": recommendations})
    except Exception as e:
        error_msg = f"Exception occurred: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
