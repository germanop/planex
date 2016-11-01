"""planex-make: Developer builds of packages.

Sub-commands:

builddep <package>

  Install package build dependencies (with yum-builddep)

build <package>

  Build the package using the %build stanza from the spec file.

install <package>

  Install the packages using the %install stanza from the spec file.

package <package> [<host>...]

  Install and then produce RPM packages, using existing build
  output. Optionally, (force) installs the packages on one or more
  hosts.

rsync <package> <host>...

  Install and then rsync the install products to one or more hosts.

bip <package> [<host>...]

  Build, install, and package.

bir <package> <host>...

  Build, install, and rsync.
"""
import argparse
import sys

import argcomplete

import planex
import planex.spec
import planex.util


def cmd_builddep(spec, args):
    print "builddep"
    #planex.util.run(["yum-builddep", spec.path])
    
    #
    # Ewww. rpmbuild gets upset if SourceN doesn't exist even if doing
    # short circuit build.  Add empty/dummy sources to keep it happy.
    #
    for source in spec.source_paths():
        planex.util.run(["tar", "-caf", source, "--files-from=/dev/null"])


def cmd_build(spec, args):
    print "build"
    # rpmbuild -bc --short-circuit <spec>
    planex.util.run(["rpmbuild", "-bc", "--short-circuit", spec.path])


def cmd_install(spec, args):
    print "install"
    planex.util.run(["rpmbuild", "-bi", "--short-circuit", spec.path])


def cmd_package(spec, args):
    cmd_install(spec, args)
    print "package"
    # rpmbuild -bb --short-circuit <spec>
    # scp <rpm> <host>
    # ssh <host> rpm --upgrade --nodeps <rpm>
    planex.util.run(["rpmbuild", "-bb", "--short-circuit", spec.path])


def cmd_rsync(spec, args):
    cmd_install(spec, args)
    print "rsync"
    # rsync -R <buildroot> <host>:/ (using ssh)


def cmd_bip(spec, args):
    cmd_build(spec, args)
    cmd_package(spec, args)


def cmd_bir(spec, args):
    cmd_build(spec, args)
    cmd_rsync(spec, args)


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description="""
    Build a package incrementally, and install the result.
    """)
    planex.util.add_common_parser_options(parser)
    subparsers = parser.add_subparsers()

    builddep_parser = subparsers.add_parser("builddep");
    builddep_parser.add_argument("package", help="package name")
    builddep_parser.set_defaults(cmd=cmd_builddep)
    
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("package", help="package name")
    build_parser.set_defaults(cmd=cmd_build)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("package", help="package name")
    install_parser.set_defaults(cmd=cmd_install)

    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("package", help="package name")
    package_parser.add_argument("host", nargs="*", help="installation host")
    package_parser.set_defaults(cmd=cmd_package)

    rsync_parser = subparsers.add_parser("rsync", description="""
    Copy the installation contents to hosts
    """)
    rsync_parser.add_argument("package", help="package name")
    rsync_parser.add_argument("host", nargs="+", help="installation host")
    rsync_parser.set_defaults(cmd=cmd_rsync)

    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv):
    """
    Entry point
    """
    planex.util.setup_sigint_handler()
    args = parse_args_or_exit(argv)

    spec_file = "./%s.spec" % (args.package)
    spec = planex.spec.Spec(spec_file)

    args.cmd(spec, args)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
