# Makefile for Sphinx documentation

# You can set these variables from the command line.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
PAPER         ?=
BUILDDIR      ?= build

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) source

.PHONY: help clean html dirhtml singlehtml pickle json htmlhelp qthelp devhelp epub latex latexpdf text man changes linkcheck doctest gettext livehtml

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html       to make standalone HTML files"
	@echo "  dirhtml    to make HTML files named index.html in directories"
	@echo "  singlehtml to make a single large HTML file"
	@echo "  pickle     to make pickle files"
	@echo "  json       to make JSON files"
	@echo "  htmlhelp   to make HTML files and a HTML help project"
	@echo "  qthelp     to make HTML files and a qthelp project"
	@echo "  devhelp    to make HTML files and a Devhelp project"
	@echo "  epub       to make an EPUB file"
	@echo "  latex      to make LaTeX files, you can set PAPER=a4 or PAPER=letter"
	@echo "  latexpdf   to make LaTeX files and run them through pdflatex"
	@echo "  latexpdfja to make LaTeX files and run them through platex and dvipdfmx"
	@echo "  text       to make text files"
	@echo "  man        to make manual pages"
	@echo "  texinfo    to make Texinfo files"
	@echo "  gettext    to make PO message catalogs"
	@echo "  changes    to make an overview of all changed/added/deprecated items"
	@echo "  xml        to make Docutils-compatible XML files"
	@echo "  pseudoxml  to make pseudoxml-compatible XML files"
	@echo "  linkcheck  to make link checks of the documentation"
	@echo "  doctest    to make doctest checks of the documentation"
	@echo "  coverage   to test coverage of documentation"
	@echo "  livehtml   to make HTML files and start an autoreload server"

clean:
	rm -rf $(BUILDDIR)/*

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

dirhtml:
	$(SPHINXBUILD) -b dirhtml $(ALLSPHINXOPTS) $(BUILDDIR)/dirhtml
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/dirhtml."

singlehtml:
	$(SPHINXBUILD) -b singlehtml $(ALLSPHINXOPTS) $(BUILDDIR)/singlehtml
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/singlehtml."

pickle:
	$(SPHINXBUILD) -b pickle $(ALLSPHINXOPTS) $(BUILDDIR)/pickle
	@echo
	@echo "Build finished. The pickle files are in $(BUILDDIR)/pickle."

json:
	$(SPHINXBUILD) -b json $(ALLSPHINXOPTS) $(BUILDDIR)/json
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/json."

htmlhelp:
	$(SPHINXBUILD) -b htmlhelp $(ALLSPHINXOPTS) $(BUILDDIR)/htmlhelp
	@echo
	@echo "Build finished. The HTML files are in $(BUILDDIR)/htmlhelp."

qthelp:
	$(SPHINXBUILD) -b qthelp $(ALLSPHINXOPTS) $(BUILDDIR)/qthelp
	@echo
	@echo "Build finished. The HTML files are in $(BUILDDIR)/qthelp."

devhelp:
	$(SPHINXBUILD) -b devhelp $(ALLSPHINXOPTS) $(BUILDDIR)/devhelp
	@echo
	@echo "Build finished. The HTML files are in $(BUILDDIR)/devhelp."

epub:
	$(SPHINXBUILD) -b epub $(ALLSPHINXOPTS) $(BUILDDIR)/epub
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/epub."

latex:
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) $(BUILDDIR)/latex
	@echo
	@echo "Build finished. The LaTeX files are in $(BUILDDIR)/latex."

latexpdf:
	$(SPHINXBUILD) -b latexpdf $(ALLSPHINXOPTS) $(BUILDDIR)/latex
	@echo
	@echo "Build finished. the PDF files are in $(BUILDDIR)/latex."

latexpdfja:
	$(SPHINXBUILD) -b latexpdfja $(ALLSPHINXOPTS) $(BUILDDIR)/latex
	@echo
	@echo "Build finished. the PDF files are in $(BUILDDIR)/latex."

text:
	$(SPHINXBUILD) -b text $(ALLSPHINXOPTS) $(BUILDDIR)/text
	@echo
	@echo "Build finished. The text files are in $(BUILDDIR)/text."

man:
	$(SPHINXBUILD) -b man $(ALLSPHINXOPTS) $(BUILDDIR)/man
	@echo
	@echo "Build finished. The manual pages are in $(BUILDDIR)/man."

texinfo:
	$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) $(BUILDDIR)/texinfo
	@echo
	@echo "Build finished. The LaTeX files are in $(BUILDDIR)/texinfo."

gettext:
	$(SPHINXBUILD) -b gettext $(ALLSPHINXOPTS) $(BUILDDIR)/locale
	@echo
	@echo "Build finished. The gettext files are in $(BUILDDIR)/locale."

changes:
	$(SPHINXBUILD) -b changes $(ALLSPHINXOPTS) $(BUILDDIR)/changes
	@echo
	@echo "Build finished. The changes overview file in $(BUILDDIR)/changes."

linkcheck:
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) $(BUILDDIR)/linkcheck
	@echo
	@echo "Link check complete; look for any errors in the $(BUILDDIR)/linkcheck/ index.html."

doctest:
	$(SPHINXBUILD) -b doctest $(ALLSPHINXOPTS) $(BUILDDIR)/doctest
	@echo
	@echo "Doctest complete; look for any errors in the $(BUILDDIR)/doctest/ index.html."

coverage:
	$(SPHINXBUILD) -b coverage $(ALLSPHINXOPTS) $(BUILDDIR)/coverage
	@echo
	@echo "Coverage complete; look for any errors in the $(BUILDDIR)/coverage/index.html."

livehtml:
	sphinx-autobuild -b html $(ALLSPHINXOPTS) source $(BUILDDIR)/html
	@echo
	@echo "Auto-rebuild server started. Visit http://localhost:8000 to view."
