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

"""
# Setup for DEVELOPMENT version
# Used in ReporterHome.py
ip = "10.1.8.30"
port = 65001
target_base = "/home/julowetz/ReporterHomeDev/Data"
raw_target = "reports.txt"

# Used in webpage.py
web_target = "/var/www/html/report_dev.html"        # NOTE: underscore, not dash
test_web_target = "/home/julowetz/ReporterHomeDev/Data/test.html"
web_target_short = "/var/www/html/report_short_dev.html"
detail_target_base = "/home/julowetz/ReporterHomeDev/details"
problem_pages = "/home/julowetz/ReporterHomeDev/Data/problem_pages.txt"
http_terse = "https://io-web.io.local/report_short_dev.html"
http_verbose = "https://io-web.io.local/report_dev.html"

http_source_report = "https://io-web.io.local/source_%s.html"       # use printer name (e.g. 158) as parameter here

# List of printers to show on the web page; the spellings here must exactly match what the printers send
# in the "printer" field of the message. Printers not listed here are ignored. Any number of printers can
# be added here.
control_list = ['JoeWork', '153', '154', '155', '158']
platen_image_pages = ['http://10.1.9.1', 'http://10.1.9.11', 'http://10.1.9.4', 'http://10.1.9.14', 'http://10.1.9.7']
outfeed_image_pages = ['http://10.1.9.2', 'http://10.1.9.112', 'http://10.1.9.5', 'http://10.1.9.15', 'http://10.1.9.8']    # TODO: temp change for 153 Outfeed IP addr
stacker_image_pages = ['http://10.1.9.3', 'http://10.1.9.13', None, 'http://10.1.9.16', 'http://10.1.9.9']     # note: 154 does not have stacker yet, but will someday

# used in logger.py
log_file_location = "/home/julowetz/ReporterHomeDev/logfiles/report_logfile.log"
logger_name = "ReporterHomeDev"
"""
# ---------------------------------------------------------------------------------------

# Setup for ***Prod*** version
# Used in ReporterHome.py
ip = "10.1.8.30"
port = 65000
target_base = "/home/julowetz/ReporterHome/Data"
raw_target = "reports.txt"

# Used in webpage.py
web_target = "/var/www/html/report.html"
web_target_short = "/var/www/html/report_short.html"
test_web_target = "/home/julowetz/ReporterHome/Data/test.html"
detail_target_base = "/home/julowetz/ReporterHome/details"
problem_pages = "/home/julowetz/ReporterHome/Data/problem_pages.txt"
http_terse = "https://io-web.io.local/report_short.html"
http_verbose = "https://io-web.io.local/report.html"

http_source_report = "https://io-web.io.local/source_%s.html"       # use printer name (e.g. 158) as parameter here

# List of printers to show on the web page; the spellings here must exactly match what the printers send
# in the "printer" field of the message. Printers not listed here are ignored. Any number of printers can
# be added here.
#control_list = ['154', '158', '153', '155']
#platen_image_pages = ['http://10.1.9.4', 'http://10.1.9.7', 'http://10.1.9.11', 'http://10.1.9.14']
#outfeed_image_pages = ['http://10.1.9.5', 'http://10.1.9.8', 'http://10.1.9.112', 'http://10.1.9.15']    # TODO: temp change for 153 Outfeed IP addr
#stacker_image_pages = [None, 'http://10.1.9.9', 'http://10.1.9.13', 'http://10.1.9.16']     # note: 154 does not have stacker yet, but will someday
# 2024.06.06 JU: re-ordered the printer list
control_list = ['153', '154', '155', '158']
platen_image_pages = ['http://10.1.9.11', 'http://10.1.9.4', 'http://10.1.9.14', 'http://10.1.9.7']
outfeed_image_pages = ['http://10.1.9.112', 'http://10.1.9.5', 'http://10.1.9.15', 'http://10.1.9.8']    # TODO: temp change for 153 Outfeed IP addr
stacker_image_pages = ['http://10.1.9.13', None, 'http://10.1.9.16', 'http://10.1.9.9']     # note: 154 does not have stacker yet, but will someday

# used in logger.py
log_file_location = "/home/julowetz/ReporterHome/logfiles/report_logfile.log"
logger_name = "ReporterHome"


