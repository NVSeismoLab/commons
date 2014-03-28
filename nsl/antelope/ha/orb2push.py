# -*- coding: utf-8 -*-
"""
orb2push

Set up to push packets from the ORB for hooking up multiple workers
for one job.
"""
import zmq
from nsl.antelope.base import Rtapp

PUSHPULL_PORT = 55555  # port used to upload messages to be sent out


class Pusher(Rtapp):
    """
    Message Queue server using 0MQ
    
    push -> [pull --> publish] -> subscribe
    
    """
    context = None
    socket  = None

    def __init__(self, port=PUSHPULL_PORT, **kwargs):
        """
        Bind to the push port and start tossing.
        """
        super(Pusher, self).__init__(**kwargs)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PULL)
        self.socket.bind("tcp://*:"+ str(port))
    
    def process(self, packet_tuple):
        """
        Process
        """
        # Shove the packets into the push queue
        message = 'test'  # process into a message (JSON?)
        self.socket.send(message)
        return 0

