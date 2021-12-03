import subprocess
import urllib.request
from pathlib import Path
import hashlib
import json
import time
import tempfile
import os
import sys

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

    timestamp = int(time.time())

    db = create_db(all_urls, timestamp)

    json_name = 'db_unstable_nightlies_folder.json'

    with open(json_name, 'w') as f:
        json.dump(db, f, sort_keys=True, indent=4)

    print(json_name)
    if len(sys.argv) > 0 and sys.argv[0] == '--push':
        subprocess.run('git add ' + json_name, shell=True, stdout=subprocess.PIPE)
        subprocess.run('git commit "%d"' % timestamp, shell=True, stdout=subprocess.PIPE)
        subprocess.run('git pull', shell=True, stdout=subprocess.PIPE)
        subprocess.run('git push', shell=True, stdout=subprocess.PIPE)
    print('Done.')

def create_db(all_urls, timestamp):

    db = {
        "db_id": 'unstable_nightlies_folder',
        "db_files": [],
        "files": {},
        "folders": {'_Unstable': {}},
        "zips": {},
        "base_files_url": "",
        "default_options": {},
        "timestamp": timestamp
    }

    with tempfile.NamedTemporaryFile() as temp:

        unstable_delme_file = temp.name

        for url in all_urls:
            try:
                Path(unstable_delme_file).unlink()
            except:
                pass
            download(url, unstable_delme_file)

            db["files"]["_Unstable/" + Path(url).name] = {
                "url": url,
                "size": size(unstable_delme_file),
                "hash": hash(unstable_delme_file)
            }

        return db

def download(url, path):
    urllib.request.urlretrieve(url, path)

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