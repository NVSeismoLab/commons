#!/usr/bin/python
#
"""
gzm.py

Simple python module for a Generalized ZeroMQ Message server daemon.

Contains both Client and Server classes for setting up the following:

   CLIENT:[push] -> SERVER:[pull --> publish] -> CLIENT:[subscribe]

Any number of clients can push messages to the server and/or subscribe
to those messages.

"""
import zmq

__version__ = '0.1.0'

PUBSUB_PORT   = 55551  # port used for subscribing to messages
PUSHPULL_PORT = 55552  # port used to upload messages to be sent out

class Server(object):
    """
    Message Queue server using 0MQ
    
    push -> [pull --> publish] -> subscribe
    
    """
    context = None
    socket  = {'pub':None, 'pull':None}

    def __init__(self, pull_port=PUSHPULL_PORT, publish_port=PUBSUB_PORT):
        
        self.context = zmq.Context()

        self.socket['pub'] = self.context.socket(zmq.PUB)
        self.socket['pub'].bind("tcp://*:"+ str(publish_port))
        self.socket['pub'].setsockopt(zmq.HWM, 1000)

        self.socket['pull'] = self.context.socket(zmq.PULL)
        self.socket['pull'].bind("tcp://*:"+ str(pull_port))

    def start(self):
        while True:
            try:
                message = self.socket['pull'].recv()
                self.socket['pub'].send(message)
            except KeyboardInterrupt:
                sys.exit(0)


class Client(object):
    """
    Message client for zserver with JSON serialization
    (Send anything that python.json can understand)

    """
    context = None
    socket = {'sub':None, 'push':None}
    
    def __init__(self, host='localhost', push_port=PUSHPULL_PORT, subscribe_port=PUBSUB_PORT):
        self.context = zmq.Context()
        self.socket['sub'] = self.context.socket(zmq.SUB)
        self.socket['sub'].connect("tcp://" + host + ":"+ str(subscribe_port))
        self.socket['sub'].setsockopt(zmq.SUBSCRIBE, "")

        self.socket['push'] = self.context.socket(zmq.PUSH)
        self.socket['push'].connect("tcp://" + host + ":" + str(push_port))
    
    def get(self):
        try:
            return self.socket['sub'].recv_json()
        except KeyboardInterrupt:
            return None

    def put(self, obj):
        self.socket['push'].send_json(obj)


if __name__ == '__main__':
    import sys, os

    usage = """GZM messager: v{0}

USAGE: gzm <command>
    'help'   -  print this message
    'start'  -  start server
    'client' -  subscribe and print message stream to STDOUT
""".format(__version__)
    
    pid = os.getpid()

    if len(sys.argv) <= 1 or sys.argv[1] == "help": 
        print usage     
    elif sys.argv[1] == "client":
        c = Client()
        while True:
            msg = c.get()
            if msg is None:
                sys.exit(0)
            else:
                print msg
    elif sys.argv[1] == "start":
        Server().start()
    else:
        print usage


