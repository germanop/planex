# Run these tests with 'nosetests':
#   install the 'python-nose' package (Fedora/CentOS or Ubuntu)
#   run 'nosetests' in the root of the repository

import glob
import os
import sys
import unittest

import planex.spec
import planex.depend


class BasicTests(unittest.TestCase):
    # unittest.TestCase has more methods than Pylint permits
    # pylint: disable=R0904
    def setUp(self):
        rpm_defines = [("dist", ".el6"),
                       ("_topdir", "_build"),
                       ("_sourcedir", "%_topdir/SOURCES/%name")]
        self.spec = planex.spec.Spec("tests/data/ocaml-cohttp.spec",
                                     defines=rpm_defines)

    def test_build_srpm_from_spec(self):
        planex.depend.build_srpm_from_spec(self.spec)

        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "tests/data/ocaml-cohttp.spec\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "./MANIFESTS/ocaml-cohttp.json\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "_build/SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz\n"
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm: "
            "SOURCES/ocaml-cohttp/ocaml-cohttp-init\n")

    def test_download_rpm_sources(self):
        planex.depend.download_rpm_sources(self.spec)

        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz: "
            "tests/data/ocaml-cohttp.spec\n")

    def test_build_rpm_from_srpm(self):
        planex.depend.build_rpm_from_srpm(self.spec)

        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/RPMS/x86_64/ocaml-cohttp-devel-0.9.8-1.el6.x86_64.rpm: "
            "_build/SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm\n")

    def test_buildrequires_for_rpm(self):
        # N.B. buildrequires_for_rpm only generates rules for other packages
        # defined by local spec files.   Even though ocaml-cohttp depends on
        # other packages, the test data directory contains only ocaml-uri and
        # ocaml-cstruct.
        spec_paths = glob.glob(os.path.join("tests/data", "ocaml-*.spec"))
        specs = [planex.spec.Spec(spec_path, defines=[('dist', '.el6')])
                 for spec_path in spec_paths]

        planex.depend.buildrequires_for_rpm(
            self.spec, planex.depend.package_to_rpm_map(specs))

        self.assertEqual(
            sys.stdout.getvalue(),
            "_build/RPMS/x86_64/ocaml-cohttp-devel-0.9.8-1.el6.x86_64.rpm: "
            "_build/RPMS/x86_64/ocaml-uri-devel-1.6.0-1.el6.x86_64.rpm\n"
            "_build/RPMS/x86_64/ocaml-cohttp-devel-0.9.8-1.el6.x86_64.rpm: "
            "_build/RPMS/x86_64/ocaml-cstruct-devel-1.4.0-1.el6.x86_64.rpm\n")
