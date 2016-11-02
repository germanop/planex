"""
planex-chroot: Start a docker container for developer builds of
packages.
"""

import argparse
import logging
import os
import pipes
import subprocess
import getpass
import sys
import tempfile

from pkg_resources import resource_filename
from os import remove
from uuid import uuid4

import argcomplete
import planex
import planex.spec
import planex.util

def create_mock_custom_file(repodata, custom_mock_repos):
    """Write mock-custom to disk"""
    with open(repodata['xs-repo']) as _xs_repo_f:
        default_repos = _xs_repo_f.read()

    with open(repodata['mock-default-cfg']) as _default_cfg_f:
        _mock_custom = _default_cfg_f.read().format(
            defaults=default_repos,
            custom="\n".join(custom_mock_repos)
            )
        with open('mock-custom', 'w') as mock_custom_f:
            mock_custom_f.write(_mock_custom)

    print "Generate custom mockfile on disk: done."

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

def generate_repodata(args):
    """Generate data for custom repos in mock and yum"""

    # this will have to be made more modular
    repodata = {
        'yum-conf': resource_filename(__name__, 'yum.conf'),
        'xs-repo': resource_filename(__name__, 'xs.repo'),
        'mock-default-cfg': resource_filename(__name__, 'default.cfg'),
        'logging-ini': resource_filename(__name__, 'logging.ini'),
        'site-defaults-cfg': resource_filename(__name__, 'site_defaults.cfg')
    }

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
        # TODO: check that the url is absolute
        _baseurl = "file://%s" % args.local
        dockerfile_repos.append("RUN yum-config-manager -y --add-repo %s" % _baseurl)
        mock_repos.append(new_repo_template.format(name="local", baseurl=_baseurl))

    for repo_url in args.remote:
        dockerfile_repos.append("RUN yum-config-manager -y --add-repo %s" % repo_url)
        # TODO: infer a decent sanitised string as a name
        mock_repos.append(new_repo_template.format(name=uuid4().hex[:5], baseurl=repo_url))
    
    repodata['yum-custom'] = "\n".join(dockerfile_repos)

    create_mock_custom_file(repodata, mock_repos)
    
    print "Generate repository data: done."

    return repodata


def build_container(args):
    """Creates the Dockerfile and run the container"""
    data = generate_repodata(args)
    data['maintainer'] = getpass.getuser()

    build_deps = []
    for spec in args.package:
        build_deps.append("RUN yum-builddep -y %s" % spec)
    data['build-deps'] = "\n".join(build_deps)

    with open(resource_filename(__name__, 'Dockerfile')) as dockerfile_template_f:
        with tempfile.NamedTemporaryFile(dir=".") as dockerfile_f:
            dockerfile_f.write(dockerfile_template_f.read().format(**data))
            dockerfile_f.flush()

            print "Create Dockerfile on disk: done."
            print "Please wait while the image is generated"

            planex.util.run(["docker", "build", "-t", "planex-%s-%s" % (user, package),
                             "--force-rm=true", "-f", dockerfile.name, "."])
    
    # container has been created, we can remove mock-custom
    # TODO: use a global temp folder instead, and delete it after generation is complete
    remove('mock-custom')


def start_container(args):
    """
    Start the docker container with the source directories availble.
    """
    path_maps = []

    for package in args.package:
        # Getting from _build for now.
        spec = planex.spec.Spec(package)
        path_maps.append(("myrepos/%s" % (spec.name()),
                          "/build/rpmbuild/BUILD/%s-%s"
                          % (spec.name(), spec.version())))

    path_maps.append(("../planex", "/build/myrepos/planex"))

    suffix = args.suffix if args.suffix is not None else uuid4().hex[:5]
    
    print("Starting the container")

    really_start_container("planex-%s-%s" % (getpass.getuser(), suffix),
                                path_maps, ("bash",))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="""
    Start a docker container for developer builds of packages.
    """)
    planex.util.add_common_parser_options(parser)
    parser.add_argument("package", nargs="*", default = [],
                        help="path to specfile whose build dependencies should be installed in container")
    parser.add_argument("--local",
                        help="absolute path to the local repo (gpgcheck disabled)")
    parser.add_argument("--remote", action="append", default=[],
                        help="uri of the remote repo (gpgcheck disabled)")
    parser.add_argument("--suffix",
                        help="container name suffix")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Entry point
    """
    planex.util.setup_sigint_handler()
    args = parse_args_or_exit(argv)
    planex.util.setup_logging(args)
    build_container(args)
    start_container(args)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
