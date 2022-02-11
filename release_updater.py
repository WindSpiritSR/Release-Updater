# -*- encoding: utf-8 -*-

import os
import sys
import time
import requests
from requests.adapters import HTTPAdapter
import json
import urllib.parse
import jsonschema
from jsonschema import validate

CONFIG_DIR = os.path.abspath('./')
CONFIG_FILE = 'release_updater.conf'
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE)
RELEASE_PATH = os.path.abspath('./')
API_GITHUB = 'https://api.github.com/repos'
API_HEADERS = {'Accept': 'application/vnd.github.v3+json'}
API_PATH_LATEST_RELEASE = 'releases/latest'
REQUESTS_RETRIES = 20
PROXIES = {}
AUTH_USER = ''
AUTH_TOKEN = ''

s = requests.Session()
s.mount('http://', HTTPAdapter(max_retries=REQUESTS_RETRIES))
s.mount('https://', HTTPAdapter(max_retries=REQUESTS_RETRIES))

schema = {
    'type': 'object',
    'required': ['repos', 'proxy', 'auth', 'release_path'],
    'properties': {
        'repos': {
            'type': 'array',
            'items': {
                'required': ['owner', 'repo', 'local_release'],
                'properties': {
                    'owner': {
                        'type': 'string'
                    },
                    'repo': {
                        'type': 'string'
                    },
                    'local_release': {
                        'type': 'string'
                    }
                }
            }
        },
        'proxy': {
            'type': 'object',
            'required': ['enable', 'http', 'https'],
            'properties': {
                'enable': {
                    'type': 'boolean'
                },
                'http': {
                    'type': 'string'
                },
                'https': {
                    'type': 'string'
                }
            }
        },
        'auth': {
            'type': 'object',
            'required': ['user', 'access_token'],
            'properties': {
                'user': {
                    'type': 'string'
                },
                'access_token': {
                    'type': 'string'
                }
            }
        },
        'release_path': {
            'type': 'string'
        }
    }
}


def err_exit(code, arg):
    if code == -1:
        print('Cannot find config file [' + arg + '].')
    elif code == -2:
        print('Config validate failed: [' + arg + '].')
    elif code == -3:
        print('Request return code [' + arg + '].')
    else:
        print('Unknown error.')
    os._exit(code)


def check_config_file():
    global CONFIG_PATH
    if not os.path.exists(CONFIG_PATH):
        err_exit(-1, CONFIG_PATH)


def check_local_dir(local_dir):
    if not os.path.exists(local_dir):
        os.mkdir(local_dir)

def init(config):
    global PROXIES, RELEASE_PATH, AUTH_USER, AUTH_TOKEN
    try:
        validate(instance=config, schema=schema)
    except jsonschema.exceptions.ValidationError as err:
        err_exit(-2, err.message)

    if config['proxy']['enable']:
        PROXIES = {
            'http': config['proxy']['http'],
            'https': config['proxy']['https'],
        }

    if config['release_path'] != '':
        RELEASE_PATH = config['release_path']

    AUTH_USER = config['auth']['user']
    AUTH_TOKEN = config['auth']['access_token']


def read_config():
    global CONFIG_PATH
    check_config_file()
    return_json = {}
    with open(CONFIG_PATH, 'r') as f:
        return_json = json.loads(f.read())
    return return_json


def get_latest_release_json(repo_owner, repo_name):
    global API_GITHUB, API_PATH_LATEST_RELEASE, API_HEADERS, PROXIES, AUTH_USER, AUTH_TOKEN
    request_url_list = [API_GITHUB, repo_owner,
                        repo_name, API_PATH_LATEST_RELEASE]
    request_url = '/'.join(request_url_list)

    req = s.get(request_url, headers=API_HEADERS, proxies=PROXIES, auth=(AUTH_USER, AUTH_TOKEN))
    if req.status_code == 200:
        return req.json()
    else:
        return {
            'err_code': req.status_code
        }


def resolve_release(config):
    release_list = []
    for conf_repo_index, repo in enumerate(config['repos']):
        repo_owner = repo['owner']
        repo_name = repo['repo']
        local_release = repo['local_release']
        release_list.append({
                'conf_repo_index': conf_repo_index,
                'repo_owner': repo_owner,
                'repo_name': repo_name,
                'local_release': local_release
            })
    return release_list


def config_update(config, repo_index, update_time):
    global CONFIG_PATH
    with open(CONFIG_PATH, 'w') as config_file:
        config['repos'][repo_index]['local_release'] = update_time
        config_file.write(json.dumps(config, indent=4))

def del_dir(file_path):
    if os.path.exists(file_path):
        if(os.path.isdir(file_path)):
            for p in os.listdir(file_path):
                del_dir(os.path.join(file_path, p))
        else:
            if(os.path.exists(file_path)):
                os.remove(file_path)


def update_release(url, release_name):
    global RELEASE_PATH, API_HEADERS, PROXIES
    check_local_dir(os.path.join(RELEASE_PATH, release_name))
    with open(os.path.join(os.path.join(RELEASE_PATH, release_name),
                urllib.parse.unquote(os.path.basename(url))), 'wb') as code:
        code.write(s.get(url, headers=API_HEADERS, proxies=PROXIES).content)

def print_status(str):
    print(str, end=' ')
    sys.stdout.flush()

def check_release_update(config, release_list):
    global RELEASE_PATH
    for release in release_list:
        release_latest = get_latest_release_json(
            release['repo_owner'], release['repo_name'])

        print_status('[' + release['repo_owner'] + '/' + release['repo_name'] + ']')

        if 'err_code' in release_latest:
            print_status('Request result code: [' + str(release_latest['err_code']) + ']')
        else:
            release_latest_time = release_latest['published_at']
            print_status('Local: [' + release['local_release'] + ']')
            print_status('Repo: [' + release_latest_time + ']')
            if release_latest_time != release['local_release']:
                del_dir(os.path.join(RELEASE_PATH, release['repo_name']))
                print_status('Updating...')
                for release_latest_asset in release_latest['assets']:
                    update_release(release_latest_asset['browser_download_url'], release['repo_name'])
                config_update(config, release['conf_repo_index'], release_latest_time)
                print_status('Done')
            else:
                print_status('Latest')
        print()


def main(argv):
    config_json = read_config()
    init(config_json)
    release_list = resolve_release(config_json)
    check_release_update(config_json, release_list)


if __name__ == "__main__":
    main(sys.argv[1:])
