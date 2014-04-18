from IPython.nbformat.current import reads_json
from IPython.nbconvert.exporters import HTMLExporter
import json

AFTER_HTML = """
<style type="text/css">
  #notebook-container { width: auto; }
</style>
<script type="text/javascript">
  window.parent.document.getElementsByTagName("iframe")[0].height = (
    document.body.scrollHeight);
</script>
"""

def render_control_box(list_of_runs):
    """
    Renders JavaScript to generate a <select> control to allow switching
    the source of the <iframe>.
    """

    data = json.dumps(list_of_runs)

    return """
    <script type="text/javascript">
        (function(options) {
            var doc = window.parent.document;
            var parent = doc.getElementsByClassName("meta")[0];
            var select = parent.firstChild;
            if (!select) {
                select = doc.createElement("select");
                parent.appendChild(select);
            }
            
            while (select.hasChildNodes())
                select.removeChild(select.firstChild());
            
            var fragments = window.top.location.pathname.split("/");
            
            for (var i = 0; i < options.length; i++) {
                var option = options[i];
                var tag = document.createElement("tag");
                var a = document.createElement("a");
                fragments[4] = option[0];
                
                tag.setAttribute("value", fragments.join("/"));
                tag.innerHTML = option[1];
                tag.selected = !!option[2];
                
                select.appendChild(tag);
            }
        })($$data$$)
    </script>
    """.replace("$$data$$", data)

def render_to_html(json_as_string):
    """
    Renders the given Notebook note as HTML.
    """

    exporter = HTMLExporter()
    try:
        notebook_node = reads_json(json_as_string)
    except Exception:
        return None

    html, _ = exporter.from_notebook_node(notebook_node)

    return html + AFTER_HTML
