"""
Wrappers and utility functions for dealing with git repositories
"""

import os
import re

from planex.util import run


def dotgitdir_of_path(repo):
    """
    Return the path to the dotgitdir of the repository.

    Possible paths: <repo>/.git, <repo> or <repo>.git

    """

    # We often have bare repos checked out, e.g. /path/to/xen-api.git,
    # which doesn't contain a '.git' dir inside. We want to support
    # specifying this by only by providing the path to the repo, or by
    # just specifying 'xen-api' and having this function check for
    # 'xen-api.git'
    possibilities = [os.path.join(repo, ".git"),
                     repo,
                     repo + ".git"]
    matches = [x for x in possibilities if
               os.path.exists(os.path.join(x, "HEAD"))]
    if matches:
        return matches[0]
    else:
        raise Exception("Not a git repository: '%s'" % repo)


def describe(repo, treeish="HEAD"):
    """
    Return an RPM compatible version string for a git repo at a given commit
    """
    dotgitdir = dotgitdir_of_path(repo)

    # First, get the hash of the commit
    cmd = ["git", "--git-dir=%s" % dotgitdir, "rev-parse", treeish]
    sha = run(cmd)['stdout'].strip()

    # Now lets describe that hash
    cmd = ["git", "--git-dir=%s" % dotgitdir, "describe", "--tags", sha]
    description = run(cmd, check=False)['stdout'].strip()

    # if there are no tags, use the number of commits
    if description == "":
        cmd = ["git", "--git-dir=%s" % dotgitdir, "log", "--oneline", sha]
        commits = run(cmd)['stdout'].strip()
        description = str(len(commits.splitlines()))

    # replace '-' with '+' in description to not confuse rpm
    match = re.search("[^0-9]*", description)
    matchlen = len(match.group())
    return description[matchlen:].replace('-', '+')


def archive(repo, commit_hash, prefix, target_dir):
    """
    Archive a git repo at a given commit with a specified version prefix.
    Returns the path to a tar.gz to be used as a source for building an RPM.
    """
    dotgitdir = dotgitdir_of_path(repo)

    prefix = "%s-%s" % (os.path.basename(repo), prefix)
    path = os.path.join(target_dir, "%s.tar" % prefix)

    run(["git", "--git-dir=%s" % dotgitdir, "archive", commit_hash,
         "--prefix=%s/" % prefix, "-o", path])
    run(["gzip", "--no-name", "-f", path])

    return path + ".gz"


def tags(repo):
    """
    Return a list of all tags defined on repo.
    """
    dotgitdir = dotgitdir_of_path(repo)
    return run(["git", "--git-dir=%s" % dotgitdir, "tag"])['stdout'].split()


def format_patch(repo, startref, endref, target_dir):
    """
    Write patches from ref to HEAD out to target_dir.
    Returns a list of patch filenames which can be used to create a
    series file.
    """
    dotgitdir = dotgitdir_of_path(repo)

    commit_range = "%s..%s" % (startref, endref)
    res = run(["git", "--git-dir=%s" % dotgitdir, "format-patch",
               "--no-renames", commit_range, "--output-directory", target_dir])
    return res['stdout'].split()
