#!/usr/bin/env python
# coding: utf-8

'''
dCode handles urls like this:

    dcode.py dcode://my_project/some/path.py?l=1&c=1
'''
import sys
import os
from os.path import join, exists, basename, expanduser
from glob import iglob
from itertools import chain
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
if 'PATH' not in os.environ:
    os.environ['PATH'] = '/usr/bin'
os.environ['PATH'] += os.pathsep + '/usr/local/bin'
PATHS = list(filter(None, os.environ['PATH'].split(os.pathsep)))


def findExecutable(candidates):
    " Search everywhere for an executable name or path from the candidate list. "
    for name in candidates:
        if name.startswith("/"):
            # An absolute path with wilcard
            cmds = iglob(name)
            if name.startswith("/Applications/"):
                # Check the $HOME/Applications first
                cmds = chain(iglob(HOME + name), cmds)
        else:
            # A script name in one the PATHS
            cmds = [join(path, name) for path in PATHS]

        for cmd in cmds:
            # Exists and is executable?
            if os.access(cmd, os.X_OK):
                return cmd

    return None


editorCommands = {
    "xcode": "open -a xcode --args '{path}'",
}

# IntelliJ editors
# Try all the common names and locations

intellijExecNames = {
    "androidstudio": [ "studio", "/Applications/Android Studio*.app/Contents/MacOS/studio"],
    "appcode": ["appcode", "/Applications/AppCode*.app/Contents/MacOS/AppCode"],
    "clion": ["clion", "/Applications/CLion*.app/Contents/MacOS/clion"],
    "idea": ["idea", "/Applications/IntelliJ IDEA*.app/Contents/MacOS/idea"],
    "phpstorm": ["phpstorm", "pstorm", "/Applications/PhpStorm*.app/Contents/MacOS/phpstorm"],
    "pycharm": ["pycharm", "charm", "/Applications/PyCharm*.app/Contents/MacOS/pycharm"],
    "rubymine": ["rubymine", "mine", "/Applications/RubyMine*.app/Contents/MacOS/rubymine"],
    "webstorm": ["webstorm", "wstorm", "/Applications/WebStorm*.app/Contents/MacOS/webstorm"],
}

# Auto-detect the launcher location
def renderIntellijCommand(editor='', **variables):
    editor = editor.split(':')[0]
    execNames = intellijExecNames[editor]
    execPath = findExecutable(execNames)
    if not execPath:
        return None
    cmd = "'{execPath}' --line '{line}' '{path}'".format(
        execPath=execPath,
        **variables
    )
    if ".app" in execPath:
        # Launch the main app in the background and return
        cmd += " &"
    return cmd

# Register them all
for ed in intellijExecNames.keys():
    editorCommands[ed] = renderIntellijCommand


# Sublime Text
sublimeExecNames = [
    "subl", # In PATH
    join(HOME, "bin/subl"), # As documented by Sublime
    "/Applications/Sublime Text*.app/Contents/SharedSupport/bin/subl", # Default on mac
    "/opt/sublime_text/sublime_text", # Default on linux
]

def renderSublimeCommand(**variables):
    execPath = findExecutable(sublimeExecNames)
    if not execPath:
        return None
    return "'{execPath}' --add '{pathLineColumn}'".format(
        execPath=execPath,
        **variables
    )

editorCommands["sublime"] = renderSublimeCommand


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

    if repoName == "_demo":
        return os.path.dirname(os.path.realpath(__file__))

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
    repo = purl.hostname
    path = purl.path.strip('/')

    # Extract repo and path from github.com org/repo/path
    if repo == 'github.com' or repo == 'bitbucket.org':
        repoStart = path.find("/") + 1
        repoEnd = path.find("/", repoStart)
        if repoEnd < 0:
            repoEnd = len(path)
        # Split the path
        repo = path[repoStart:repoEnd]
        path = path[repoEnd+1:]  # Skip the slash
        # Remove blob/master/ if present
        if path.startswith("blob/"):  # len=5
            pathStart = path.find("/", 5) + 1
            path = path[pathStart:]

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
            repoName=repo,
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
        if not cmd:
            print('E No editor launcher found')
            return
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
        warning("No config file at %s (%s)", CONFIG_FILE, str(e)[:500])
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


def mainDcode(args=None):
    ' Handle a URL '

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


def main(args=None):
    ' Command line '

    if args is None:
        args = sys.argv[1:]

    if len(args) < 1:
        print(__doc__)
        sys.exit(1)

    elif args[0] == 'install':
        from . import install
        install.install()
        sys.exit(0)

    else:
        mainDcode(args)

if __name__ == '__main__':
    main()
