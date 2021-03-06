import requests
import csv
import os
import sys
import json
import argparse
import time
import logging
import logging.handlers

from config import settings

query_url = settings.config['RAB_QUERY_API']
email = settings.config['ADMIN_EMAIL']
passw = settings.config['ADMIN_PASS']
log_file = settings.config['LOG_FILE']
throttle = settings.config['THROTTLE']

logger = logging.getLogger(__name__)
handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=100000, backupCount=2)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')

logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)


attrMap = {
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
    'http://vivo.brown.edu/ontology/vivo-brown/degreeDate' : 'year',
    'http://temporary.name.space/facultyTitle' :'faculty_title',
    'http://temporary.name.space/adminTitle' :'admin_title'
}

def mint_roster_obj():
    return {
        'url' : '',
        'first' : '',
        'last' : '',
        'middle' : '',
        'full' : '',
        'title' : '',
        'title_detail' : {},
        'email' : '',
        'image' : '',
        'thumbnail' : '',
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
            ?subject a vivo:FacultyMember,
                blocal:BrownThing ;
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
                tmp:image ?thumb ;
                tmp:fullImage ?photo ;
                tmp:affiliations ?orgName ;
                tmp:degreeStr ?degreeStr;
                tmp:researchArea ?raName ;
                tmp:researchGeo ?countryName ;
                tmp:facultyTitle ?facultyTitle ;
                tmp:adminTitle ?adminTitle .
            ?edu a vivo:EducationalTraining ;
                blocal:degreeDate ?degreeDate;
                tmp:eduOrg ?eduLabel ;
                tmp:degreeTitle ?degree .
        }}
        WHERE {{
            #required - label, first, last
            #BrownThing to ignore inactive faculty
            {{
            ?subject blocal:hasAffiliation <{0}> ;
                a vivo:FacultyMember,
                blocal:BrownThing ;
                rdfs:label ?name ;
                foaf:firstName ?first ;
                foaf:lastName ?last .
            }}
            #optional - middle name
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	vivo:middleName ?middle .
            }}
            #optional - title
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	vivo:preferredTitle ?title .
            }}
            #optional - email
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	vivo:primaryEmail ?email .
            }}
            #optional - overview
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	vivo:overview ?overview .
            }}
            #optional - affiliations
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	blocal:hasAffiliation ?org .
                ?org rdfs:label ?orgName .
            }}
            #optional - education
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
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
                        a blocal:BrownThing ;
                	vivo:hasResearchArea ?ra .
                ?ra a blocal:ResearchArea ;
                    rdfs:label ?raName .
            }}
            #optional - research country
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	blocal:hasGeographicResearchArea ?country .
                ?country a blocal:Country ;
                    rdfs:label ?countryName .
            }}
            #optional - photos
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                	vitro:mainImage ?mi .
                #main image
                ?mi vitro:downloadLocation ?miDl .
                ?miDl vitro:directDownloadUrl ?miURL .
                BIND(CONCAT('https://vivo.brown.edu', ?miURL) as ?photo) .
                #thumbnail
                ?mi vitro:thumbnailImage ?ti .
                ?ti vitro:downloadLocation ?dl .
                ?dl vitro:directDownloadUrl ?tiURL .
                BIND(CONCAT('https://vivo.brown.edu', ?tiURL) as ?thumb) .
            }}
            #optional - faculty titles
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                    vivo:personInPosition ?pos .
                ?pos a vivo:FacultyPosition;
                    rdfs:label ?facultyTitle.
            }}
            #optional - administrative titles
            UNION {{
                ?subject blocal:hasAffiliation <{0}> ;
                        a blocal:BrownThing ;
                    vivo:personInPosition ?pos .
                ?pos a vivo:FacultyAdministrativePosition;
                    rdfs:label ?adminTitle.
            }}
        }}
    """.format(org_uri)
    headers = {'Accept': 'application/json', 'charset':'utf-8'}	
    data = { 'email': email, 'password': passw, 'query': query }
    resp = requests.post(query_url, data=data, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.error('Bad response from Query API: {}'.format(resp.text))
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
            attr = attrMap[k]
            for obj in v:
                out[attr] = obj['@value']
    return out

def cast_roster_data(data, edu_map):
    out = mint_roster_obj()
    for k, v in data.items():
        if k == '@type':
            continue
        attr = attrMap[k]
        if attr == 'education':
            for eduId in v:
                eduObj = edu_map[eduId['@id']]
                edu_cast = cast_edu_data(eduObj)
                out[attr].append(edu_cast)
        elif attr == 'url':
            out[attr] += v
        elif attr in ( 'affiliations','topics','countries' ):
            for obj in v:
                out[attr].append(obj['@value'])
        elif attr in ( 'first','last','middle','title', 'full',
                        'email','image','thumbnail','overview'):
            for obj in v:
                out[attr] += obj['@value']
        elif attr in ('faculty_title', 'admin_title'):
            attrs = {
                'faculty_title': 'faculty',
                'admin_title': 'administrative',
            }
            out['title_detail'][attrs[attr]] = [ obj['@value'] for obj in v ]
        else:
            raise Exception(k)
    return out

def main(uri=None, all_uris=False):
    logger.info('Initiating roster build')
    uri_tuples = []
    if all_uris:
        with open('data/org_ids.csv','r') as f:
            rdr = csv.reader(f)
            for row in rdr:
                uri_tuples.append(row)
    elif uri:
        uri_tuples.append( (uri, uri[33:]) )
    for uri_tup in uri_tuples:
        time.sleep(throttle)
        logger.info('Building roster for: {}'.format(uri_tup[1]))
        try:
            roster_resp = query_roster(uri_tup[0])
        except:
            logger.error(
                'Failure to query roster for: {}'.format(uri_tup[1]))
            continue
        try:
            roster_list, edu_map = extract_education_data(roster_resp)
        except:
            logger.error(
                'Failure to extract data for: {}'.format(uri_tup[1]))
            continue
        unit_data = { 'unit': uri_tup[0], 'roster': [] }
        for prsn in roster_list:
            try:
                prsn_data = cast_roster_data(prsn, edu_map)
            except:
                rabid = prsn.get('@id', 'Could not parse RABID')
                logger.error(
                    'Failure to cast data for: {}'.format(rabid))
                continue
            unit_data['roster'].append(prsn_data)
        logger.info('Writing JSON for: {}'.format(uri_tup[1]))
        with open(os.path.join('rosters', uri_tup[1] +'.json'), 'w') as f:
            json.dump(unit_data, f,
                indent=2, sort_keys=True, ensure_ascii=False)
    logger.info('Roster build complete')

if __name__ == "__main__":
    arg_parse = argparse.ArgumentParser()
    arg_parse.add_argument("-u","--uri")
    arg_parse.add_argument("-a","--all", action="store_true")
    arg_parse.add_argument("-t","--test", action="store_true")
    args = arg_parse.parse_args()
    if args.uri:
        main(uri=args.uri)
    if args.all:
        main(all_uris=True)
    if args.test:
        main(uri='http://vivo.brown.edu/individual/org-brown-univ-dept29')
