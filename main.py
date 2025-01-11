import json
import google.generativeai as genai
import time
from datetime import datetime, timedelta
import random
import threading
import os
from dotenv import load_dotenv

load_dotenv()
api = os.getenv("API_KEY")
# Load AI users from JSON file with UTF-8 encoding
def load_users(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# Load emotions from JSON file with UTF-8 encoding
def load_emotions(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# Load tones from JSON file with UTF-8 encoding
def load_tones(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# Save data to a temporary database (JSON file) with UTF-8 encoding
def save_to_db(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Load data from a temporary database with UTF-8 encoding
def load_from_db(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Generate tweets with rate limiting
class APIRateLimiter:
    def __init__(self, max_per_minute, max_per_day):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self.requests_in_last_minute = 0
        self.total_requests_today = 0
        self.minute_reset_time = datetime.now() + timedelta(minutes=1)
        self.daily_reset_time = datetime.now() + timedelta(days=1)

    def check_limits(self):
        now = datetime.now()

        if now >= self.minute_reset_time:
            self.requests_in_last_minute = 0
            self.minute_reset_time = now + timedelta(minutes=1)

        if now >= self.daily_reset_time:
            self.total_requests_today = 0
            self.daily_reset_time = now + timedelta(days=1)

        if self.requests_in_last_minute >= self.max_per_minute:
            time_to_wait = (self.minute_reset_time - now).total_seconds()
            print(f"Rate limit reached! Waiting {time_to_wait:.2f} seconds...")
            time.sleep(time_to_wait)
        if self.total_requests_today >= self.max_per_day:
            raise Exception("Daily API request limit reached!")

    def log_request(self):
        self.requests_in_last_minute += 1
        self.total_requests_today += 1

rate_limiter = APIRateLimiter(max_per_minute=10, max_per_day=1000)

def generate_tweet(user, emotions, tones):
    rate_limiter.check_limits()
    username = user["username"]
    category = user["category"]
    interests = user["interests"]
    name = user["name"]

    # Randomly select emotion and tone
    selected_emotion = random.choice(emotions)
    selected_tone = random.choice(tones)

    prompt = f"""
    You are {username}, a {name}, classified under the {category} category. You are passionate about topics like {', '.join(interests)}.
    Right now, you're feeling {selected_emotion} and your tone is {selected_tone}.
    Compose a tweet that reflects your personality and mood. 
    Structure your tweet as follows:
    - Start with a catchy hook or statement.
    - Share a thought or reaction related to your interests.
    - End with a relatable or engaging closing, possibly with emojis or hashtags.
    """

    try:
        genai.configure(api_key=api, transport='rest')
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        tweet = response.text.strip()
        rate_limiter.log_request()
    except Exception as e:
        tweet = f"Failed to generate tweet for {username}: {str(e)}"
    
    return tweet

def generate_comment(user, tweet, tones):
    rate_limiter.check_limits()

    # Randomly select tone for comment
    selected_tone = random.choice(tones)

    prompt = f"""
    {user['username']} saw this tweet: "{tweet}". Write a {selected_tone} comment that reflects {user['username']}'s i.e {user['name']} pokemon personality.
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        comment = response.text.strip()
        rate_limiter.log_request()
    except Exception as e:
        comment = f"Failed to generate comment: {str(e)}"
    return comment

# Run tweeting in a separate thread
def tweeting(users, emotions, tones, tweets_db):
    while True:
        for user in users:
            if random.random() < 0.3:  # Adjust tweet probability
                tweet = generate_tweet(user, emotions, tones)
                if "Failed to generate tweet" not in tweet:  # Only proceed if generation was successful
                    tweets_db.insert(0, {
                        "user": user["username"],
                        "name": user["name"],  # Add user's name
                        "tweet": tweet,
                        "timestamp": str(datetime.now()),
                        "comments": []
                    })
                    save_to_db("tweets_db.json", tweets_db)
                    print(f"{user['username']} tweeted: {tweet}")
                else:
                    print(f"Skipping tweet for {user['username']} due to failure.")
                time.sleep(random.uniform(1, 3))  # Control tweet frequency

# Run commenting in a separate thread
def commenting(users, tweets_db, tones):
    while True:
        if tweets_db:  # Ensure there are tweets to comment on
            for user in users:
                sampled_tweets = random.sample(tweets_db, min(5, len(tweets_db)))
                for tweet_data in sampled_tweets:
                    if user["username"] != tweet_data["user"] and random.random() < 0.2:
                        comment = generate_comment(user, tweet_data["tweet"], tones)
                        if "Failed to generate comment" not in comment:  # Only proceed if generation was successful
                            tweet_data["comments"].append({
                                "commenter": user["username"],
                                "name": user["name"],  # Add user's name
                                "comment": comment,
                                "timestamp": str(datetime.now())
                            })
                            save_to_db("tweets_db.json", tweets_db)
                            print(f"{user['username']} commented on {tweet_data['user']}'s tweet: {comment}")
                        else:
                            print(f"Skipping comment for {user['username']} due to failure.")
                        time.sleep(random.uniform(1, 3))  # Control comment frequency

# Start threads for tweeting and commenting
def run_simulation(users, emotions, tones):
    tweets_db = load_from_db("tweets_db.json")
    print("Simulation running... Press Ctrl+C to stop.")

    tweet_thread = threading.Thread(target=tweeting, args=(users, emotions, tones, tweets_db), daemon=True)
    comment_thread = threading.Thread(target=commenting, args=(users, tweets_db, tones), daemon=True)

    tweet_thread.start()
    comment_thread.start()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Simulation stopped by user.")


users = load_users("pokemon_users.json")
emotions = load_emotions("emotions.json")
tones = load_tones("tones.json")
run_simulation(users, emotions, tones)