from kazoo.client import KazooClient
from kazoo.client import KazooState
import pika
import random
import json
import time
import os


BASE_PATH = "election"
RABBITMQ_URL = os.getenv("RABBITMQ_URL") or 'amqp://user:password@localhost:5672'
ZOOKEEPER_URL = os.getenv("ZOOKEEPER_URL") or '127.0.0.1:2181'


def addTaskToQueue():
    parameters = pika.URLParameters(RABBITMQ_URL)
    try:
        connection = pika.BlockingConnection(parameters)
    except Exception:
        print("Unable to connect to rabbitmq")
        return
    channel = connection.channel()
    channel.queue_declare(queue='task')
    channel.basic_publish('',
                      'task',
                      str(random.randint(0, 1000)),
                      pika.BasicProperties(content_type='text/plain',
                                           delivery_mode=pika.DeliveryMode.Transient))
    connection.close()

def getTaskFromQueue():
    parameters = pika.URLParameters(RABBITMQ_URL)
    try:
        connection = pika.BlockingConnection(parameters)
    except Exception:
        print("Unable to connect to rabbitmq")
        return
    channel = connection.channel()
    channel.queue_declare(queue='task')
    method_frame, header_frame, body = channel.basic_get('task')
    if method_frame:
        print("The message is", body.decode('utf-8'))
        channel.basic_ack(method_frame.delivery_tag)
    else:
        print('No message returned')
    connection.close()

def getCurrentNode():
    with open("node.json", "r") as f:
        return json.load(f)


def state_listener(state):
    if state == KazooState.LOST:
        # Register somewhere that the session was lost
        print("Connection to zookeeper lost, session was probably expired/lost")
        exit(0)
    elif state == KazooState.SUSPENDED:
        # Handle being disconnected from Zookeeper
        print("Client disconnected from zookeeper")
    elif state == KazooState.CONNECTED:
        print(f"Connection to zookeeper at {ZOOKEEPER_URL} successful")
    else:
        # Handle being reconnected to Zookeeper
        print("Reconnected client")


zk = KazooClient(hosts=ZOOKEEPER_URL)


zk.add_listener(state_listener)
zk.start()

# Ensure the /election path exists
zk.ensure_path(f"/{BASE_PATH}")
# Create the ephemeral child znode
print(os.getenv("HOSTNAME"))
node = zk.create(f"/{BASE_PATH}/node", b"127.0.0.1",
                 ephemeral=True, sequence=True)
children = zk.get_children(f"/{BASE_PATH}")

# Leader is znode with least uuid
leader = sorted(children)[0]

if leader == node.split("/")[-1]:
    print("I am the master")
    with open("node.json", "w") as f:
        json.dump({"node": node.split("/")[-1], "master": True}, f)
else:
    print("Nothing to see here, just a child")
    with open(f"node.json", "w") as f:
        json.dump({"node": node.split("/")[-1], "master": False}, f)


@zk.ChildrenWatch(f"/{BASE_PATH}")
def checkLeader(children):
    current = getCurrentNode()["node"]
    if sorted(children)[0] == current:
        print("I guess im the leader now")
        with open("node.json", "w") as f:
            json.dump({"node": current, "master": True}, f)


while True:
    master = getCurrentNode()["master"]
    if master:
        addTaskToQueue()
        time.sleep(2)
    else:
        getTaskFromQueue()
        time.sleep(1)