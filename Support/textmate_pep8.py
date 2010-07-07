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
import string

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

tm_ruby = os.environ.get("TM_RUBY", "ruby")


def html_header(page_title, sub_title, window_title=None):
    if not window_title:
        window_title = page_title
    sys.stdout.flush()
    return sh("""
    export TM_SUPPORT_PATH="%(tm_support_path)s"
    "%(tm_ruby)s" -r"%(tm_support_path)s/lib/web_preview.rb" <<-'RUBY'
    puts html_head(
        :window_title   => "%(window_title)s",
        :page_title     => "%(page_title)s",
        :sub_title      => "%(sub_title)s"
    )
RUBY
    """ % {
        "tm_ruby": tm_ruby,
        "tm_support_path": tm_support_path,
        "window_title": window_title,
        "page_title": page_title,
        "sub_title": sub_title,
    })

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

    def report_all_on(self, html_out):
        """Fix html_out and launch check_all"""
        self.html_out = html_out
        self.check_all()

    def report_error(self, line_number, offset, text, check):
        """Report error to html_out function"""
        pep8.Checker.report_error(self, line_number, offset, text, check)

        code_python = (self.lines[line_number - 1]).rstrip()
        code_python_formated = ('%s<span class=caret>%s</span>%s' %
            (cgi.escape(code_python[:offset]),
             cgi.escape(code_python[offset:(offset + 1)]),
             cgi.escape(code_python[(offset + 1):])))

        doc = check.__doc__.lstrip('\n').rstrip()
        self.html_out({
            "lig": line_number, "col": offset,
            "txt_code": cgi.escape(text[:4]),
            "txt_msg": cgi.escape(text[5:]),
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

class FormatTxmtPep8(object):
    """
    Build HTML output for TextMate preview.

    Take : file descriptor for output
    Give : method render each errorBuild HTML output for TextMate preview.
    """

    header_tpl = string.Template('''
    %(html_header)s
        <script src="file://%(script_src)s"
            type="text/javascript" charset="utf-8">
        </script>
        <p style="float:right;">
            <input type="checkbox" id="view_source" title="view source"
                onchange="view(this);" checked="checked" /><label
             for="view_source" title="view source"> view source</label>
            <input type="checkbox" id="view_pep" title="view PEP"
                onchange="view(this);" checked="checked" /><label
             for="view_pep" title="view PEP"> view PEP</label>
            <br />
            <label for="filter_codes"
                title="list of error code to hide">hide :</label>
            <input type="text" id="filter_codes" value="" size="22"
                placeholder="list of error code"
                title="list of error code to hide"
                onkeyup="update_list();"/>
        </p>
        <h2>File : ${txmt_filename}</h2>
            <ul>
        ''' % {
            "html_header": html_header("PEP-8 Python", "Python style checker"),
            "script_src": urllib.pathname2url(os.path.join(
                                os.path.dirname(__file__), "txmt_pep8.js")),
        })

    error_tpl = string.Template('''
            <li class="${txt_code}">
                <code><a href="txmt://open/?url=file://${url_file}\
&line=${lig}&column=${col}">${position}</a></code>
                   <code><i>${txt_code}</i></code> : ${txt_msg}
                <pre class="view_source">${code_python}</pre>
                <blockquote class="view_pep">
                    ${pep_html}
                </blockquote>
            </li>
        ''')

    footer_tpl = string.Template('''
            </ul>
            <p>&nbsp;</p>
            <div class="alternate">
                ${alternate}
            </div>
        </div>
        </body>
        </html>
        ''')

    def _statistics_iter(self, iter):
        yield "<ul>"
        for key in iter:
            yield """
            <li>
                <code><b>%4d</b>    </code>
                <code><i>%s</i></code>
                : %s
            </li>
            """ % key
        yield "</ul>"

    def __init__(self, txmt_filepath, txmt_filename, out):

        self.txmt_filepath = txmt_filepath
        self.txmt_filename = txmt_filename
        self.out = out

        self.url_file = urllib.pathname2url(txmt_filepath)
        self.error = False

    def _write(self, tpl, values):
        """Write on out file descriptor"""
        self.out.write(tpl.substitute(values))

    def __enter__(self):
        """Build header of HTML page"""

        self._write(self.header_tpl, {
            "txmt_filename": cgi.escape(self.txmt_filename),
        })

        return self.__call__

    def __call__(self, error):
        """Render an error"""
        self.error = True

        self._write(self.error_tpl, dict(error,
            url_file=self.url_file,
            position="<b>%4d</b>:%-3d" % (error["lig"], error["col"]),
            pep_html="\n".join(line if len(line) > 0 else '<br /><br />'
                                for line in error["pep_list"])))

    def __exit__(self, type, value, traceback):
        """Build footer of HTML page"""
        if self.error:
            alternate = "\n".join(self._statistics_iter(
                            (
                                pep8.options.counters[key],
                                cgi.escape(key),
                                cgi.escape(pep8.options.messages[key]),
                            )
                            for key in sorted(pep8.options.messages)
                        ))
        else:
            alternate = '<h2>No error</h2>'
        self._write(self.footer_tpl, {
        "alternate": alternate,
        })


help_message = '''
Check Python source code formatting, according to PEP 8
'''


class Usage(Exception):

    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv

    output_name = None

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
                output_name = value

    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2

    with open(output_name, 'w') if output_name else sys.stdout as f_out:
        with open(args[0]) if args else sys.stdin as f_in:
            filepath = os.environ.get('TM_FILEPATH', None) or args[0]
            filename = os.environ.get('TM_FILENAME',
                                        os.path.basename(filepath))
            pep8.process_options([
                '--repeat',
                '--show-source',
                '--show-pep8',
                filename])
            with FormatTxmtPep8(filepath, filename, f_out) as html_out:
                TxmtChecker(filepath, f_in.readlines()).report_all_on(html_out)


if __name__ == "__main__":
    sys.exit(main())
