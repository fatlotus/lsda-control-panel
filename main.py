from gevent import monkey; monkey.patch_all()

from flask import Flask, jsonify, render_template, request, redirect
from boto.ec2.cloudwatch import CloudWatchConnection
import datetime
import git
import functools
import threading
import time
from submission import view_jobs_for, submit_a_job, cancel_a_job
from submission import list_all_nodes, list_all_owners, tasks_for_file
from submission import notebook_from_task, get_job_status
from gitrepo import fetch_commits, notebook_from_commit, prepare_submission
from ipython import render_to_html, python_to_notebook
from timer import Timer
import logging
import datetime
import pytz

logging.basicConfig(level = logging.INFO)

app = Flask(__name__)
app.debug = True

def format_date(seconds):
    return datetime.datetime.fromtimestamp(seconds,
               tz=pytz.timezone('US/Central'))

app.jinja_env.globals.update(format_date = format_date)

@app.route('/')
def main():
    timer = Timer()
    
    owner = request.environ["HTTP_REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty", "qinqing", "nseltzer")
    
    if is_admin:
        owner = request.args.get("owner", owner)
    
    commits = [] # timer.invoke(fetch_commits, owner)
    commits_index = {} # dict([(x['hexsha'], x) for x in commits])
    
    return render_template("plain.html",
        commits = commits,
        commits_index = commits_index,
        jobs = timer.invoke(view_jobs_for, owner),
        nodes = timer.invoke(list_all_nodes, is_admin, owner),
        owners = timer.invoke(list_all_owners),
        owner = owner,
        is_admin = is_admin,
        times = timer.format()
    )

@app.route('/render')
def render_page():
    """
    Renders the IPython notebook from a commit.
    """

    # Retrieve request parameters.
    owner = request.environ["HTTP_REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty", "qinqing", "nseltzer")
    from_user = request.args.get("repo", "")[:-4]

    if not is_admin:
        from_user = owner

    sha1 = request.args.get("sha1", "")
    file_name = request.args.get("file_name", "")
    target = request.args.get("target", "latest")

    # Fetch the list of tasks for this file.
    tasks = list(tasks_for_file(from_user, file_name))

    # If we're undecided, pick the latest task available.
    if target == "latest":
        if len(tasks) > 0:
            target = max(tasks, key = lambda x: x[2])[0]
        else:
            target = ""

    if target == "":
        
        # Fetch the notebook from Git.
        notebook = notebook_from_commit(from_user, sha1, file_name)

        if file_name.endswith(".py"):
            notebook = python_to_notebook(notebook)

        status, info = "stored", None
        nodes = []

    else:
        
        # Fetch the notebook from S3.
        notebook = notebook_from_task(target)
        status, info = get_job_status(target)
        
        # Retrieve the list of nodes for this task.
        nodes = list_all_nodes(None, None, target)

    # Compute styling fixes.
    offset = (len(nodes) + 2) * 30

    # Build a <select> for the UI.
    options = []

    tasks.sort(key = lambda x: x[2])
    tasks.reverse()

    for task_id, owner, submitted_on in tasks:
        options.append(dict(
            label = "Run on {:%Y-%m-%d %H:%M:%S} by {}".format(
              submitted_on, owner),
            target = task_id,
            selected = (task_id == target)
        ))

    options.append(dict(
        label = "Latest Git version",
        target = "",
        selected = (target == "")
    ))

    # Render the result.
    notebook_html = render_to_html(notebook)
    
    return render_template("notebook.html", **locals())

@app.route('/submit', methods = ["POST"])
def submit_job():
    """
    Submits a job with the given SHA-1 commit to the backing cluster.
    """
    
    owner = request.environ["HTTP_REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty", "qinqing", "nseltzer")
    from_user = request.args.get("repo", "")[:-4]
    
    git_sha1 = request.args.get("sha1", "")
    queue_name = request.args.get("queue_name", "stable")
    file_name = request.args.get("file_name", "main.ipynb")
    
    # Upload this commit to S3.
    prepare_submission(from_user, git_sha1)
    
    # Submit this SHA-1 to the backing cluster.
    submit_a_job(owner, from_user, git_sha1, queue_name, is_admin, file_name)
    return redirect(request.referrer or "/")

@app.route('/cancel', methods = ["POST"])
def cancel_job():
    """
    Cancels the given task.
    """
    
    task_id = request.args.get("task_id", "").encode("ascii")
    cancel_a_job(task_id)
    return redirect(request.referrer or "/")

if __name__ == "__main__":
    app.run(debug=True)
