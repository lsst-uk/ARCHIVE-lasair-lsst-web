from django.test import TestCase

# Create your tests here.
import requests
import json

# put your token here
headers = {
    'Authorization': 'Token ffffffffffffffffffffffffffffffffffffffff'
}

def cone():
    url = 'https://lasair-iris.roe.ac.uk/coneapi/'
    data = {
        'ra': '194.494',
        'dec': '48.851',
        'radius': '60.0',
        'requestType':'all'
    }

    r = requests.post(url, data, headers=headers)
    print('status=', r.status_code)
    response = r.json()
    print(json.dumps(response, indent=2))

def streamlog():
    url = 'https://lasair-iris.roe.ac.uk/streamlogapi/'
    data = {
        'topic': '2SherlockCVs'
#        'topic': '2OrphanSearch'
    }

    r = requests.post(url, data, headers=headers)
    print('status=', r.status_code)
    if r.status_code != 200:
        print('Failed')
    else:
        response = r.json()
        if 'jsonStreamLog' in response:
            data = response['jsonStreamLog']['digest']
            print(json.dumps(data, indent=2))
        print('info:', response['info'])

def query():
    url = 'https://lasair-iris.roe.ac.uk/queryapi/'
    data = {
        'selected'  : 'objectId, latestgmag',
        'tables'    : 'objects',
        'conditions': 'latestgmag < 13'
    }

    r = requests.post(url, data, headers=headers)
    print('status=', r.status_code)
    if r.status_code != 200:
        print('Failed')
        print(r.text)  # dump
    else:
        response = r.json()
        print(json.dumps(response['query'],  indent=2))
        print(json.dumps(response['result'], indent=2))
        print('info:', response['info'])

########## choose one ###########
#cone()
#streamlog()
query()

