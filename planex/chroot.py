"""
planex-chroot: Start a docker container for developer builds of
packages.
"""
from __future__ import print_function

import argparse
import logging
import os
import pipes
import subprocess
import getpass
import sys
import tempfile

from os import mkdir, path
from shutil import copy, rmtree
from uuid import uuid4

import argcomplete
import planex
import planex.spec
import planex.util

from pkg_resources import resource_filename

# TODO:
#  - generate git config in the repo  <-- bad idea. The user should work from own
#  - use correct guilt version        <-- (external) environment and use the
#                                         container only for compilation and test
#  - prepare SOURCES content
#  - fix local repo
#  - improve planex-make to be able to shortcircuit the RPM creation
#  - ???

def copy_configuration_templates(tempdir):
    """
    Copy template files that need to be included in the docker image
    """

    copy(resource_filename(__name__, 'yum.conf'), '%s/yum.conf' % tempdir)
    copy(resource_filename(__name__, 'xs.repo'), '%s/xs.repo' % tempdir)
    copy(resource_filename(__name__, 'logging.ini'), '%s/logging.ini' % tempdir)
    copy(resource_filename(__name__, 'site-defaults.cfg'), '%s/site-defaults.cfg' % tempdir)

    print("Template files copied")


def prepare_specfiles(args, tempdir):
    """
    Creates a SPECS folder in the tempdir that is mounted in the container
    in the folder /SPECS
    """

    # We do not try..except OSError because the folder should not be present yet
    specdir = "%s/SPECS" % tempdir
    mkdir(specdir)

    for specfile in args.package:
        specname = path.basename(specfile)
        copy(specfile, "%s/%s" % (specdir, specname))

    print("SPECS folder generated")


def create_custom_mock_config(tempdir, custom_mock_repos):
    """
    Write mock-custom to disk
    """
    with open(resource_filename(__name__, 'xs.repo')) as _xs_repo_f:
        default_repos = _xs_repo_f.read()

    with open(resource_filename(__name__, 'default.cfg')) as _default_cfg_f:
        _mock_custom = _default_cfg_f.read().format(
            defaults=default_repos,
            custom="\n".join(custom_mock_repos)
            )
        with open('%s/default.cfg' % tempdir, 'w') as mock_custom_f:
            mock_custom_f.write(_mock_custom)

    print("Generate custom mockfile on disk: done.")


def really_start_container(container_name, path_maps, command):
    """
    Start the planex docker container.
    """

    # Add standard path maps
    path_maps.append((os.getcwd() + "/_obj/var/cache/mock", "/var/cache/mock"))
    path_maps.append((os.getcwd() + "/_obj/var/cache/yum", "/var/cache/yum"))
    path_maps.append((os.getcwd(), "/build"))

    cmd = ["docker", "run", "--privileged", "--rm", "-i", "-t"]

    for (local, container) in path_maps:
        cmd += ("-v", "%s:%s" % (os.path.realpath(local), container))

    cmd += (container_name,)
    cmd += command

    logging.debug("running command: %s",
                  (" ".join([pipes.quote(word) for word in cmd])))
    subprocess.call(cmd)


def generate_repodata(args, data):
    """
    Generate data for custom repos in mock and yum
    """

    # do not indent or it fails to be a valid repository entry
    new_repo_template = """
[{name}]
name = {name}
gpgcheck = 0
enabled = 1
baseurl = {baseurl}
"""

    dockerfile_repos = []
    mock_repos = []

    if args.local:
        # TODO: hardlink the local repo in the current folder and mount it in
        #       the local /REPOS folder
        _baseurl = "file://%s" % args.local
        dockerfile_repos.append("RUN yum-config-manager -y --add-repo %s" % _baseurl)
        mock_repos.append(new_repo_template.format(name="local", baseurl=_baseurl))

    for repo_url in args.remote:
        dockerfile_repos.append("RUN yum-config-manager -y --add-repo %s" % repo_url)
        mock_repos.append(new_repo_template.format(name=uuid4().hex[:5], baseurl=repo_url))

    data['yum-custom'] = "\n".join(dockerfile_repos)

    create_custom_mock_config(data['tempdir'], mock_repos)

    print("Generate repository data: done.")

    return data


def add_guilt(flag):
    """
    Install guilt in the container if flag is true
    """
    # TODO: this should also create a .gitconfig for the container with
    #       the user's git user/email or add an ENV to create it in entry.sh

    guilt_docker_template = """
WORKDIR /tmp
RUN git clone git://repo.or.cz/guilt.git && \
    cd guilt && \
    make && \
    make install && \
    cd .. && \
    rm -R -f guilt
"""

    return guilt_docker_template if flag else ""


def build_container(args, tempdir, suffix):
    """
    Creates the Dockerfile and build the container. Return the container name
    """
    data = {'tempdir': tempdir}
    data = generate_repodata(args, data)
    data['add-guilt'] = add_guilt(args.guilt)
    data['maintainer'] = user = getpass.getuser()

    build_deps = []
    for spec in args.package:
        build_deps.append("RUN yum-builddep -y %s" % spec)
    data['build-deps'] = "\n".join(build_deps)

    with open(resource_filename(__name__, 'Dockerfile')) as dockerfile_template_f:
        with open("%s/Dockerfile" % tempdir, "w") as dockerfile_f:
            dockerfile_f.write(dockerfile_template_f.read().format(**data))
        print("Create Dockerfile on disk: done.")

    container_name = "planex-%s-%s" % (user, suffix)
    print("Please wait while '%s' is generated" % container_name)

    planex.util.run(["docker", "build", "-t", container_name,
                     "--force-rm=true", "-f", "%s/Dockerfile" % tempdir, "."])
    return container_name


def start_container(container_name):
    """
    Start the docker container.
    """
    path_maps = []
    print("Starting container '%s'..." % container_name)
    really_start_container(container_name, path_maps, ("bash",))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="""
    Start a docker container for developer builds of packages.
    """)

    planex.util.add_common_parser_options(parser)
    subparsers = parser.add_subparsers()

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("container", default=None,
                            help="name of an existing docker image to run")

    new_parser = subparsers.add_parser("new")
    new_parser.add_argument("package", nargs="*",
                            help="path to specfile whose build dependencies \
                                should be installed in container")
    new_parser.add_argument("--local",
                            help="absolute path to the local repo \
                                (gpgcheck disabled)")
    new_parser.add_argument("--remote", action="append", default=[],
                            help="uri of the remote repo (gpgcheck disabled)")
    new_parser.add_argument("--suffix",
                            help="container name suffix")
    new_parser.add_argument("--keeptmp", action="store_true", default=False,
                            help="keep temporary files")
    new_parser.add_argument("--guilt", action="store_true", default=False,
                            help="install guilt in the chroot (git config is \
                                not yet generated) [likely to be deprecated \
                                in the near future]")

    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Entry point
    """

    planex.util.setup_sigint_handler()
    args = parse_args_or_exit(argv)
    planex.util.setup_logging(args)

    try:
        if args.container is not None:
            suffix = args.suffix if args.suffix is not None else uuid4().hex[:5]
            tempdir = tempfile.mkdtemp(dir=".")
            prepare_specfiles(args, tempdir)
            copy_configuration_templates(tempdir)
            container_name = build_container(args, tempdir, suffix)
        else:
            container_name = args.container
        start_container(container_name)
    except Exception as exn:
        print("Something went wrong: %s" % str(exn))
    finally:
        if args.container is not None:
            if not args.keeptmp:
                print("Cleaning up temp dirs")
                rmtree(tempdir)
            else:
                print("--keeptmp flag detected. \
                       The template files can be found in %s" % tempdir)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
