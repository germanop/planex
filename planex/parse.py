"""
planex-parse: Spit out spec files with correct download URLs
"""

import argparse
import json
import sys
import shutil
import re
import fileinput

import argcomplete
import pkg_resources

from planex.util import add_common_parser_options
from planex.util import run
from planex.util import setup_logging
from planex.util import setup_sigint_handler
import planex.spec


class ParseException(Exception):
    def __init__(self, exc):
        super(ParseException, self).__init__("%s" % exc)
        

def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Create proper spec files')
    add_common_parser_options(parser)
    parser.add_argument('spec_or_link', metavar='SRC', help='RPM Spec or'
                        ' link file')
    parser.add_argument('newspec', metavar='DEST',
                        help="Destination spec file")
    parser.add_argument('--branch', metavar='repo branch', nargs='?',
                        help='repository branch')
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def replace_url(tags):

    new_url = ""

    # Ensure we have enough info for a URL
    if tags['repo'] == None:
        raise ParseException("No info about repo")

    base_repo = r"https://code.citrite.net/rest/archive/latest/projects/"\
                 "XS/repos/{0}/archive?at=".format(tags['repo'])

    if tags['tag'] != None:
        new_url = base_repo+r"{0}&format=tar.gz".format(tags['tag'])
    else:
        new_url = base_repo+r"{0}&format=tar.gz".format(tags['branch'])
    return new_url

def parse_spec(args):

    infile = args.spec_or_link
    outfile = args.newspec
    tmpfile = outfile+".bak"

    try:
        shutil.copy2(infile, tmpfile)
    except Exception as e:
        raise ParseException(e)

    regexps = {'repo': re.compile('^#XSrepo:\s*(\S+)'),
               'tag': re.compile('^#XStag:\s*(\S+)'),
               'branch': re.compile('^#XSbranch:\s*(\S+)'),
               'exit': re.compile('^Source0:\s*(\S+)#/(\S+)')
              }
    # Set defaults tags for a spec file
    tags = {'repo': r"%{name}", 'tag': r"v%{version}", 'branch': "master"}

    for line in fileinput.input(tmpfile, inplace=1):
        for key, regexp in regexps.items():
            match = re.match(regexp, line)
            if match:
                if key == "exit":
                    print("Source0: {}#/{}".format(replace_url(tags),
                                                   match.group(2)))
                    regexps.clear()
                    break
                if key == "branch":
                    # We want explicitly to use HEAD and not 'tag'
                    tags['tag'] = None # No default
                    if args.branch:
                        tags['branch'] = args.branch
                else:
                    tags[key] = match.group(1)
                del regexps[key]
                break
        else: # for
            print line,

    try:
        shutil.move(tmpfile, outfile)
    except Exception as e:
        raise ParseException(e)


def parse_link(args):

    infile = args.spec_or_link
    outfile = args.newspec

    try:
        with open(infile) as lnkfile:
            json_dict = json.load(lnkfile)
    except Exception as e:
        raise ParseException(e)

    # Set default tags for a lnk file
    tags = {'repo': None, 'tag': None, 'branch': None}

    if 'repo' in json_dict:
        tags['repo'] = json_dict['repo']

    # If we have 'tag' we do not care about 'branch'.
    # If we don't, then it is branch from:
    # command line, json file, master
    if 'tag' in json_dict:
        tags['tag'] = json_dict['tag']
    elif args.branch:
        tags['branch'] = args.branch
    elif 'branch' in json_dict:
        tags['branch'] = json_dict['branch']
    else:
        tags['branch'] = 'master'

    json_dict['URL'] = replace_url(tags)

    # We don't want branch in output lnk file because
    # other progs could use to override
    json_dict.pop('branch', None)

    try:
        with open(outfile, mode='w') as outf:
            json.dump(json_dict, outf, indent=4)
    except Exception as e:
        raise ParseException(e)


def main(argv):
    """
    Main function.  Parse spec or link files.
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    if args.spec_or_link.endswith('.spec'):
        try:
            parse_spec(args)
        except ParseException as e:
            sys.exit("{}: {}\n".format(sys.argv[0], e))
    elif args.spec_or_link.endswith('.lnk'):
        parse_link(args)
    else:
        sys.exit("%s: Unsupported file type: %s" % (sys.argv[0],
                                                    args.spec_or_link))


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])


# Entry point when run directly
if __name__ == "__main__":
    _main()
