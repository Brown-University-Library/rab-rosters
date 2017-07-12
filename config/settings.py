import os

config = {
	'APP_ROOT' : os.path.abspath(__file__ + "/../../"),
	'RAB_QUERY_API': '',
	'ADMIN_EMAIL' : '',
	'ADMIN_PASS' : '',
	'THROTTLE' : 1
}

config['LOG_FILE'] = os.path.join(config['APP_ROOT'],
						'logs', 'roster-query.log')