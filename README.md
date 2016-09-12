# dcode://

This repo describes and implements a URL scheme to share code.

# Link-to-code

A dCode URL represents a location in a codebase.

A dCode handler finds this code on a particular computer and opens it with the user's preferred editor.

URLs can be shared within a team, embedded in documentation, or simply stored as bookmarks.

URLs supports different degrees of precision, allowing to describe a location across code changes, or not.

## Strict mode

A dCode URL that contains a repository URL, commit ID, path, line and column numbers uniquely identifies a location. It may still contain other details for readability and to allow friendly alternative behaviors of handlers.

## Human-friendly mode

URLs may omit all parts but the path. This makes it easy to write them by hand or to generate them from other tools. Handlers should make their best efforts to locate the code that best matches the URL.


# Specification

A dCode URL is composed of a mandatory path and optional repository and file information:

    dcode:// repo_name / path ? repo_spec & code_spec

`path`: the path to a file relative to the root of a project, typically a git repository.

`repo_name`: the common name of the repo, the last part of a repo url and typically the name of the local working directory.

`repo_spec` can indicate version control details, such as branch names and commit ids.

`code_spec` can indicate the location of code inside of a file.

## Repository specification

`git`: a URL that can be interpreted by git. Must be URL-encoded.

`hg`: a URL that can be interpreted by mercurial. Must be URL-encoded.

`commit` or `h`: a specific commit hash.

`branch` or `b`: a branch or tag.

`date` or `d`: a date as YYYY-MM-DD, representing the last commit of the day in UTC, in the specified or the default branch.

## Code specification

`line` or `l`: line number starting at 1.

`column` or `c`: column number starting at 1.

`word` or `w`: one or more words that should appear at the URL location. Several words can be given, separated by commas. This allows handlers to find code across changes.

## Name

A name or comment can be added at the end of URLs like this: `#--Some_name`. This makes links easier to manage.


# Implementation

The current implementation looks for all git or mercurial repositories in the home directory, by default. It can open files at the right place in any code editor. Presets for popular setups are provided.


# Install

    git clone https://github.com/deckardai/dcode.git
    cd dcode
    make build-mac start-mac

This will install the url handler.

You should then be able to click links like this one and end up right in your text editor:

[dcode://dcode/tests/some_file?l=3&c=30](dcode://dcode/tests/some_file?l=3&c=30)
