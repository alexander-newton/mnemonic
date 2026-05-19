Mnemonic Documentation
======================

Adaptive spaced repetition system with LLM-powered question variations.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user-guide/index
   developer/index
   api/index
   adr/index

Quick Start
-----------

See the README for installation and setup instructions.

.. code-block:: bash

   cd infrastructure
   docker-compose -f docker-compose.dev.yml up

Features
--------

- Spaced repetition using FSRS algorithm
- LLM-powered question variation generation
- Leech detection and card decomposition
- Offline-first PWA with IndexedDB
- Support for Markdown, cloze deletions, and math notation

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
