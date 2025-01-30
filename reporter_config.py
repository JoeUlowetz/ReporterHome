# reporter_config.py

"""
Documentation:


/var/www/html   Web page folder contents:
report.html             Prod web page
report_short.html       terse version of Prod web page
report_dev.html         Dev web page
report_short_dev.html   terse version of Dev web page

Source code report for printers:
source_153.html
source_154.html
source_155.html
source_158.html
source_JoeWork.html

Cached files used to create web pages:
/home/julowetz/ReporterHome/Data  -or-  /home/julowetz/ReporterHomeDev/Data
These files contain table stats for today. The number in each name is the index into `control_list`
    today_stats_0
    today_stats_1
    today_stats_2
This comes in a message with the tag 'today_stats'; it gets sent out as each page completes printing,
plus in several other places such as when the print job is paused. The info is generated in the printer
from Performance.prepare_today_summary() in the module statistics.py

These files contain table stats for previous days:
    hist_stats_0
    hist_stats_1
    hist_stats_2
This info comes in a message from the printer with the tag 'hist_stats'; it is only sent by the printer
when the printer starts up. The info is generated in the printer by Performance.prepare_past_summary()
in the module statistics.py

"""

#=============================================================================================================

import os
import pika
cwd = os.getcwd()

# common stuff for RabbitMQ (this can also run from ReporterHome.write_to_rabbitmq() in case connection goes down)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
queue = 'webpub'
channel = connection.channel()
channel.queue_declare(queue=queue)

# Control which config to use by whether we are running in the Dev directory or not!
if 'ReporterHomeDev' in cwd:

    # Setup for DEVELOPMENT version
    # Used in ReporterHome.py
    ip = "10.1.8.30"
    port = 65001
    target_base = "/home/julowetz/ReporterHomeDev/Data"
    raw_target = "reports.txt"
    sys_ver = "*DEV*"           # used for print statements so I can sort out DEV from PROD


    use_rabbitmq = False        # <<< control whether to use RabbitMQ for sending data to web app


    #
    # Used for direct write to web server location, use_rabbitmq = False
    #
    web_target = "/var/www/html/report_dev.html"
    web_target_orig = "/var/www/html/report_orig_dev.html"
    web_target_short = "/var/www/html/report_short_dev.html"

    #
    # Used for buffering to RabbitMQ queue, use_rabbitmq = True
    #
    base_web_target = "report_dev.html"                 # new version w/ camera images shown
    base_web_target_orig = "report_orig_dev.html"       # version without images (original webpage)
    base_web_target_short = "report_short_dev.html"     # terse version w/o daily stats


    # test_web_target = "/home/julowetz/ReporterHomeDev/Data/test.html"       # DEPRECATED
    # detail_target_base = "/home/julowetz/ReporterHomeDev/details"           # DEPRECATED


    problem_pages = "/home/julowetz/ReporterHomeDev/Data/problem_pages.txt"
    http_terse = "http://io-web.io.local/report_short_dev.html"
    http_verbose = "http://io-web.io.local/report_dev.html"
    http_orig = "http://io-web.io.local/report_orig_dev.html"



    source_report = "/var/www/html/source_%s.html"      # used with printer_name to generate source code change report

    http_source_report = "http://io-web.io.local/source_%s.html"       # use printer name (e.g. 158) as parameter here

    # List of printers to show on the web page; the spellings here must exactly match what the printers send
    # in the "printer" field of the message. Printers not listed here are ignored. Any number of printers can
    # be added here.
    control_list = ['JoeWork', '153', '154', '155', '158']
    platen_image_pages = ['http://10.1.9.1', 'http://10.1.9.11', 'http://10.1.9.4', 'http://10.1.9.14', 'http://10.1.9.7']
    outfeed_image_pages = ['http://10.1.9.2', 'http://10.1.9.112', 'http://10.1.9.5', 'http://10.1.9.15', 'http://10.1.9.8']    # TODO: temp change for 153 Outfeed IP addr
    stacker_image_pages = ['http://10.1.9.3', 'http://10.1.9.13', 'http://10.1.9.6', 'http://10.1.9.16', 'http://10.1.9.9']     # note: 154 does not have stacker yet, but will someday

    # this list in same order as control_list, with address for CURRENT.jpg image, plus %s to use for inserting value to make each request unique
    printer_images = ['http://10.1.9.3/CURRENT.jpg?%s',
                      'http://10.1.9.13/CURRENT.jpg?%s',
                      'http://10.1.9.5/CURRENT.jpg?%s',         # outfeed image because 154 doesn't have a stacker camera
                      'http://10.1.9.16/CURRENT.jpg?%s',
                      'http://10.1.9.9/CURRENT.jpg?%s' ]

    # used in logger.py
    log_file_location = "/home/julowetz/ReporterHomeDev/logfiles/report_logfile.log"
    logger_name = "ReporterHomeDev"

else:    # ---------------------------------------------------------------------------------------

    # Setup for ***Prod*** version
    # Used in ReporterHome.py
    ip = "10.1.8.30"
    port = 65000
    target_base = "/home/julowetz/ReporterHome/Data"
    raw_target = "reports.txt"
    sys_ver = "*PROD*"           # used for print statements so I can sort out DEV from PROD


    use_rabbitmq = False        # <<< control whether to use RabbitMQ for sending data to web app


    #
    # Used for direct write to web server location, use_rabbitmq = False
    #
    web_target = "/var/www/html/report.html"
    web_target_orig = "/var/www/html/report_orig.html"
    web_target_short = "/var/www/html/report_short.html"


    #
    # Used for buffering to RabbitMQ queue, use_rabbitmq = True
    #
    base_web_target = "report.html"                     # new version w/ camera images shown
    base_web_target_orig = "report_orig.html"           # version without images (original webpage)
    base_web_target_short = "report_short.html"         # terse version w/o daily stats


    # test_web_target = "/home/julowetz/ReporterHome/Data/test.html"          # DEPRECATED
    # detail_target_base = "/home/julowetz/ReporterHome/details"              # DEPRECATED

    problem_pages = "/home/julowetz/ReporterHome/Data/problem_pages.txt"
    http_terse = "http://io-web.io.local/report_short.html"
    http_verbose = "http://io-web.io.local/report.html"
    http_orig = "http://io-web.io.local/report_orig.html"

    source_report = "/var/www/html/source_%s.html"      # used with printer_name to generate source code change report

    http_source_report = "http://io-web.io.local/source_%s.html"       # use printer name (e.g. 158) as parameter here

    # List of printers to show on the web page; the spellings here must exactly match what the printers send
    # in the "printer" field of the message. Printers not listed here are ignored. Any number of printers can
    # be added here.
    # 2024.06.06 JU: re-ordered the printer list
    control_list = ['153', '154', '155', '158']
    platen_image_pages = ['http://10.1.9.11', 'http://10.1.9.4', 'http://10.1.9.14', 'http://10.1.9.7']
    outfeed_image_pages = ['http://10.1.9.112', 'http://10.1.9.5', 'http://10.1.9.15', 'http://10.1.9.8']    # TODO: temp change for 153 Outfeed IP addr
    stacker_image_pages = ['http://10.1.9.13', 'http://10.1.9.6', 'http://10.1.9.16', 'http://10.1.9.9']     # note: 154 does not have stacker yet, but will someday

    # this list in same order as control_list, with address for CURRENT.jpg image, plus %s to use for inserting value to make each request unique
    printer_images = ['http://10.1.9.13/CURRENT.jpg?%s',
                      'http://10.1.9.5/CURRENT.jpg?%s',         # outfeed image because 154 doesn't have a stacker camera
                      'http://10.1.9.16/CURRENT.jpg?%s',
                      'http://10.1.9.9/CURRENT.jpg?%s' ]

    # used in logger.py
    log_file_location = "/home/julowetz/ReporterHome/logfiles/report_logfile.log"
    logger_name = "ReporterHome"


