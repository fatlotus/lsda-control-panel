#!/usr/bin/env python
#
# Author: Jeremy Archer <jarcher@uchicago.edu>
# Date: 14 December 2013
#

import pika, uuid, base64, time, re, json

from kazoo.client import KazooClient
from kazoo.exceptions import KazooException, NoNodeError, NodeExistsError

DEFAULT_CONSTELLATION = ["controller", "engine", "engine", "engine"]

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
        return zookeeper.get_children('/jobs')
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
    
    for task_id in children:
        # Retrieve job meta-information.
        data = zookeeper.get('/jobs/{}/{}'.format(owner, task_id))[0].split(":")
        
        if len(data) == 2:
            git_sha1, submitted = data
        else:
            git_sha1 = data[0]
            submitted = 0
        
        try:
            finish_reason = zookeeper.get('/done/{}'.format(task_id))
        except NoNodeError:
            finish_reason = (None,)
        
        try:
            magic_json = zookeeper.get('/controller/{}'.format(task_id))
        except NoNodeError:
            magic_json = None
        
        # Determine what, exactly, has happened.
        if finish_reason[0] is not None:
            status = finish_reason[0] or "done"
        elif magic_json:
            status = "running"
        else:
            status = "enqueued"
        
        all_jobs.append(dict(
            task_id=task_id,
            sha1=git_sha1,
            status=status,
            submitted=float(submitted)
        ))
    
    all_jobs.sort(key = lambda x: -x['submitted'])
    
    return all_jobs[:10]

def submit_a_job(owner, git_sha1, constellation = DEFAULT_CONSTELLATION):
    """
    Adds a job into the AMQP processing queue.
    """
    
    # Validate the incoming GIT SHA-1.
    if not re.match(r'[a-f0-9]{40}', git_sha1):
        return
    
    # Create a new ID for this task.
    task_id = str(uuid.uuid4())
    
    # Save the task into ZooKeeper.
    zookeeper.create("/jobs/{}/{}".format(owner, task_id),
      value = ":".join([git_sha1.encode("ascii"), str(time.time())]),
      makepath = True)
    
    # Publish the task on the channel.
    for job_type in constellation:
        channel.basic_publish(
           exchange = '',
           routing_key = 'lsda_tasks',
           body = ':'.join([job_type, owner, task_id, git_sha1])
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

def list_all_nodes(is_admin, primary_owner):
    """
    Returns a list of connected ZooKeeper nodes.
    """
    
    for ip_address in zookeeper.get_children("/nodes"):
        state = json.loads(zookeeper.get("/nodes/{}".format(ip_address))[0])
        
        # Unpack task information.
        version = state.get("release", "")
        
        # Unpack application-level state information from this node.
        state_symbol = state.get("state_stack", [ None ])[-1]
        owner = state.get("owner", "")
        task_type = state.get("task_type", "")
        task_id = state.get("task_id", "")
        sha1 = state.get("sha1", "")
        
        if not is_admin and owner and owner != primary_owner:
            continue
        
        # Unpack subsystem metrics.
        idle = state.get("cpu_usage", {}).get("idle", float("NaN"))
        mactive, mtotal, mcached, mfree, stotal, sfree = (
          state.get("mem_usage", [float("NaN")] * 7))
        received = state.get("net_throughput", {}).get("received")
        transmitted = state.get("net_throughput", {}).get("transmitted")
        read_rate, write_rate = state.get("disk_throughput", [None, None])
        
        # Compute derivative values.
        cpu_usage = (100 - idle) / 100
        mem_usage = (mfree + mcached) / mtotal
        
        yield locals()