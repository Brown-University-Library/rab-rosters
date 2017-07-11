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

prp_map = {
    '@id': 'url',
    'http://xmlns.com/foaf/0.1/firstName' : 'first',
    'http://xmlns.com/foaf/0.1/lastName' : 'last',
    'http://vivoweb.org/ontology/core#middleName' : 'middle',
    'http://temporary.name.space/fullName' : 'full',
    'http://vivoweb.org/ontology/core#preferredTitle' : 'title',
    'http://vivoweb.org/ontology/core#primaryEmail' : 'email',
    'http://temporary.name.space/fullImage' : 'image',
    'http://temporary.name.space/image' : 'thumbnail',
    'http://vivoweb.org/ontology/core#overview' : 'overview',
    'http://temporary.name.space/affiliations' : 'affiliations',
    'http://temporary.name.space/researchArea' : 'topics',
    'http://temporary.name.space/researchGeo' : 'countries',
    'http://vivoweb.org/ontology/core#educationalTraining' : 'education',
    'http://temporary.name.space/eduOrg' : 'organization',
    'http://temporary.name.space/degreeTitle' :'degree',
    'http://vivo.brown.edu/ontology/vivo-brown/degreeDate' : 'year'
}

def mint_roster_obj():
    return {
        'url' : '',
        'first' : '',
        'last' : '',
        'middle' : '',
        'full' : '',
        'title' : '',
        'email' : '',
        'image' : 'https://vivo.brown.edu',
        'thumbnail' : 'https://vivo.brown.edu',
        'overview' : '',
        'affiliations' : [],
        'topics' : [],
        'countries' : [],
        'education' : []
    }


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
                tmp:fullName ?name ;
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
                tmp:degreeTitle ?degree .
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
		return []

def extract_education_data(dataList):
    edu_map = {}
    del_index = []
    for i, data in enumerate(dataList):
        try:
            type_data = data['@type']
        except:
            del_index.append(i)
        if 'http://vivoweb.org/ontology/core#EducationalTraining' in type_data:
            del_index.append(i)
            edu_map[data['@id']] = data
        else:
            continue
    newList = [ data for i, data in enumerate(dataList) if i not in del_index ]
    return ( newList, edu_map )

def cast_edu_data(data):
    out = {}
    for k, v in data.items():
        if k in ('@id', '@type'):
            continue
        else:
            alias = prp_map[k]
            for obj in v:
                out[alias] = obj['@value']
    return out

def cast_roster_data(data, edu_map):
    out = mint_roster_obj()
    for k, v in data.items():
        if k == '@type':
            continue
        alias = prp_map[k]
        if alias == 'education':
            for eduId in v:
                eduObj = edu_map[eduId['@id']]
                edu_cast = cast_edu_data(eduObj)
                out[alias].append(edu_cast)
        elif alias == 'url':
            out[alias] += v
        elif alias in ( 'affiliations','topics','countries' ):
            for obj in v:
                out[alias].append(obj['@value'])
        elif alias in ( 'first','last','middle','title', 'full',
                        'email','image','thumbnail','overview'):
            for obj in v:
                out[alias] += obj['@value']
        else:
            raise Exception(k)
    return out

def main(org_uri):
    # org_uri = 'http://vivo.brown.edu/individual/org-brown-univ-dept56'
    roster_resp = query_roster(org_uri)
    roster_list, edu_map = extract_education_data(roster_resp)
    roster_data = []
    for prsn in roster_list:
        prsn_data = cast_roster_data(prsn, edu_map)
        roster_data.append(prsn_data)
	with open(os.path.join('app/data/rosters',org_uri[33:]+'.json'), 'w') as f:
		json.dump(roster_data, f, indent=2, sort_keys=True)

if __name__ == "__main__":
	org_uri = sys.argv[1]
	main(org_uri)