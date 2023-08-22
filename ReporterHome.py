#!/usr/bin/python3
# ReporterHome.py
#   2022.02.18 Joe Ulowetz, Impossible Objects
#   copied from CameraServer.py

# 2022.05.10 JU: plan for testing on different IP/Port than current version
# 2022.08.16 JU: an unhandled exception was occurring over and over until I restarted the service; add sys.exc_info()

# *** WARNING: ALL SOURCE FILES MUST BE CONVERTED TO LINUX EOL CHARACTER BEFORE COPYING TO IO-WEB
# *** REMINDER: THE WEB TARGET FILE IN webpage.py MUST BE WRITTEN DIRECTLY TO /var/www/html/report.html BECAUSE
#               LINKS ARE NOT ALLOWED IN THAT DIRECTORY LIKE I WAS DOING ON RPi's. IT IS A SECURITY RISK TO USE
#               A LINK IN THIS DIRECTORY, which is why they won't work if I try; links are Forbidden.
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
import sys
import reporter_config as cfg


global target     # Reminder: this is on target Linux system
target = None     # Reminder: this is on target Linux system

BUFFER_SIZE = 2048      # For the moment, assume all messages will fit in one buffer length
DELTA = 100             # allow for overhead in socket buffer when comparing if message is too large
ENCODING = 'ascii'      # use 'ascii' or 'utf-8'

action_event = threading.Event()    # set when any action 'run' thread running

socket_working = False      # set to True when server_bind() successfully runs

print("================================================")
print(f"Configured to use IP: {cfg.ip}")
print(f"Configured to use port: {cfg.port}")
print("================================================")


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
        trace_it = []
        output_data_dict = {
            'NetCmd': "NAK",
            'message': "Uncaught exception"}

        trace_it.append(1)
        # ########################################
        # Receive the bytes, which we assume are
        # JSON-encoded string, from the network
        # ########################################
        data_bytes = self.request.recv(BUFFER_SIZE)
        data_str = str(data_bytes, ENCODING)
        log_event("DEBUG", "REPORTER", state="Request", incoming_msg=data_str)


        trace_it.append(2)
        # ########################################
        # Convert the JSON-encoded string into an
        # object, which should be a dictionary
        # ########################################
        try:
            trace_it.append(3)
            input_data_dict = json.loads(data_str)
            trace_it.append(4)

        except ValueError:
            # Server received something from client that is not valid json
            # log_it("{S}: ERROR Server received a string that is not valid JSON")
            trace_it.append(5)
            msg1 = "incoming string is not valid JSON"
            log_event("WARNING", "REPORTER", state="Request", msg=msg1)
            output_data_dict = {
                'NetCmd': "NAK",
                'message': msg1}
        except:
            _, value, traceback = sys.exc_info()
            log_event("ERROR", "REPORTER", msg="Other exception occurred", value=value, traceback=traceback)
            trace_it.append(555)
            trace_it.append(value)
            trace_it.append(traceback)
        else:
            # ########################################
            # Make sure the object we received is a
            # dictionary object as expected
            # ########################################
            trace_it.append(6)
            if type(input_data_dict) is not dict:
                trace_it.append(7)
                msg1 = "received object is not a dictionary"
                output_data_dict = {
                    'NetCmd': "NAK",
                    'message': msg1}
                log_event("WARNING", "REPORTER", state="Request", msg=msg1)
            else:
                # ########################################
                # Save the report
                # ########################################
                trace_it.append(8)
                ts = datetime.datetime.now()
                print("%s Saving record: %s" % (ts.strftime("%m-%d %H:%M:%S "), str(input_data_dict)))

                trace_it.append(81)
                with open(target, 'a') as f:
                    f.write("%s\n" % str(input_data_dict))
                trace_it.append(82)
                webpage.receive(input_data_dict)    # <<<<<<<<<<< This is where OLD web page gets updated
                trace_it.append(83)

                output_data_dict = {
                    'NetCmd': "ACK",
                    'message': "Saved report"}
                trace_it.append(84)

        finally:    # send out server response (unless size too large for network buffer)
            # Note: if there is an unhandled exception somewhere within the camera or network logic, it will
            # be caught here. In that scenario output_data_dict[] has not been initialized, so it causes another
            # exception here. I changed this so output_data_dict[] gets initialized right at the start of the
            # handle() function, and if that version gets returned it is because of some other unhandled exception.
            # misc info
            trace_it.append(9)
            if output_data_dict is None:
                # not sure yet how this happens, but it does
                trace_it.append(10)
                msg1 = "Response dictionary null"
                output_data_dict = {
                    'NetCmd': "NAK",
                    'message': msg1}

            # save the notes we took on path of execution
            trace_it.append(11)
            output_data_dict['trace_it'] = str(trace_it)

            # ########################################
            # turn dictionary into JSON-encoded string
            # ########################################
            log_event("INFO", "REPORTER", state="Response", msg=str(output_data_dict))
            out_string = json.dumps(output_data_dict)       # TODO: could this throw an exception?

            # ########################################
            # convert string to bytes so it can be sent to socket
            # ########################################
            out_bytes = bytes(out_string, ENCODING)

            # make sure we aren't exceeding our expected buffer size limit (it won't)
            if len(out_bytes) >= (BUFFER_SIZE-DELTA):
                msg1 = "response message was too large for network buffer; unable to send"
                log_event("WARNING", "REPORTER", state="Response", msg=msg1)
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
    log_event('INFO', 'REPORTER')
    msg = '============= ReporterHome.py startup ==============================='
    log_event('INFO', 'REPORTER', msg=msg, argv=str(sys.argv))
    log_event('INFO', 'LOGGING', msg='Log file location', location=cfg.log_file_location)
    print(msg)

    # optional arguments:
    #       ReporterHome.py IP PORT ReportFilename
    #       ReporterHome.py 10.1.10.1 65000 reports.txt
    # Example:
    #       ReporterHome.py 10.1.10.11 65000 reports.txt
    # if len(sys.argv) > 1:
    if False:
        # running on my development system for testing
        my_ip = sys.argv[1]
        my_port = int(sys.argv[2])
        raw_target = sys.argv[3]
        target_base = "/home/pi/ImpossibleObjects/ReporterHome"
    else:
        # Running on CentOS7 office web server
        my_ip = cfg.ip                  # "10.1.8.30"  # this is the 'server' that this runs on
        my_port = cfg.port              # 65000  # <<< prod port
        raw_target = cfg.raw_target     # "reports.txt"
        target_base = cfg.target_base   # "/home/julowetz/ReporterHome/Data"

    target = os.path.join(target_base, raw_target)
    log_event('INFO', 'REPORTER', target_base=target_base)

    # Make sure the target directory exists to write the file to
    head, _ = os.path.split(target)
    Path(head).mkdir(parents=True, exist_ok=True)

    # load previous reports to web page so it shows the most recent into at startup
    webpage.catchup(target)

    while True:
        launch_tcp_server(my_ip, my_port)      # this will run forever, unless the socket is not available
        print("Failed to start tcp server")
        time.sleep(5)
        print("-----")
        print("Retrying to launch_tcp_server...")

