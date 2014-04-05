import git, pytz, time, datetime

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
    
    while len(stack) > 0:
        head = stack.pop()
        
        if head in shared_parents:
            continue
        else:
            parents.append(head)
        
        stack.extend(head.parents)
    
    # Transform the commits into a template-friendly object.
    for parent in parents:
        result.append({
          "hexsha": parent.hexsha,
          "committer": parent.committer.name,
          "committer_email": parent.committer.email,
          "date": datetime.datetime.fromtimestamp(int(parent.committed_date),
                    tz=pytz.timezone('US/Central')),
          "message": parent.message
        })
    
    result.sort(key = lambda x: x["date"])
    result.reverse()
    
    return result