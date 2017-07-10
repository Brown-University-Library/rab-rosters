from app import app

import requests
import csv
import os
import sys
import json

query_url = app.config['RAB_QUERY_API']
email = app.config['ADMIN_EMAIL']
passw = app.config['ADMIN_PASS']

with open('app/data/org_ids.csv','rb') as f:
	dept_ids = []
	rdr = csv.reader(f)
	for row in rdr:
		dept_ids.append(row)

def query_roster(org_uri):
	query = """
		PREFIX rdf:		<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
		PREFIX rdfs:	<http://www.w3.org/2000/01/rdf-schema#>
		PREFIX blocal:	<http://vivo.brown.edu/ontology/vivo-brown/>
		PREFIX foaf:	<http://xmlns.com/foaf/0.1/>
		PREFIX vitro:	<http://vitro.mannlib.cornell.edu/ns/vitro/public#>
		PREFIX vivo:	<http://vivoweb.org/ontology/core#>
		PREFIX tmp:		<http://temporary.name.space/>
        CONSTRUCT {{
            ?subject a vivo:FacultyMember ;
                #label, first, last, email required
                rdfs:label ?name ;
                foaf:firstName ?first ;
                foaf:lastName ?last ;
                vivo:middleName ?middle ;
                vivo:preferredTitle ?title ;
                vivo:primaryEmail ?email ;
                vivo:overview ?overview ;
                vivo:educationalTraining ?edu ;
                #pseudo-properties
                tmp:image ?photo ;
                tmp:fullImage ?miURL ;
                tmp:affiliations ?orgName ;
                tmp:degreeStr ?degreeStr;
                tmp:researchArea ?raName ;
                tmp:researchGeo ?countryName .
            ?edu a vivo:EducationalTraining ;
            	blocal:degreeDate ?degreeDate;
            	tmp:eduOrg ?eduLabel ;
                rdfs:label ?degree .
        }}
        WHERE {{
            #required - label, first, last
            {{
            ?subject blocal:hasAffiliation <{0}> ;
            	a vivo:FacultyMember ;
                rdfs:label ?name ;
                foaf:firstName ?first ;
                foaf:lastName ?last .
            }}
            #optional - middle name
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vivo:middleName ?middle .
            }}
            #optional - title
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vivo:preferredTitle ?title .
            }}
            #optional - email
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vivo:primaryEmail ?email .
            }}
            #optional - overview
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vivo:overview ?overview .
            }}
            #optional - affiliations
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	blocal:hasAffiliation ?org .
                ?org rdfs:label ?orgName .
            }}
            #optional - education
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vivo:educationalTraining ?edu .
                ?edu a vivo:EducationalTraining ;
                	blocal:degreeDate ?degreeDate;
                	vivo:trainingAtOrganization ?eduOrg;
                    rdfs:label ?degree .
                ?eduOrg rdfs:label ?eduLabel .
            }}
            #optional - research areas
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vivo:hasResearchArea ?ra .
                ?ra a blocal:ResearchArea ;
                    rdfs:label ?raName .
            }}
            #optional - research country
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	blocal:hasGeographicResearchArea ?country .
                ?country a blocal:Country ;
                    rdfs:label ?countryName .
            }}
            #optional - photos
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                	vitro:mainImage ?mi .
                #main image
                ?mi vitro:downloadLocation ?miDl .
                ?miDl vitro:directDownloadUrl ?miURL .
                #thumbnail
                ?mi vitro:thumbnailImage ?ti .
                ?ti vitro:downloadLocation ?dl .
                ?dl vitro:directDownloadUrl ?photo .
            }}
        }}
	""".format(org_uri)
	headers = {'Accept': 'application/json', 'charset':'utf-8'}	
	data = { 'email': email, 'password': passw, 'query': query }
	resp = requests.post(query_url, data=data, headers=headers)
	if resp.status_code == 200:
		return resp.json()
	else:
		return {}

def main(org_uri):
	# org_uri = 'http://vivo.brown.edu/individual/org-brown-univ-dept56'
	roster_resp = query_roster(org_uri)
	with open(os.path.join('app/data/rosters',org_uri[33:]+'.json'), 'w') as f:
		json.dump(roster_resp, f, indent=2, sort_keys=True)

if __name__ == "__main__":
	org_uri = sys.argv[1]
	main(org_uri)