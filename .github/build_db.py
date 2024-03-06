# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# You can download the latest version of this tool from:
# https://github.com/MiSTer-unstable-nightlies/Unstable_Folder_MiSTer


import subprocess
from pathlib import Path
import hashlib
import json
import time
import tempfile
import os
import sys
import re

_print = print
def print(text=""):
    _print(text, flush=True)
    sys.stdout.flush()

def main():
    print('START!')
    print()

    all_urls = gather_urls()
    if len(all_urls) == 0:
        print('Nothing to do.')
        return
    
    db = create_db(all_urls)

    add_n64(db)
    
    json_name = 'db_unstable_nightlies_folder.json'
    save_json(db, json_name)

    if len(sys.argv) > 1 and sys.argv[1] == '--push':
        push(db, json_name)

    print('Done.')

def gather_urls():
    proc = subprocess.run('gh repo list -L 200 MiSTer-unstable-nightlies --json "name" | jq -r ".[].name"', shell=True, stdout=subprocess.PIPE)
    all_urls = []
    for name in proc.stdout.decode().splitlines():
        print(name)

        proc = subprocess.run(r'gh release view -R "MiSTer-unstable-nightlies/%s" unstable-builds --json "assets" 2> /tmp/stderr | jq -r ".assets[] | select(.name|test(\"^.*_unstable_[0-9]{8}_([0-9]{2})?[0-9a-z]{4}[.]rbf$\")) | .url" | sort' % name, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        lines = proc.stdout.decode().strip().splitlines()
        if len(lines) == 0:
            print('rbf file not found')

        lines.reverse()
        core_cache = set()
        for url in lines:
            cache_id = url.split('_unstable_')[0]
            if cache_id in core_cache:
                continue

            core_cache.add(cache_id)
            all_urls.append(url)
            print('URL: ' + url)

        print()
    
    return all_urls
    
def create_db(all_urls):

    db = {
        "db_id": 'unstable_nightlies_folder',
        "db_files": [],
        "files": {},
        "folders": {'_Unstable': {}},
        "zips": {},
        "base_files_url": "",
        "default_options": {},
        "timestamp":  int(time.time())
    }

    with tempfile.NamedTemporaryFile() as temp:

        unstable_delme_file = temp.name

        for url in all_urls:
            unlink(unstable_delme_file)
            download(url, unstable_delme_file)
            db["files"]["_Unstable/" + Path(url).name] = describe_file(url, unstable_delme_file)

        return db

def download(url, path):
    subprocess.run(['curl', '-L', '-o', path, url], stderr=subprocess.STDOUT)

def unlink(path):
    try:
        Path(unstable_delme_file).unlink()
    except:
        pass

def describe_file(url, file):
    name = Path(url).name.split('_unstable_')[0].lower()
    try:
        return {
            "url": url,
            "size": size(file),
            "hash": hash(file),
            "tags": [clean_tag(name)]
        }
    except Exception as e:
        print('Exception during ' + url)
        raise e

def hash(file):
    with open(file, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
        return file_hash.hexdigest()

def size(file):
    return os.path.getsize(file)

def save_json(db, json_name):
    with open(json_name, 'w') as f:
        json.dump(db, f, sort_keys=True, indent=4)

    print(json_name)
    subprocess.run(['cat', json_name], stderr=subprocess.STDOUT)
    print()

def push(db, json_name):
    timestamp = db['timestamp']

    if not changes_detected(db):
        print('No changes')
        return

    print('Pushing changes...')
    subprocess.run(['git', 'add', json_name], stderr=subprocess.STDOUT)
    subprocess.run(['git', 'commit', '-m', str(timestamp)], stderr=subprocess.STDOUT)
    subprocess.run(['git', 'pull'], stderr=subprocess.STDOUT)
    subprocess.run(['git', 'push'], stderr=subprocess.STDOUT)

def changes_detected(db):
    try:
        return changes_detected_impl(db)
    except:
        pass
    return True

def changes_detected_impl(db):
    already_existing_file = "/tmp/existing.json"
    
    download("https://raw.githubusercontent.com/MiSTer-unstable-nightlies/Unstable_Folder_MiSTer/main/db_unstable_nightlies_folder.json", already_existing_file)
    with open(already_existing_file) as json_file:
        existing = json.load(json_file)
        existing['timestamp'] = 0
        db['timestamp'] = 0

        return json.dumps(existing, sort_keys=True) != json.dumps(db, sort_keys=True)

term_regex = re.compile("[-_a-z0-9.]$", )

def clean_tag(term: str) -> str:
    result = ''.join(filter(lambda chr: term_regex.match(chr), term.replace(' ', '')))
    return result.replace('-', '').replace('_', '')

def add_n64(db):
    try:
        getlast_tmp = "/tmp/getlast.json"
        download("https://vampier.net/N64/getlast.php", getlast_tmp)
        with open(getlast_tmp) as getlast_db:
            for file_path, file_description in json.load(getlast_db)['files'].items():
                db['files'][file_path] = file_description
                file_description['tags'] = ['n64', 'nintendo64']
    except Exception as err:
        print('Exception on add_n64!')
        print(err)
        print('Running fallback')
        already_existing_file = "/tmp/existing.json"
        download("https://raw.githubusercontent.com/MiSTer-unstable-nightlies/Unstable_Folder_MiSTer/main/db_unstable_nightlies_folder.json", already_existing_file)
        with open(already_existing_file) as json_file:
            for file_path, file_description in json.load(json_file)['files'].items():
                if 'tags' in file_description and 'n64' in file_description['tags']:
                    db['files'][file_path] = file_description

if __name__ == "__main__":
    main()
