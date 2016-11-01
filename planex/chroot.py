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


YUM_CONF_CITRIX="""
[main]
cachedir=/tmp/yum
keepcache=0
debuglevel=2
logfile=/var/log/yum.log
exactarch=1
obsoletes=1
gpgcheck=0
plugins=1
installonly_limit=3
reposdir=/etc/yum.repos.d.xs
"""

XS_REPO_CITRIX="""
[epel]
name = epel
enabled = 1
baseurl = https://repo.citrite.net/fedora/epel/7/x86_64/
exclude = ocaml*
gpgcheck = 0
[base]
name = base
enabled = 1
baseurl = https://repo.citrite.net/centos/7.2.1511/os/x86_64/
exclude = ocaml*
gpgcheck = 0
[updates]
name = updates
enabled = 1
baseurl = https://repo.citrite.net/centos/7.2.1511/os/x86_64/
exclude = ocaml*
gpgcheck = 0
[extras]
name = extras
enabled = 1
baseurl = https://repo.citrite.net/centos/7.2.1511/os/x86_64/
exclude = ocaml*
gpgcheck = 0
"""

def generate_repodata(args):
    dockerfile_repo = []
    if args.override:
        # this is probably not going to be dynamic
        with open("yum.conf.custom", "w") as yum_conf:
            yum_conf.write(YUM_CONF_CITRIX)
        dockerfile_repo.append("COPY yum.conf.custom /etc/yum.conf")
        
        with open("xs.repo", "w") as repo_conf:
            repo_conf.write(XS_REPO_CITRIX)
        dockerfile_repo.append("COPY xs.repo /etc/yum.repos.d.xs/xs.repo")
    
    # note that we should probably use planex-cache cachedirs syntax...
    if args.local:
        # TODO: check that the url is absolute
        dockerfile_repo.append("RUN yum-config-manager --add-repo file://%s" % args.local)

    for repo in args.remote:
        dockerfile_repo.append("RUN yum-config-manager --add-repo {}" % repo)
    
    return "\n".join(dockerfile_repo)


def build_container(args):
    user = getpass.getuser()
    package = args.package[0]
    repodata = generate_repodata(args)
    
    dockerfile = tempfile.NamedTemporaryFile(dir=".")
    dockerfile.write("""
FROM xenserver/planex
MAINTAINER %s

# yum repo customization
%s

# install guilt
WORKDIR /tmp
RUN git clone git://repo.or.cz/guilt.git && \
    cd guilt && \
    make && \
    make install && \
    cd .. && \
    rm -R -f guilt

    ENV XSDEVHOME=/build/myrepos/%s

# RUN yum-builddep -y /myrepos/%s/xsdevbuild/%s.spec
""" % (user, repodata, package, package, package))

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
    parser.add_argument("--override", action="store_true",
                        help="replace official yum repos with citrix internal ones (gpgcheck disabled)")
    parser.add_argument("--local",
                        help="absolute path to the local repo (gpgcheck disabled)")
    parser.add_argument("--remote", action="append", default=[],
                        help="uri of the remote repo (gpgcheck disabled)")
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
