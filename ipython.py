from IPython.nbformat.current import reads_json
from IPython.nbconvert.exporters import HTMLExporter
import json
import hashlib
import memcache
import traceback
import logging
import StringIO
import subprocess
import os
import sys

if __name__ != "__main__":
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
        if type(value) not in (str, unicode):
            raise ValueError("Invalid cache response.")

    except Exception:
        logging.exception("Unable to read fragment.")

    else:
        if value:
            logging.info("Cache HIT.")
            return value
        else:
            logging.info("Cache MISS.")

    # Render the notebook.
    logging.info("About to render externally.")

    process = subprocess.Popen(["/usr/bin/env", "python", "ipython.py"],
               cwd = os.path.dirname(__file__),
               stdin = subprocess.PIPE,
               stdout = subprocess.PIPE)

    logging.info("About to render externally.")
    html = process.communicate(json_as_string)[0]
    logging.info("Rendering complete.")

    if html == "":
        return None

    # Saved the cached value.
    try:
        connection.set(key, html)
    except Exception:
        logging.exception("Unable to cache fragment.")

    return html

def main():
    """
    Render STDIN as a notebook.
    """

    exporter = HTMLExporter()
    json_as_string = sys.stdin.read()

    try:
        notebook_node = reads_json(json_as_string)
    except Exception:
        logging.exception("Unable to parse JSON.")
    
    html, _ = exporter.from_notebook_node(notebook_node)
    
    sys.stderr.write("JSON was {} byte(s); html is {} byte(s).\n".format(
        len(json_as_string), len(html)
    ))
    
    sys.stdout.write(html)
    sys.stderr.flush()
    sys.stdout.flush()

if __name__ == '__main__':
    main()
