"""
planex-chroot: Start a docker container for developer builds of
packages.
"""

import argparse
import getpass
import sys
import tempfile

import argcomplete

import planex
import planex.spec
import planex.util


def build_container(args):
    user = getpass.getuser()
    package = args.package[0]
    
    dockerfile = tempfile.NamedTemporaryFile(dir=".")
    dockerfile.write(
    """
    FROM planex-%s
    MAINTAINER %s

    RUN yum-builddep -y _build/SPECS/%s.spec
    """
    % (user, user, package))
    dockerfile.flush()

    planex.util.run(["docker", "build", "-t", "planex-%s-%s" % (user, package),
                     "--force-rm=true", "-f", dockerfile.name, "."])

    dockerfile.close()

def start_container(args):
    """
    Start the docker container with the source directories availble.
    """
    path_maps = []

    for package in args.package:
        # Getting from _build for now.
        spec = planex.spec.Spec("_build/SPECS/%s.spec" % (package))
        path_maps.append(("myrepos/%s" % (spec.name()),
                          "/build/rpmbuild/BUILD/%s-%s"
                          % (spec.name(), spec.version())))

    path_maps.append(("../planex", "/build/myrepos/planex"))

    planex.util.start_container("planex-%s-%s" % (getpass.getuser(), args.package[0]),
                                path_maps, ("bash",))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="""
    Start a docker container for developer builds of packages.
    """)
    planex.util.add_common_parser_options(parser)
    parser.add_argument("package", nargs="+",
                        help="source to include in container")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Entry point
    """
    planex.util.setup_sigint_handler()
    args = parse_args_or_exit(argv)
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
