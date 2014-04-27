from IPython.nbformat.current import reads_json
from IPython.nbconvert.exporters import HTMLExporter
import json

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

    exporter = HTMLExporter()
    try:
        notebook_node = reads_json(json_as_string)
    except Exception:
        return None

    html, _ = exporter.from_notebook_node(notebook_node)

    return html
