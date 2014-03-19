from flask import Flask, jsonify, render_template, request, redirect
from boto.ec2.cloudwatch import CloudWatchConnection
import datetime
import git
import functools
import threading
import time
from submission import view_jobs_for, submit_a_job, cancel_a_job
from submission import list_all_nodes, list_all_owners
from gitrepo import fetch_commits

app = Flask(__name__)

@app.route('/')
def main():
    owner = request.environ["REMOTE_USER"]
    is_admin = owner in ("jarcher", "lafferty")
    
    if is_admin:
        owner = request.args.get("owner", owner)
    
    commits = fetch_commits(owner)
    commits_index = dict([(x['hexsha'], x) for x in commits])
    
    return render_template("plain.html",
        commits = commits,
        commits_index = commits_index,
        jobs = view_jobs_for(owner),
        nodes = list_all_nodes(),
        owners = list_all_owners(),
        owner = owner,
        is_admin = is_admin
    )

@app.route('/submit', methods = ["POST"])
def submit_job():
    """
    Submits a job with the given SHA-1 commit to the backing cluster.
    """
    
    # TODO(fatlotus): add validation.
    git_sha1 = request.args.get("sha1", "").encode("ascii")
    
    # Submit this SHA-1 to the backing cluster.
    submit_a_job("jarcher", git_sha1)
    return redirect("/")

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