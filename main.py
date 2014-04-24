from flask import Flask, jsonify, render_template, request, redirect
from boto.ec2.cloudwatch import CloudWatchConnection
import datetime
import git
import functools
import threading
import time
from submission import view_jobs_for, submit_a_job, cancel_a_job
from submission import list_all_nodes, list_all_owners
from gitrepo import fetch_commits, notebook_from_commit
from ipython import render_to_html, render_control_box
from timer import Timer

app = Flask(__name__)
app.debug = True

@app.route('/')
def main():
    timer = Timer()
    
    owner = request.environ["REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty", "qinqing", "nseltzer")
    
    if is_admin:
        owner = request.args.get("owner", owner)
    
    commits = timer.invoke(fetch_commits, owner)
    commits_index = dict([(x['hexsha'], x) for x in commits])
    
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

    owner = request.environ["REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty", "qinqing", "nseltzer")
    from_user = request.args.get("repo", "")[:-4]

    if not is_admin:
        from_user = owner

    sha1 = request.args.get("sha1", "")
    file_name = request.args.get("file_name", "")

    notebook = notebook_from_commit(from_user, sha1, file_name)

    if not notebook:
        return

    options = []
    
    for commit in fetch_commits(owner):
        options.append((
          commit["hexsha"],        # link target
          commit["short_message"], # readable label
          commit["hexsha"] == sha1 # selection status
        ))

        options.append((commit["hexsha"], "  First run.", False))

    return render_to_html(notebook) + render_control_box(options)

@app.route('/submit', methods = ["POST"])
def submit_job():
    """
    Submits a job with the given SHA-1 commit to the backing cluster.
    """
    
    owner = request.environ["REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty", "qinqing", "nseltzer")
    
    if not is_admin:
        from_user = owner
    else:
        from_user = request.args.get("submitter", owner)
    
    git_sha1 = request.args.get("sha1", "")
    queue_name = request.args.get("queue_name", "stable")
    file_name = request.args.get("file_name", "main.ipynb")
    
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
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)