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

_print = print
def print(text=""):
    _print(text, flush=True)
    sys.stdout.flush()

def main():
    print('START!')
    print()

    proc = subprocess.run('gh repo list MiSTer-unstable-nightlies --json "name" | jq -r ".[].name"', shell=True, stdout=subprocess.PIPE)
    all_urls = []
    for name in proc.stdout.decode().splitlines():
        print(name)
        proc = subprocess.run(r'gh release view -R "MiSTer-unstable-nightlies/%s" unstable-builds --json "assets" 2> /tmp/stderr | jq -r ".assets[] | select(.name|test(\"^.*_unstable_[0-9]{8}_[0-9a-z]{4}[.]rbf$\")) | .url" | sort | tail -n 1' % name, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        url = proc.stdout.decode().strip()
        if url:
            all_urls.append(url)
            print('URL: ' + url)
        else:
            print('rbf file not found')

        print()

    if len(all_urls) == 0:
        return

    db = create_db(all_urls)

    json_name = 'db_unstable_nightlies_folder.json'

    with open(json_name, 'w') as f:
        json.dump(db, f, sort_keys=True, indent=4)

    print(json_name)
    subprocess.run(['cat', json_name], stderr=subprocess.STDOUT)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == '--push':
        push(db, json_name)

    print('Done.')

def push(db, json_name):
    timestamp = db['timestamp']
    already_existing_file = "/tmp/existing.json"

    try:
        download("https://raw.githubusercontent.com/MiSTer-unstable-nightlies/Unstable_Folder_MiSTer/main/db_unstable_nightlies_folder.json", already_existing_file)
        with open(already_existing_file) as json_file:
            old = json.load(json_file)
            old['timestamp'] = 0
            db['timestamp'] = 0

            if json.dumps(old, sort_keys=True) == json.dumps(db, sort_keys=True):
                print('No changes')
                return
    except:
        pass

    print('Pushing changes...')
    subprocess.run(['git', 'add', json_name], stderr=subprocess.STDOUT)
    subprocess.run(['git', 'commit', '-m', str(timestamp)], stderr=subprocess.STDOUT)
    subprocess.run(['git', 'pull'], stderr=subprocess.STDOUT)
    subprocess.run(['git', 'push'], stderr=subprocess.STDOUT)

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
            try:
                Path(unstable_delme_file).unlink()
            except:
                pass
            download(url, unstable_delme_file)

            try:
                db["files"]["_Unstable/" + Path(url).name] = {
                    "url": url,
                    "size": size(unstable_delme_file),
                    "hash": hash(unstable_delme_file)
                }
            except Exception as e:
                print('Exception during ' + url)
                raise e

        return db

def download(url, path):
    subprocess.run(['curl', '-L', '-o', path, url], stderr=subprocess.STDOUT)

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

if __name__ == "__main__":
    main()
