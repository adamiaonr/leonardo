#!/usr/bin/env python

import os
import sys
import optparse
import urllib
import shutil

from scholar import *
from BeautifulSoup import BeautifulSoup
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

LIBRARY_PROXY = {
    'dl.acm.org': 'dl.acm.org.proxy.library.cmu.edu'
}

def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = file(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()

    try:
        for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
            interpreter.process_page(page)
    except:
        print("exception while reading .pdf file")
        return ""

    # extract the text from the read pages
    text = retstr.getvalue()
    # save it as <filename>.txt
    text_file = open(path.replace(".pdf", ".txt"), "w")
    text_file.write(text)
    text_file.close()

    fp.close()
    device.close()
    retstr.close()

    return text

# taken from http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
def to_camelcase(title):
    s = re.sub(r"[^\w\s]", '', title)
    s = re.sub(r"\s+", '_', s)

    return s.lower()

# in some cases, we get a url to a description webpage, which includes a link 
# to the .pdf file. this function extracts that link.
def extract_link(webpage):

    key = webpage.lstrip("http://").split("/", 1)[0]

    if key in LIBRARY_PROXY:
        webpage = webpage.replace(key, LIBRARY_PROXY[key])

    print(webpage)

    html_page = urllib.urlopen(webpage)
    soup = BeautifulSoup(html_page)
    for link in soup.findAll('a'):
        print link.get('href')

def cleanup_url(url):

    url = url.replace("http://scholar.google.com/", "")
    url = url.replace("https://", "http://")

    return url

def download_articles(articles, output_dir):

    for article in articles:

        # filename derived from title, in camelcase (don't care how long it is)
        title_camelcase = to_camelcase(article.attrs['title'][0]) + ".pdf"
        filename = os.path.join(output_dir, title_camelcase)

        # download the article, save it in output dir
        # with urllib.request.urlopen(article.attrs['url'][0]) as response, open(filename, 'wb') as out_file:
        #     shutil.copyfileobj(response, out_file)
        print(article.attrs['url'][0])
        url = cleanup_url(article.attrs['url'][0])

        print(url)
        print(filename)

        # urllib.urlretrieve(url, filename)

def get_articles(options):

    querier = ScholarQuerier()
    settings = ScholarSettings()

    if options.citation == 'bt':
        settings.set_citation_format(ScholarSettings.CITFORM_BIBTEX)
    elif options.citation == 'en':
        settings.set_citation_format(ScholarSettings.CITFORM_ENDNOTE)
    elif options.citation == 'rm':
        settings.set_citation_format(ScholarSettings.CITFORM_REFMAN)
    elif options.citation == 'rw':
        settings.set_citation_format(ScholarSettings.CITFORM_REFWORKS)
    elif options.citation is not None:
        print('Invalid citation link format, must be one of "bt", "en", "rm", or "rw".')
        return 1

    querier.apply_settings(settings)

    if options.cluster_id:
        query = ClusterScholarQuery(cluster=options.cluster_id)
    else:
        query = SearchScholarQuery()
        if options.author:
            query.set_author(options.author)
        if options.allw:
            query.set_words(options.allw)
        if options.some:
            query.set_words_some(options.some)
        if options.none:
            query.set_words_none(options.none)
        if options.phrase:
            query.set_phrase(options.phrase)
        if options.title_only:
            query.set_scope(True)
        if options.pub:
            query.set_pub(options.pub)
        if options.after or options.before:
            query.set_timeframe(options.after, options.before)
        if options.no_patents:
            query.set_include_patents(False)
        if options.no_citations:
            query.set_include_citations(False)

    if options.count is not None:
        options.count = min(options.count, ScholarConf.MAX_PAGE_RESULTS)
        query.set_num_page_results(options.count)

    if options.offset is not None:
        query.set_offset(options.offset)

    querier.send_query(query)

    return querier

def main():
    usage = """leonardo.py [options] <query string>
text mining on Google Scholar documents. uses scholar.py (https://github.com/ckreibich/scholar.py) 

Examples:

(...)"""

    # parser code adapted from scholar.py (uses optparse)
    fmt = optparse.IndentedHelpFormatter(max_help_position=50, width=100)
    parser = optparse.OptionParser(usage=usage, formatter=fmt)

    # unchanged from scholar.py
    group = optparse.OptionGroup(parser, 'Query arguments',
                                 'These options define search query arguments and parameters.')
    group.add_option('-a', '--author', metavar='AUTHORS', default=None,
                     help='Author name(s)')
    group.add_option('-A', '--all', metavar='WORDS', default=None, dest='allw',
                     help='Results must contain all of these words')
    group.add_option('-s', '--some', metavar='WORDS', default=None,
                     help='Results must contain at least one of these words. Pass arguments in form -s "foo bar baz" for simple words, and -s "a phrase, another phrase" for phrases')
    group.add_option('-n', '--none', metavar='WORDS', default=None,
                     help='Results must contain none of these words. See -s|--some re. formatting')
    group.add_option('-p', '--phrase', metavar='PHRASE', default=None,
                     help='Results must contain exact phrase')
    group.add_option('-t', '--title-only', action='store_true', default=False,
                     help='Search title only')
    group.add_option('-P', '--pub', metavar='PUBLICATIONS', default=None,
                     help='Results must have appeared in this publication')
    group.add_option('--after', metavar='YEAR', default=None,
                     help='Results must have appeared in or after given year')
    group.add_option('--before', metavar='YEAR', default=None,
                     help='Results must have appeared in or before given year')
    group.add_option('--no-patents', action='store_true', default=False,
                     help='Do not include patents in results')
    group.add_option('--no-citations', action='store_true', default=False,
                     help='Do not include citations in results')
    # group.add_option('-C', '--cluster-id', metavar='CLUSTER_ID', default=None,
    #                  help='Do not search, just use articles in given cluster ID')
    group.add_option('-c', '--count', type='int', default=None,
                     help='Maximum number of results')

    # additional option (compared to scholar.py): determines the starting 
    # point for the list of results (default is 0)   
    group.add_option('-o', '--offset', type='int', default=None,
                     help='staring nr. for the search result list. default is 0.')
    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, 'Output format',
                                 'These options control the appearance of the results.')
    # group.add_option('--txt', action='store_true',
    #                  help='Print article data in text format (default)')
    # group.add_option('--txt-globals', action='store_true',
    #                  help='Like --txt, but first print global results too')
    # group.add_option('--csv', action='store_true',
    #                  help='Print article data in CSV form (separator is "|")')
    # group.add_option('--csv-header', action='store_true',
    #                  help='Like --csv, but print header with column names')
    # group.add_option('--citation', metavar='FORMAT', default=None,
    #                  help='Print article details in standard citation format. Argument Must be one of "bt" (BibTeX), "en" (EndNote), "rm" (RefMan), or "rw" (RefWorks).')

    # additional option (compared to scholar.py): self explanatory 
    group.add_option('--output-dir', metavar='OUTPUT_DIR', default=None,
                     help='the output directory for downloaded articles')
    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, 'Miscellaneous')
    group.add_option('--cookie-file', metavar='FILE', default=None,
                     help='File to use for cookie storage. If given, will read any existing cookies if found at startup, and save resulting cookies in the end.')
    group.add_option('-d', '--debug', action='count', default=0,
                     help='Enable verbose logging to stderr. Repeated options increase detail of debug output.')
    group.add_option('-v', '--version', action='store_true', default=False,
                     help='Show version information')
    parser.add_option_group(group)

    options, _ = parser.parse_args()

    # Show help if we have neither keyword search nor author name
    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    if not options.output_dir:
        sys.stderr.write("""leonardo.py : [ERROR] specify an output directory for downloaded articles\n""") 
        parser.print_help()
        return 1

    if options.debug > 0:
        options.debug = min(options.debug, ScholarUtils.LOG_LEVELS['debug'])
        ScholarConf.LOG_LEVEL = options.debug
        ScholarUtils.log('info', 'using log level %d' % ScholarConf.LOG_LEVEL)

    if options.version:
        print('leonardo.py, using scholar.py version %s.' % ScholarConf.VERSION)
        return 0

    if options.cookie_file:
        ScholarConf.COOKIE_JAR_FILE = options.cookie_file

    # # sanity-check the options: if they include a cluster ID query, it
    # # makes no sense to have search arguments:
    # if options.cluster_id is not None:
    #     if options.author or options.allw or options.some or options.none \
    #        or options.phrase or options.title_only or options.pub \
    #        or options.after or options.before:
    #         print('Cluster ID queries do not allow additional search arguments.')
    #         return 1

    # make the query, get the query results
    query_results = get_articles(options)
    if options.debug:
        txt(query_results, with_globals=options.txt_globals)

    # download the .pdf files
    download_articles(query_results.articles, options.output_dir)

    # convert .pdf files to .txt files (requires pdfminer package)
    for pdf_filename in os.listdir(options.output_dir):

        if not pdf_filename.endswith(".pdf"):
            continue

        text = convert_pdf_to_txt(os.path.join(options.output_dir, pdf_filename))

    if options.cookie_file:
        querier.save_cookies()

    return 0

if __name__ == "__main__":
    sys.exit(main())
