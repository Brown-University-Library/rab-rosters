from flask import request, jsonify
from app import app

import os

@app.route('/')
def root():
	return '<h1>Roster feed is live</h1>'

@app.route('/<org_id>/')
def roster(org_id):
	with open(os.path.join( 'rosters', org_id + '.json' ), 'r') as f:
		roster_data = json.load(f)
	return jsonify(roster_data)