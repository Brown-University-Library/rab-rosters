from app import app

import requests
import csv

query_url = app.config['RAB_QUERY_API']

with open('data/org_ids.csv','rb') as f:
	dept_ids = []
	rdr = csv.reader(f)
	for row in rdr:
		dept_ids.append(row)