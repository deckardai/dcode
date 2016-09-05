#!/usr/bin/env python2
# coding: utf-8

# Handles urls like code://xyz

import sys
import os
from os.path import join, exists, normpath, basename, expanduser
from subprocess import check_call
try:
    from urlparse import urlparse, parse_qs
except:
    from urllib.parse import urlparse, parse_qs
import json

HOME = expanduser("~")
CONFIG_FILE = join(HOME, '.dcode.json')

# Add paths where editors are likely found
print(os.environ['PATH'])
os.environ['PATH'] += os.pathsep + '/usr/local/bin'

if sys.platform == 'darwin':
    editorCommands = {
        'atom': ['open', '-a', 'atom', '-n', '--args'],
        # vscode doesn't honor arguments from "open -a"
        'vscode': [
            '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code',
            '--goto', '--reuse-window',
        ],
    }
else:
    editorCommands = {
        'atom': ['atom'],
        # vscode doesn't honor arguments from "open -a"
        'vscode': [
            'code', '--goto', '--reuse-window',
        ],
    }


# Paths known to be repositories
repoCache = None


def enumerateRepos(home=None):
    ' Walk through HOME and yield git repositories. '
    if not home:
        home = HOME
    # Walk all directories
    for dirpath, childDirs, filenames in os.walk(home, topdown=True):
        # Skip hidden directories
        if basename(dirpath).startswith('.'):
            del childDirs[:]
            continue
        # See whether that's a repository root
        if '.git' in childDirs or '.hg' in childDirs:
            print('GIT ' + basename(dirpath) + ' in ' + dirpath)
            yield dirpath


def collectRepos(home=None, refresh=False):
    global repoCache
    if repoCache is None or refresh:
        repoCache = list(enumerateRepos(home))
    return repoCache


def findRepoWithPath(path, repoName=None):
    ' Find a repo that contains this path. '
    for root in collectRepos():
        fullPath = root + '/' + path
        if exists(fullPath):
            if repoName and basename(root).lower() != repoName.lower():
                print('W Repo name %s do not match %s', repoName, root)
            return root
    return None


def findRepoFromUrl(url):
    # Find erroneous encoding of hashes (#)
    lastHash = url.rfind('%23')
    if lastHash >= 0:
        url = url[:lastHash] + '#' + url[lastHash+3:]

    # Parse url and parameters
    purl = urlparse(url)
    params = parse_qs(purl.query)
    if not purl.path:
        return None

    root = findRepoWithPath(
        path=purl.path,
        repoName=purl.hostname,
    )
    if root is None:
        return None

    lines = params.get('line') or params.get('l')
    cols = params.get('column') or params.get('c')
    location = {
        'root': root,
        'path': purl.path,
        'line': lines[0] if lines else None,
        'column': cols[0] if cols else None,
    }
    return location


def launchEditor(location):
    arg = location['root'] + '/' + location['path']
    if location['line']:
        arg += ':' + location['line']
        if location['column']:
            arg += ':' + location['column']

    # TODO Use multiple PATH to support linux and mac
    editor = 'atom'
    cmd = editorCommands[editor] + [arg]
    check_call(cmd)


def openUrl(url):
    print('Opening ' + url)
    location = findRepoFromUrl(url)
    if not location:
        # Rescan and try again
        collectRepos(refresh=True)
        location = findRepoFromUrl(url)

    if not location:
        print('E Not found')
    else:
        print(location)
        launchEditor(location)


def testOpen():
    openUrl('code://deckard/codebase/Makefile?line=2&column=4')


def load():
    try:
        with open(CONFIG_FILE) as fd:
            config = json.load(fd)
    except:
        config = {}
    return config


def save(config):
    try:
        with open(CONFIG_FILE, 'w') as fd:
            json.dump(config, fd)
    except Exception as e:
        print(repr(e))
    return config


def init():
    ' Load configuration file and populate the cache if available '
    global repoCache
    config = load()
    repos = config.get('repositories')
    if repos:
        repoCache = repos
    else:
        config['repositories'] = collectRepos()
    return config


def main(argv):
    ' Command line '
    config = init()
    save(config)
    if len(argv) >= 2:
        # Run once, from argument
        openUrl(argv[1])
    else:
        # Run forever, from stdin
        while True:
            url = sys.stdin.readline().strip()
            openUrl(url)
            sys.stdout.flush()

if __name__ == '__main__':
    main(sys.argv)
