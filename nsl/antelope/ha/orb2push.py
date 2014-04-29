# -*- coding: utf-8 -*-
"""
orb2push

Set up to push packets from the ORB for hooking up multiple parallel
workers for one task.
"""
import zmq
from nsl.antelope.base import Rtapp

PUSHPULL_PORT = 55555  # port used to upload messages to be sent out


class Pusher(Rtapp):
    """
    Message Queue server using 0MQ

    Pushes out tuples reaped from ORB as JSON packets on a given port,
    using the PUSH protocol. This way a packet can be sent to one of
    many multiple workers running in parallel.
    """
    context = None
    socket  = None

    def __init__(self, port=PUSHPULL_PORT, **kwargs):
        """
        Bind to the push port and start tossing.
        """
        super(Pusher, self).__init__(**kwargs)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.bind("tcp://*:"+ str(port))
    
    def process(self, packet_tuple):
        """
        Process
        """
        self.socket.send_json(packet_tuple)
        return 0


if __name__=="__main__":
    Pusher.main()
