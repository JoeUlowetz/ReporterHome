# reporter_config.py

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

# List of printers to show on the web page; the spellings here must exactly match what the printers send
# in the "printer" field of the message. Printers not listed here are ignored. Any number of printers can
# be added here.
control_list = ['JoeWork', '153', '154', '158']

# used in logger.py
log_file_location = "/home/julowetz/ReporterHomeDev/logfiles/report_logfile.log"
logger_name = "ReporterHomeDev"
"""
# ---------------------------------------------------------------------------------------

# Setup for Prod version
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

# List of printers to show on the web page; the spellings here must exactly match what the printers send
# in the "printer" field of the message. Printers not listed here are ignored. Any number of printers can
# be added here.
control_list = ['154', '158', '153']

# used in logger.py
log_file_location = "/home/julowetz/ReporterHome/logfiles/report_logfile.log"
logger_name = "ReporterHome"


