import git

repo = git.Repo("/home/git/repositories/assignment-one/.git")

def fetch_commits(cnetid):
    """
    Retrieves a list of all commits relevant to the given user.
    """
    
    # Look for those unique commits not on master.
    try:
        latest = repo.heads["submissions/{}/submit".format(cnetid)].commit
    except IndexError:
        return []
    
    parents = list(latest.iter_parents()) + [latest]
    shared_parents = list(repo.heads.master.commit.iter_parents())
    result = []
    
    # Transform the commits into a template-friendly object.
    for parent in parents:
        path_to_check = "results/{}.ipynb".format(parent.hexsha)
        
        result.append({
          "hexsha": parent.hexsha,
          "committer": parent.committer.name,
          "committer_email": parent.committer.email,
          "date": parent.committed_date,
          "message": parent.message
        })
    
    result.sort(key = lambda x: -x["date"])
    
    return result