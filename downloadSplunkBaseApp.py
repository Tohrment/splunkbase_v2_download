#!/usr/local/bin/python3

import json
import requests
import os
import bs4
import cgi
import argparse


def get_js_form_details(form):
    action = form.attrs.get('action').lower()
    method = form.attrs.get('method', 'get').lower()
    data = {}
    for input_tag in form.find_all('input'):
        input_name = input_tag.attrs.get('name')
        input_value = input_tag.attrs.get('value', '')
        data[input_name] = input_value
    return action, method, data


def submit_js_form(session, form):
    action, method, form_data = get_js_form_details(form)
    if method == 'post':
        session.post(action, data=form_data)
    elif method == 'get':
        session.get(action, data=form_data)


def get_download_link_classic(splunkbase_num, session, version):
    ver_list = []
    BASE_SPLUNK_BASE_URL = 'https://classic.splunkbase.splunk.com'
    soup_ver = bs4.BeautifulSoup(session.get(
        f"{BASE_SPLUNK_BASE_URL}/app/{splunkbase_num}").content, 'html.parser')
    versions = soup_ver.find_all('sb-release-select')
    for v in range(len(versions)-1):
        ver_list.append(soup_ver.find_all('sb-release-select')[v]['sb-target'])
    ver_list = list(dict.fromkeys(ver_list))
    if version == 'latest':
        target_ver = soup_ver.find('sb-release-select')['sb-target']
    elif version in ver_list:
        target_ver = version
    else:
        raise "Version not found. Please check version and try again."
    dl_link = f"{BASE_SPLUNK_BASE_URL}/app/{splunkbase_num}/release/{target_ver}/download/"

    return dl_link


def get_download_link(splunkbase_num, session, version, username):
    try:
        ver_list = {}
        refresh = session.get(
            f'https://api.splunkbase.splunk.com/api/v1/user/{username}/?fields=id,username,apps,apps_editable,apps_subscribed,apps_entitlements,api_tos_accepted')
        response = json.loads((session.get(
            f'https://api.splunkbase.splunk.com/api/v2/apps?include=categories,collections,contributors,created_by,documentation,icon,installation,ranking,rating,release,release.actions,release.version_compatibility,releases,releases.actions,releases.version_compatibility,repo_name,repo_url,screenshots,support,troubleshooting&ids={splunkbase_num}&limit=1&archive=all&product=all')).content)
        if not version == 'latest':
            for i in response['results']:
                for j in i['releases']:
                    ver_list[j['release_name']]: j['path']
            dl_link = ver_list[version]
        elif version == 'latest':
            dl_link = response['results'][0]['release']['path']
    except:
        dl_link = get_download_link_classic(splunkbase_num, session, version)
    return dl_link


def splunk_login(session, username, password):
    CSRF_BASE_URL = 'https://login.splunk.com/api/v2/auth/csrfToken'
    BASE_AUTH_URL = 'https://login.splunk.com/api/v2/auth/okta-login'
    headers = {
        'accept': '*/*',
        'Content-Type': "application/json"
    }

    csrf = (json.loads((session.get(CSRF_BASE_URL, headers=headers)).text))[
        '_csrf']

    data = {
        "username": username,
        "password": password,
        "_csrf": csrf
    }

    auth = session.post(BASE_AUTH_URL, json=data,
                        headers=headers, allow_redirects=True)
    return auth


def tgz_download(username, password, splunkbase_num, version):
    session = requests.session()
    auth = splunk_login(session, username, password)
    dl_link = get_download_link(splunkbase_num, session, version, username)
    if auth.status_code == 200:
        print('Successfully auth\'d')
        con_refresh = session.get(
            f'https://api.splunkbase.splunk.com/api/v1/user/{username}/?fields=id,username,apps,apps_editable,apps_subscribed,apps_entitlements,api_tos_accepted')
        js_site = bs4.BeautifulSoup(
            session.get(dl_link).content, 'html.parser')
        if len(js_site) > 1:
            submit_js_form(session, js_site.find('form'))
            response = session.get(dl_link)
            _, params = cgi.parse_header(
                response.headers.get('Content-Disposition'))
            # print(params)
            filename = params['filename']
        if filename:
            with open(filename, 'wb') as f:
                f.write(response.content)
        if os.path.exists(filename):
            print(f'Successfully downloaded {filename}.')
        else:
            print(f'Failed to write data to file.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--username', help='Splunkbase username', required=True)
    parser.add_argument(
        '--password', help='Splunkbase password', required=True)
    parser.add_argument('--splunkbase_num',
                        help='ID of application to download', required=True)
    parser.add_argument('--version', help='Version of app to download')
    args = parser.parse_args()
    if not args.version:
        args.version = 'latest'
    tgz_download(args.username, args.password,
                 args.splunkbase_num, args.version)
