from flask import request, jsonify
from app import app

import os
import json

rosters_dir = os.path.join(app.config['APP_ROOT'], 'app/rosters')

@app.route('/')
def root():
	return '<h1>Roster feed is live</h1>'

@app.route('/rosters/<org_id>/')
def roster(org_id):
	with open(os.path.join( rosters_dir, org_id + '.json' ), 'r') as f:
		roster_data = json.load(f)
	return jsonify(roster_data)