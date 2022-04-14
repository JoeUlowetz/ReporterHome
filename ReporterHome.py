#!/usr/bin/python3
# ReporterHome.py
#   2022.02.18 Joe Ulowetz, Impossible Objects
#   copied from CameraServer.py

"""
 To install (one-time event): copy ReporterHome.service to /etc/systemd/system and make sure owned by root
 Then: sudo systemctl enable ReporterHome.service
 Then: sudo systemctl start ReporterHome.service
 Now it will automatically start every time the RPi is booted.

 To check:     systemctl status ReporterHome.service

 If you ever need to manually start:     sudo systemctl start ReporterHome.service
 You can also have it restart if you have changes to install:  sudo systemctl restart ReporterHome.service

 Service file: /etc/systemd/system/ReporterHome.service

 Python libraries you may have to load
"""

import socket
import socketserver
import time
import datetime     # to show formatted time on print lines
import json
import threading
from logger import set_logger, log_event
from pathlib import Path
import os
import webpage

target = "/home/pi/ImpossibleObjects/ReporterHome/reports.txt"     # Reminder: this is on target Linux system

BUFFER_SIZE = 2048      # For the moment, assume all messages will fit in one buffer length
DELTA = 100             # allow for overhead in socket buffer when comparing if message is too large
ENCODING = 'ascii'      # use 'ascii' or 'utf-8'

pycam = None  # later set to PyCam() instance

action_event = threading.Event()    # set when any action 'run' thread running

socket_working = False      # set to True when server_bind() successfully runs


# -----------------------------------------------------------------------------------------------------------
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """
    Besides having the handle() function to receive/respond to network traffic, this class is responsible for
    decoding and validating the request that is received here (needs to be proper JSON, decode to a dictionary,
    and have certain fields present).
    See documentation for the Python library socketserver for more details.

    OR: see:  https://brokenbad.com/address-reuse-in-pythons-socketserver/
    OR: see:  https://stackoverflow.com/questions/49728912/socketserver-allow-reuse-address-to-rebind-existing-port-number-not-working-wi

    Or maybe:
    class MyTcpServer(socketserver.TCPServer):
        allow_reuse_address = True

        def __init__(self, address, request_handler_class):
            self.address = address
            self.request_handler_class = request_handler_class
            super().__init__(self.address, self.request_handler_class)
    """
    allow_reuse_address = True  # this should allow the socket to be reused!

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)       # this may not do anything
        self.socket.bind(self.server_address)

    # Reminder: the main server loop calls server.handle_request(), and that in turn will call handle() here.
    def handle(self):

        received = round(time.time(), 3)

        # This is only used if there is an unhandled exception that gets caught below
        output_data_dict = {
            'NetCmd': "NAK",
            'message': "Uncaught exception"}

        # ########################################
        # Receive the bytes, which we assume are
        # JSON-encoded string, from the network
        # ########################################
        data_bytes = self.request.recv(BUFFER_SIZE)
        data_str = str(data_bytes, ENCODING)
        log_event("DEBUG", "REQUEST", incoming_msg=data_str)


        # ########################################
        # Convert the JSON-encoded string into an
        # object, which should be a dictionary
        # ########################################
        try:
            input_data_dict = json.loads(data_str)
        except ValueError:
            # Server received something from client that is not valid json
            # log_it("{S}: ERROR Server received a string that is not valid JSON")
            msg1 = "incoming string is not valid JSON"
            log_event("WARNING", "REQUEST", msg=msg1)
            output_data_dict = {
                'NetCmd': "NAK",
                'message': msg1}
        else:
            # ########################################
            # Make sure the object we received is a
            # dictionary object as expected
            # ########################################
            if type(input_data_dict) is not dict:
                msg1 = "received object is not a dictionary"
                output_data_dict = {
                    'NetCmd': "NAK",
                    'message': msg1}
                log_event("WARNING", "REQUEST", msg=msg1)
            else:
                # ########################################
                # Save the report
                # ########################################
                ts = datetime.datetime.now()
                print("%s Saving record: %s" % (ts.strftime("%m-%d %H:%M:%S "), str(input_data_dict)))

                with open(target, 'a') as f:
                    f.write("%s\n" % str(input_data_dict))

                output_data_dict = {
                    'NetCmd': "ACK",
                    'message': "Saved report"}

                webpage.receive(input_data_dict)    # <<<<<<<<<<< This is where web page gets updated

        finally:    # send out server response (unless size too large for network buffer)
            # Note: if there is an unhandled exception somewhere within the camera or network logic, it will
            # be caught here. In that scenario output_data_dict[] has not been initialized, so it causes another
            # exception here. I changed this so output_data_dict[] gets initialized right at the start of the
            # handle() function, and if that version gets returned it is because of some other unhandled exception.
            # misc info
            if output_data_dict is None:
                # not sure yet how this happens, but it does
                msg1 = "Response dictionary null"
                output_data_dict = {
                    'NetCmd': "NAK",
                    'message': msg1}

            # ########################################
            # turn dictionary into JSON-encoded string
            # ########################################
            log_event("INFO", "RESPONSE", msg=str(output_data_dict))
            out_string = json.dumps(output_data_dict)       # TODO: could this throw an exception?

            # ########################################
            # convert string to bytes so it can be sent to socket
            # ########################################
            out_bytes = bytes(out_string, ENCODING)

            # make sure we aren't exceeding our expected buffer size limit (it won't)
            if len(out_bytes) >= (BUFFER_SIZE-DELTA):
                msg1 = "response message was too large for network buffer; unable to send"
                log_event("WARNING", "RESPONSE", msg=msg1)
                output_data_dict = {
                    'NetCmd': "NAK",
                    'message': msg1
                }

                out_string = json.dumps(output_data_dict)
                out_bytes = bytes(out_string, ENCODING)
                # Note: truncating buffer makes it invalid JSON, so we just can't truncate
                # our buffer. Instead we return a different message to describe problem

            # ########################################
            # Send out the server's response to the client request
            # ########################################
            self.request.sendall(out_bytes)

        #print("^^^^^^  Finished Network message [updated]")


# -----------------------------------------------------------------------------------------------------------
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

# -----------------------------------------------------------------------------------------------------------


# This allows the socket to be reused immediately.
# Reference: https://stackoverflow.com/questions/6380057/python-binding-socket-address-already-in-use/18858817#18858817
class MyTCPServer(socketserver.TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("*** calling socket.bind ***")
        try:
            self.socket.bind(self.server_address)
            global socket_working
            socket_working = True
        except OSError:
            socket_working = False
            print("********************************************************************")
            print(">>> socket not available; already in use, or wrong ip/port specified")
            print("********************************************************************")
            print("Hint: if you specified the IP addr in this file, it might not match the actual IP addr in use")


# -----------------------------------------------------------------------------------------------------------
def launch_tcp_server(host, port):
    print(">Launching TCPServer: %s / %d" % (host,port))
    with MyTCPServer((host, port), ThreadedTCPRequestHandler) as server:
        if socket_working:
            print("It is running")
            server.serve_forever()
        else:
            print("  ")
            print(">> Server unable to run; socket not available!")
            time.sleep(3)


# -----------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    set_logger()                # calls to log_event allowed **AFTER** this point
    log_event('INFO', 'DEBUG_MSG')
    msg = '============= ReporterHome.py startup ==============================='
    log_event('INFO', 'DEBUG_MSG', msg=msg)
    print(msg)

    # pycam = PyCam.PyCam()       # global state variables kept here; this looks up IP addr for the RPi; need to have it configured
    # print("CameraServer version: %s" % pycam.version)

    # Make sure the target directory exists to write the file to
    head, _ = os.path.split(target)
    Path(head).mkdir(parents=True, exist_ok=True)

    my_ip = "10.1.10.11"        # this is the 'server' that this runs on
    my_port = 65000

    # load previous reports to web page so it shows the most recent into at startup
    webpage.catchup(target)

    while True:
        launch_tcp_server(my_ip, my_port)      # this will run forever, unless the socket is not available
        print("Failed to start tcp server")
        time.sleep(5)
        print("-----")
        print("Retrying to launch_tcp_server...")

