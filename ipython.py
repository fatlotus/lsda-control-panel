from IPython.nbformat.current import reads_json
from IPython.nbconvert.exporters import HTMLExporter
import json
import hashlib
import memcache
import traceback
import logging

connection = memcache.Client([
    "notebook-cache.l0s8m9.0001.use1.cache.amazonaws.com"])

def python_to_notebook(source_code):
    """
    Converts this Python file into a notebook.
    """

    return json.dumps({
        "metadata": { "name": "" },
        "nbformat": 3,
        "nbformat_minor": 0,
        "worksheets": [ {
            "cells": [ {
                "cell_type": "code",
                "collapsed": False,
                "input": source_code.split("\n"),
                "language": "python",
                "metadata": {},
                "outputs": []
            } ],
            "metadata": {}
        } ]
    })

def render_to_html(json_as_string):
    """
    Renders the given Notebook node as HTML.
    """

    import os
    os.environ["HOME"] = "/home/git"

    # Return if not yet ready.
    if not json_as_string:
        return

    # Attempt to read a cached value.
    key = hashlib.sha1(json_as_string).hexdigest()
    try:
        value = connection.get(key)

    except Exception:
        logging.exception("Unable to read fragment.")

    else:
        if value:
            logging.info("Cache HIT.")
            return value
        else:
            logging.info("Cache MISS.")

    # Render the notebook.
    exporter = HTMLExporter()
    try:
        notebook_node = reads_json(json_as_string)
    except Exception:
        return None

    html, _ = exporter.from_notebook_node(notebook_node)

    # Saved the cached value.
    try:
        connection.set(key, html)
    except Exception:
        logging.exception("Unable to cache fragment.")

    return html
