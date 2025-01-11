from flask import Flask, jsonify, request
import json
from flask_cors import CORS

# Load JSON data
JSON_FILE = 'tweets_db.json'

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def load_json_data():
    with open(JSON_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

# Endpoint with pagination
@app.route('/api', methods=['GET'])
def get_paginated_data():
    data = load_json_data()  # Reload data dynamically

    # Get pagination parameters
    page = request.args.get('page', default=1, type=int)  # Default to page 1
    limit = request.args.get('limit', default=10, type=int)  # Default to limit 10

    # Calculate start and end indices for slicing
    start = (page - 1) * limit
    end = start + limit

    # Slice the data for the given page
    paginated_data = data[start:end]

    # Include metadata in the response
    response = {
        "page": page,
        "limit": limit,
        "total_items": len(data),
        "total_pages": (len(data) + limit - 1) // limit,  # Calculate total pages
        "data": paginated_data,
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
