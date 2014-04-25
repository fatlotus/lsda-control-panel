import git, pytz, time, datetime, re, tempfile, boto

shared_repo = git.Repo("/home/git/repositories/assignment-one.git")

def fetch_stale_commits(cache = {'age': 0, 'value': None}):
    """
    Returns a list of all commits on master (those not submitted by the
    student.)
    """
    
    if time.time() - cache['age'] > 30:
        cache['value'] = list(shared_repo.heads.master.commit.iter_parents())
        cache['age'] = time.time()
    
    return cache['value']

def fetch_commits(cnetid):
    """
    Retrieves a list of all commits relevant to the given user.
    """
    
    # Pull the user-specific repository.
    my_repo = git.Repo("/home/git/repositories/{}.git".format(cnetid))
    
    # Look for those unique commits not on master.
    try:
        latest = my_repo.heads["master"].commit
    except IndexError:
        return []
    
    # Search for the latest commits by that user.
    parents = []
    shared_parents = fetch_stale_commits()
    stack = [latest]
    result = []
    visited = set()
    
    while len(stack) > 0:
        head = stack.pop()
        
        if head in shared_parents:
            continue
        elif head in visited:
            continue
        else:
            parents.append(head)
        
        visited.add(head)
        stack.extend(head.parents)
    
    # Transform the commits into a template-friendly object.
    for parent in parents:
        result.append({
          "hexsha": parent.hexsha,
          "committer": parent.committer.name,
          "committer_email": parent.committer.email,
          "date": datetime.datetime.fromtimestamp(int(parent.committed_date),
                    tz=pytz.timezone('US/Central')),
          "message": parent.message,
          "short_message": parent.message.split("\n")[0]
        })
    
    result.sort(key = lambda x: x["date"])
    result.reverse()
    
    return result

def notebook_from_commit(cnetid, commit, path):
    """
    Returns the notebook, as a string, for the given path in the given
    repository.
    """

    # Fetch the repository object for this person.
    my_repo = git.Repo("/home/git/repositories/{}.git".format(cnetid))

    # Validate the commit to view.
    if not re.match(r'[a-f0-9]{40}', commit):
        return

    # Retrieve the commit, with guards.
    commit = my_repo.commit(commit)
    if not commit:
        return

    # Fetch the blob, with guards.
    blob = commit.tree[path]
    if not blob:
        return

    # Ensure that the result is valid JSON.
    return blob.data_stream.read()

def prepare_submission(cnetid, sha1):
    """
    Uploads a ZIP archive to S3.
    """

    # Read the repo and connect to S3.
    my_repo = git.Repo("/home/git/repositories/{}.git".format(cnetid))
    bucket = boto.connect_s3().get_bucket("ml-checkpoints")

    with tempfile.TemporaryFile() as fp:
        # Generate a zip archive for this submission.
        my_repo.archive(fp, sha1, format = "zip")

        # Upload the archive to the S3.
        key = bucket.new_key("submissions/{}/{}.zip".format(cnetid, sha1))
        key.set_contents_from_file(fp)
