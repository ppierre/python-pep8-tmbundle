#!/usr/bin/env python
# encoding: utf-8
"""
textmate_pep8.py

Created by pierre pracht on 2009-03-11.
"""

from __future__ import with_statement

import sys
import getopt
import os
import re
import urllib
import StringIO
import tempfile
import cgi

# =====================================================
# = Adapted from : $TM_SUPPORT_PATH/lib/webpreview.py =
# =====================================================

# fix up path
tm_support_path_default = "/Library/Application Support/TextMate/Support/"
tm_support_path = os.environ.get("TM_SUPPORT_PATH", tm_support_path_default)
tm_support_lib_path = os.path.join(tm_support_path, "lib")
if not tm_support_lib_path in os.environ:
    sys.path.insert(0, tm_support_lib_path)

from tm_helpers import sh, sh_escape

webpreview = sh_escape(os.path.join(
               tm_support_path, "lib/webpreview.sh"))

webpreview_sh = ('export TM_SUPPORT_PATH="%s"; source %s; ' %
                    (tm_support_path, webpreview))


def html_header(title, subtitle):
    return sh(webpreview_sh + 'html_header "%s" "%s"' % (title, subtitle))


def html_footer():
    return sh(webpreview_sh + 'html_footer')

# =======================
# = Fix Bundle sys.path =
# =======================

if 'TM_BUNDLE_PATH' in os.environ:
    tm_bundle_path = os.environ['TM_BUNDLE_PATH']
else:
    tm_bundle_path = os.path.split(
                        os.path.abspath(
                            os.path.dirname(__file__)))[0]

sys.path.append(tm_bundle_path)

from Vendor import pep8

# ==============================================
# = Checker sub-class : Intercept report_error =
# ==============================================

class TxmtChecker(pep8.Checker):
    """Intercept Checker:report_error"""

    def __init__(self, filename, lines=None):
        """Override pep8.Checker.__init__

         - take lines from parameters
         - initialize self.output dict to store error
        """
        # pep8.Checker.__init__(self, filename)

        ## Copy from pep8.Checker.__init__
        self.filename = filename

        if not lines:
            self.lines = file(filename).readlines()
        else:
            # take lines from parameters
            self.lines = lines

        self.physical_checks = pep8.find_checks('physical_line')
        self.logical_checks = pep8.find_checks('logical_line')
        pep8.options.counters['physical lines'] = \
            pep8.options.counters.get('physical lines', 0) + len(self.lines)

        self.output = []

    def report_error(self, line_number, offset, text, check):
        """Report error to a list of structured dict"""
        pep8.Checker.report_error(self, line_number, offset, text, check)

        code_python = (self.lines[line_number - 1]).rstrip()
        code_python_formated = ('%s<span class=caret>%s</span>%s' %
            (cgi.escape(code_python[:offset]),
             cgi.escape(code_python[offset:(offset + 1)]),
             cgi.escape(code_python[(offset + 1):])))

        doc = check.__doc__.lstrip('\n').rstrip()
        self.output.append({
            "lig": line_number, "col": offset,
            "txt": cgi.escape(text),
            "code_python": code_python_formated,
            "pep_list": cgi.escape(doc).splitlines(),
        })


def null_message(text):
    """Replace pep8.py message discarding output"""
    pass

pep8.message = null_message

# ======================================
# = Format pep8.py output for TextMate =
# ======================================

def txmt_pep8(filepath, lines=None, txmt_filename=None):
    """
    Format pep8.py output for TextMate Web preview

    Args :
        filepath: path where to read file
        txmt_filepath : path used for TextMate link
        txmt_filename : displayed filename
    """

    if not txmt_filename:
        txmt_filename = os.path.basename(filepath)

    pep8_errors_list = output_pep8(filepath, lines)

    return format_txmt_pep8(pep8_errors_list, filepath, txmt_filename)


def output_pep8(filepath, lines):
    """Capture pep8.py output"""

    pep8.process_options([
        '--repeat',
        '--show-source',
        '--show-pep8',
        filepath])
    checker = TxmtChecker(filepath, lines)
    errors = checker.check_all()

    return checker.output


def format_txmt_pep8(pep8_errors_list, txmt_filepath, txmt_filename):
    """
    Format pep8.py errors for TextMate Web preview

    Args:
        pep8_errors_list: a list of structured error
        txmt_filepath : path used for TextMate link
        txmt_filename : displayed filename
    """

    url_file = urllib.pathname2url(txmt_filepath)

    output = []

    output.append(html_header("PEP-8 Python", "Python style checker"))

    output.append("<script>")
    txmt_pep8_js = os.path.join(os.path.dirname(__file__), "txmt_pep8.js")
    output.append(file(txmt_pep8_js).read())
    output.append("</script>")
    output.append('''
    <p style="float:right;">
        <input type="checkbox" id="view_source" title="view source"
            onchange="view(this);" checked="checked" />
        <label for="view_source" title="view source">view source</label>
        <input type="checkbox" id="view_pep" title="view PEP"
            onchange="view(this);" checked="checked" />
        <label for="view_pep" title="view PEP">view PEP</label>
    </p>
    <style>
      blockquote.view_pep {margin-bottom:1.5em;}
      .caret {background-color:rgba(255,0,0,0.4);}
    </style>
    ''')

    output.append("<ul>")

    if pep8_errors_list:
        output.append("<h2>File : %s</h2>" % txmt_filename)
    else:
        output.append("<h2>No error on file : %s</h2>" % txmt_filename)

    for error in pep8_errors_list:
        output.append("<li>")

        output.append('<a href="txmt://open/?url=file://%s' % url_file +
                      ('&line=%(lig)s&column=%(col)s">' % error) +
                      ('line:%(lig)s col:%(col)s</a> %(txt)s' % error))

        output.append('<pre class="view_source">%(code_python)s</pre>' % error)

        output.append('<blockquote class="view_pep">')
        for pep_line in error["pep_list"]:
            if len(pep_line) > 0:
                output.append(pep_line)
            else:
                output.append('<br /><br />')
        output.append('</blockquote>')

        output.append("</li>")

    output.append("</ul>")
    output.append(html_footer())

    return "\n".join(output)


help_message = '''
Check Python source code formatting, according to PEP 8
'''


class Usage(Exception):

    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv

    output_filename = None

    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ho:", ["help", "output="])
        except getopt.error, msg:
            raise Usage(msg)

        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-o", "--output"):
                output_filename = value

    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2

    # if no arguments use TextMate variables and read from stdin
    if len(args) == 0:
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(sys.stdin.read())
            tmp_file.flush()
            tmp_filepath = tmp_file.name
            txmt_filepath = os.environ['TM_FILEPATH']
            txmt_filename = os.environ['TM_FILENAME']
            output = txmt_pep8(txmt_filepath, file(tmp_filepath).readlines(), txmt_filename)
    else:
        # TODO: process multiple files
        filepath = args[0]
        output = txmt_pep8(filepath)

    if output_filename:
        output_file = open(output_filename, 'w')
        output_file.write(output)
        output_file.close()
    else:
        print(output)

if __name__ == "__main__":
    sys.exit(main())
