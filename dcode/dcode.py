#!/usr/bin/env python
# coding: utf-8

'''
dCode handles urls like this:

    dcode.py dcode://my_project/some/path.py?l=1&c=1
'''

import sys
import os
from os.path import join, exists, basename, expanduser
from subprocess import check_call
try:
    from urlparse import urlparse, parse_qs
except:
    from urllib.parse import urlparse, parse_qs
import json
from pprint import pprint
from logging import warning
from time import sleep

HOME = expanduser("~")
CONFIG_FILE = join(HOME, '.dcode.json')
CONFIG_DEFAULTS = {
    'command': '',
    'editor': 'system',
}
DEV = os.environ.get('DCODE_DEV')

# Add paths where editors are likely found
os.environ['PATH'] += os.pathsep + '/usr/local/bin'


editorCommands = {
    # IntelliJ editors
    'androidstudio': "studio '{pathLine}'",
    'appcode': "appcode '{pathLine}'",
    'clion': "clion '{pathLine}'",
    'idea': "idea '{pathLine}'",
    'phpstorm': "pstorm '{pathLine}'",
    'pycharm': "charm '{pathLine}'",
    'rubymine': "mine '{pathLine}'",
    'webstorm': "wstorm '{pathLine}'",
    'xcode': "open -a xcode --args '{path}'",
}

# Vim
def renderVimCommand(editor='', **variables):
    tpl = "{vim} {server} --remote-tab-silent '+call cursor({line},{column})' '{path}'"
    parts = editor.split(':')
    vim = parts[0]
    server = parts[1] if len(parts) >= 2 else ""
    if not server:
        # No server specified, must open vim in a graphical window
        vim = "gvim"
    cmd = tpl.format(
        vim=vim,
        server=("--servername '" + server + "'") if server else "",
        **variables
    )
    return cmd

editorCommands['vim'] = renderVimCommand
editorCommands['gvim'] = renderVimCommand
editorCommands['nvim'] = renderVimCommand

# Atom, VSCode, ...
if sys.platform == 'darwin':
    editorCommands.update({
        'atom': "open -a atom -n --args '{pathLineColumn}'",
        'system': "open '{path}'",
        # vscode doesn't honor arguments from "open -a"
        'vscode': "'/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code' --goto --reuse-window '{pathLineColumn}'",
    })
else:
    editorCommands.update({
        'atom': "atom '{pathLineColumn}'",
        'system': "xdg-open '{path}'",
        'vscode': "code --goto --reuse-window '{pathLineColumn}'",
    })

# Add documentation to the config file
CONFIG_EXTRAS = {
    '_doc': (
        'Choose an editor preset, or specify a command template. '
        'The following parameters are currently supported: {path} {pathLine} {pathLineColumn}. '
        'The path and numbers render as path:12:34 '
    ),
    '_editors_available': list(sorted(editorCommands.keys())),
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
        repoCache.sort(key=len)  # Prioritize shorter paths
        freshCache = True
    return repoCache


def sortReposForName(roots, name):
    ' Reorder the roots by closeness to the name'
    def distance(root):
        folder = basename(root)
        if name == folder:
            return 0
        fl = folder.lower()
        nl = name.lower()
        if nl == fl:
            return 1
        if nl in fl:
            return 1 + len(fl) - len(nl)
        if fl in nl:
            return 1 + len(nl) - len(fl)
        if nl in root.lower():
            return 1 + len(root)
        return 1000
    return sorted(roots, key=distance)


def findRepoWithPath(path, repoName=None):
    ' Find a repo that contains this path. '
    roots = collectRepos()
    if repoName:
        roots = sortReposForName(roots, repoName)
    for root in roots:
        fullPath = root + '/' + path
        if exists(fullPath):
            if repoName and basename(root).lower() != repoName.lower():
                print('W Repo name {0} does not match {1}'.format(repoName, root))
            return root
    return None


def findRepoWithRoot(root, path):
    ' Check if the root contains the path. '
    fullPath = root + '/' + path
    if exists(fullPath):
        return root
    return None


def cleanQuotes(path):
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

    root = None
    # Try the root from the url
    urlRoots = params.get('root')
    if urlRoots:
        root = findRepoWithRoot(
            root=urlRoots[0],
            path=path,
        )
    # Otherwise autodetect the root
    if root is None:
        root = findRepoWithPath(
            path=path,
            repoName=purl.hostname,
        )
    # Not found
    if root is None:
        return None

    def listToInt(strings):
        if not strings:
            return 0
        s = strings[0]
        if not s.isdigit():
            return 0
        return int(s)

    lines = params.get('line') or params.get('l')
    cols = params.get('column') or params.get('c')
    editors = params.get('editor')
    location = {
        'root': root,
        'path': path,
        'line': listToInt(lines),
        'column': listToInt(cols),
        'editor': editors[0] if editors else '',
    }
    return location


def renderEditorCommand(tpl, variables):
    " Format tpl if it's a string, or call it if it's a function "
    if hasattr(tpl, '__call__'):
        return tpl(**variables)
    else:
        return tpl.format(**variables)


def makeEditorCommand(config, location):
    # Create path:line:column notation
    # `line` and `column` are optional
    fullPath = join(location['root'], location['path']).rstrip('/')
    withLine = fullPath
    withColumn = fullPath
    if location['line']:
        withLine += ':' + str(location['line'])
        withColumn = withLine
        if location['column']:
            withColumn += ':' + str(location['column'])

    # Find the command template...
    # ...in the url itself
    editor = location.get('editor', '')
    preset = editor.split(':')[0]
    tpl = editorCommands.get(preset)
    if preset and not tpl:
        warning('Unknown editor "%s"' % preset)
    # ...as a custom command
    if not tpl:
        preset = ''
        tpl = config.get('command')
    # ...as a preset
    if not tpl:
        editor = config.get('editor', '')
        preset = editor.split(':')[0]
        tpl = editorCommands.get(preset)

    if not tpl:
        raise ValueError('Could not make an editor command')

    variables = dict(
        root=cleanQuotes(location['root']),
        relPath=cleanQuotes(location['path']),
        path=cleanQuotes(fullPath),
        line=location['line'],
        column=location['column'],
        pathLine=withLine,
        pathLineColumn=withColumn,
        editor=cleanQuotes(editor),
    )
    cmd = renderEditorCommand(tpl, variables)
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
                dict(config, **CONFIG_EXTRAS),
                fd,
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


def main(args=None):
    ' Command line '

    if args is None:
        args = sys.argv[1:]

    if len(args) < 1:
        print(__doc__)
        sys.exit(1)

    config = init()
    save(config)
    if DEV:
        pprint(config)

    if args[0] == '-':
        # Run forever, from stdin
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            url = line.strip()
            if not url:
                continue
            try:
                openUrl(config, url)
            except Exception as e:
                warning(repr(e)[:500])
            sys.stdout.flush()
            sleep(0.1)

    else:
        # Run once, from argument
        openUrl(config, args[0])

if __name__ == '__main__':
    main()
