#!/usr/bin/env python
# coding: utf-8

# Handles urls like dcode://my_project/some/path.py?l=1&c=1

import sys
import os
from os.path import join, exists, normpath, basename, expanduser
from subprocess import check_call
try:
    from urlparse import urlparse, parse_qs
except:
    from urllib.parse import urlparse, parse_qs
import json
from pprint import pprint
from logging import warning

HOME = expanduser("~")
CONFIG_FILE = join(HOME, '.dcode.json')
CONFIG_DEFAULTS = {
    'editor': 'atom',
}
DEV = os.environ.get('DCODE_DEV')

# Add paths where editors are likely found
os.environ['PATH'] += os.pathsep + '/usr/local/bin'
print('PATH=' + os.environ['PATH'])

if sys.platform == 'darwin':
    editorCommands = {
        'atom': "open -a atom -n --args '{pathLineColumn}'",
        # vscode doesn't honor arguments from "open -a"
        'vscode': "'/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code' --goto --reuse-window '{pathLineColumn}'",
    }
else:
    editorCommands = {
        'atom': "atom '{pathLineColumn}'",
        'vscode': "code --goto --reuse-window '{pathLineColumn}'",
    }


# Paths known to be repositories
repoCache = None
freshCache = False


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
    global repoCache, freshCache
    if repoCache is None or refresh:
        repoCache = list(enumerateRepos(home))
        freshCache = True
    return repoCache


def findRepoWithPath(path, repoName=None):
    ' Find a repo that contains this path. '
    for root in collectRepos():
        fullPath = root + '/' + path
        if exists(fullPath):
            if repoName and basename(root).lower() != repoName.lower():
                print('W Repo name {0} do not match {1}'.format(repoName, root))
            return root
    return None


def cleanPath(path):
    ' Remove quotes from paths '
    return path.replace('"', '').replace("'", '')


def findRepoFromUrl(url):
    # Find erroneous encoding of hashes (#)
    lastHash = url.rfind('%23')
    if lastHash >= 0:
        url = url[:lastHash] + '#' + url[lastHash+3:]

    # Parse url and parameters
    purl = urlparse(url)
    params = parse_qs(purl.query)
    path = purl.path.strip('/')
    if not path:
        return None

    root = findRepoWithPath(
        path=path,
        repoName=purl.hostname,
    )
    if root is None:
        return None

    lines = params.get('line') or params.get('l')
    cols = params.get('column') or params.get('c')
    location = {
        'root': root,
        'path': path,
        'line': lines[0] if lines else '',
        'column': cols[0] if cols else '',
    }
    return location


def makeEditorCommand(config, location):
    # Create path:line:column notation
    # `line` and `column` are optional
    fullPath = join(location['root'], location['path'])
    withLine = fullPath
    withColumn = fullPath
    if location['line']:
        withLine += ':' + location['line']
        withColumn = withLine
        if location['column']:
            withColumn += ':' + location['column']

    # Find the command template
    tpl = config.get('command')
    if not tpl:
        preset = config.get('editor')
        if not preset:
            raise ValueError('Could not make an editor command')

        tpl = editorCommands[preset]

    variables = dict(
        root=cleanPath(location['root']),
        path=cleanPath(location['path']),
        line=location['line'],
        column=location['column'],
        fullPath=fullPath,
        pathLine=withLine,
        pathLineColumn=withColumn,
    )
    cmd = tpl.format(**variables)
    if DEV:
        pprint(variables)
        print(cmd)
    return cmd


def openUrl(config, url):
    print('Opening ' + url)
    location = findRepoFromUrl(url)
    if not location and not freshCache:
        # Rescan and try again
        collectRepos(refresh=True)
        location = findRepoFromUrl(url)

    if not location:
        print('E Not found')
    else:
        cmd = makeEditorCommand(config, location)
        prefix = 'echo ' if DEV else ''
        check_call(prefix + cmd, shell=True)


def testOpen():
    openUrl(load(), 'dcode://deckard/codebase/Makefile?line=2&column=4')


def load():
    config = {}
    config.update(CONFIG_DEFAULTS)
    try:
        with open(CONFIG_FILE) as fd:
            config.update(json.load(fd))
    except Exception as e:
        warning(repr(e)[:500])
    return config


def save(config):
    try:
        with open(CONFIG_FILE, 'w') as fd:
            json.dump(
                config, fd,
                sort_keys=True, indent=4, separators=(',', ': '),
            )
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
    if DEV:
        pprint(config)
    if len(argv) >= 2:
        # Run once, from argument
        openUrl(config, argv[1])
    else:
        # Run forever, from stdin
        while True:
            url = sys.stdin.readline().strip()
            openUrl(config, url)
            sys.stdout.flush()

if __name__ == '__main__':
    main(sys.argv)
