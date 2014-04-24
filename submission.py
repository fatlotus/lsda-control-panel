#!/usr/bin/env python
#
# Author: Jeremy Archer <jarcher@uchicago.edu>
# Date: 14 December 2013
#

import pika, uuid, base64, time, re, json, datetime, pytz, boto

from kazoo.client import KazooClient
from kazoo.exceptions import KazooException, NoNodeError, NodeExistsError

# Set up the connection to AMQP.
connection = pika.BlockingConnection(pika.ConnectionParameters(
  'amqp.lsda.cs.uchicago.edu'))
channel = connection.channel()

channel.queue_declare("lsda_tasks", durable=True)

# Set up the connection to ZooKeeper.
zookeeper = KazooClient(
  hosts = 'zookeeper.lsda.cs.uchicago.edu'
)

zookeeper.start()

def list_all_owners():
    """
    Returns a list of all users who have submitted jobs.
    """
    
    try:
        return sorted(zookeeper.get_children('/jobs'))
    except NoNodeError:
        return []

def view_jobs_for(owner):
    """
    Returns a list of all jobs for each individual user.
    """
    
    # Retrieve all tasks for this user.
    try:
        children = zookeeper.get_children('/jobs/{}'.format(owner))
    except NoNodeError:
        children = []
    
    # Fetch the completion status of each job.
    all_jobs = []
    
    # Sets up all queries for each node.
    blocks = []
    
    for task_id in children:
        # Fetch job submission information.
        blocks.append(zookeeper.get_async('/jobs/{}/{}'.format(owner, task_id)))
        
        # Fetch completion status.
        blocks.append(zookeeper.get_async('/done/{}'.format(task_id)))
        
        # Fetch completion status.
        blocks.append(zookeeper.exists_async('/controller/{}'.format(task_id)))
    
    for task_id, metadata, status, run_status in zip(children,
           blocks[::3], blocks[1::3], blocks[2::3]):
        
        # Retrieve submission information.
        data = metadata.get()[0].split(":")
        
        if len(data) == 3:
            git_sha1, submitted, file_name = data
        elif len(data) == 2:
            git_sha1, submitted = data
            file_name = "main.ipynb"
        else:
            git_sha1 = data[0]
            submitted = 0
            file_name = "main.ipynb"
        
        # Retrieve completion information.
        try:
            finish_reason = status.get()
        except NoNodeError:
            finish_reason = (None,)
        
        # Retrieve progress information.
        try:
            magic_json_exists = run_status.get()
        except NoNodeError:
            magic_json_exists = False
        
        if finish_reason[0] is not None:
            status = finish_reason[0] or "done"
        elif magic_json_exists:
            status = "running"
        else:
            status = "enqueued"
        
        # Save this for the template.
        all_jobs.append(dict(
            task_id=task_id,
            sha1=git_sha1,
            status=status,
            file_name=file_name,
            submitted=datetime.datetime.fromtimestamp(int(float(submitted)),
                                tz=pytz.timezone('US/Central'))
        ))
    
    all_jobs.sort(key = lambda x: x['submitted'])
    all_jobs.reverse()
    
    return all_jobs[:20]

def submit_a_job(owner, from_user, git_sha1, queue_name, is_admin,
        file_name = "main.ipynb", number_of_workers = 1):
    
    """
    Adds a job into the AMQP processing queue.
    """
    
    # Validate the incoming GIT SHA-1.
    if not re.match(r'[a-f0-9]{40}', git_sha1):
        return
    
    # Allow TAs to specify custom job queues.
    if not is_admin:
        queue_name = 'stable'
    
    # Allow TAs to submit from other's repos.
    if not is_admin:
        from_user = owner
    
    # Create a new ID for this task.
    task_id = str(uuid.uuid4())
    
    # Save the task into ZooKeeper.
    zookeeper.create("/jobs/{}/{}".format(owner, task_id),
      value = ":".join([git_sha1.encode("ascii"), str(time.time()),
                        file_name.encode("ascii")]),
      makepath = True)
    
    # Index this task by filename.
    hashed_name = hashlib.sha1(
      json.dumps(from_user, file_name)).hexdigest()
    
    zookeeper.create("/byfile/{}/{}-{}".format(hashed_name, task_id, owner),
      value = "", makepath = True)
    
    # Generate a cluster shape for this task.
    constellation = ["controller"] + (["engine"] * number_of_workers)
    
    # Publish the task on the channel.
    for job_type in constellation:
        channel.basic_publish(
           exchange = '',
           routing_key = queue_name,
           body = json.dumps(dict(
               kind = job_type,
               owner = owner,
               task_id = task_id,
               from_user = from_user,
               sha1 = git_sha1,
               file_name = file_name,
               number_of_workers = number_of_workers,
           ))
        )

def cancel_a_job(task_id):
    """
    Marks a job as done, interrupting whatever worker is executing it.
    """
    
    # Save the task into ZooKeeper.
    try:
        zookeeper.create("/done/{}".format(task_id), "cancelled",
          makepath = True)
    except NodeExistsError:
        pass

def notebook_from_task(task_id):
    """
    Returns the notebook for the given task as a string.
    """

    bucket = boto.connect_s3().get_bucket("ml-submissions")
    key = bucket.get_key(task_id + ".ipynb")

    if key is None:
        return None

    return key.get_contents_as_string()

def list_all_nodes(is_admin, primary_owner):
    """
    Returns a list of connected ZooKeeper nodes.
    """
    
    nodes = []
    
    for ip_address in zookeeper.get_children("/nodes"):
        state = json.loads(zookeeper.get("/nodes/{}".format(ip_address))[0])
        
        # Unpack task information.
        version = state.get("release", "")
        
        # Unpack application-level state information from this node.
        task = state.get("task")
        if type(task) is not dict:
            task = {}
        state_symbol = (state.get("state_stack", None) or [ None ])[-1]
        owner = task.get("owner", "")
        task_type = task.get("task_type", "")
        task_id = task.get("task_id", "")
        sha1 = task.get("sha1", "")
        flag = state.get("flag", "")
        queue_name = state.get("queue_name", "")
        
        if not is_admin:
            if owner:
                if owner != primary_owner: # Hide non-owned jobs.
                    continue
            else:
                if queue_name != "stable": # Hide prerelease nodes.
                    continue
        
        # Unpack subsystem metrics.
        NaN = float("NaN")
        idle = state.get("cpu_usage", {}).get("idle", NaN)
        mactive, mtotal, mcached, mfree, stotal, sfree = (
          state.get("mem_usage", [NaN] * 6))
        net_stat = state.get("net_throughput", {})
        received = float(net_stat.get("received", NaN))
        transmitted = float(net_stat.get("transmitted", NaN))
        read_rate, write_rate = state.get("disk_throughput", [NaN, NaN])
        spindles = state.get("spindles", NaN) / 100
        
        disk_usage = float(state.get("disk_usage", ["NaN%"] * 6)[4][:-1]) / 100
        
        # Compute derivative values.
        cpu_usage = (100 - idle) / 100
        mem_usage = 1 - (mfree + mcached) / float(mtotal)
        
        nodes.append(dict(locals()))
    
    nodes.sort(key = lambda x: x['task_id'])
    nodes.reverse()
    
    return nodes