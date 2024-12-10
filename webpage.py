# *** WARNING: ALL SOURCE FILES MUST BE CONVERTED TO LINUX EOL CHARACTER BEFORE COPYING TO IO-WEB
# *** REMINDER: THE WEB TARGET FILE IN webpage.py MUST BE WRITTEN DIRECTLY TO /var/www/html/report.html BECAUSE
#               LINKS ARE NOT ALLOWED IN THAT DIRECTORY LIKE I WAS DOING ON RPi's. IT IS A SECURITY RISK TO USE
#               A LINK IN THIS DIRECTORY, which is why they won't work if I try; links are Forbidden.
import datetime
import ast
import time
from logger import set_logger, log_event
import os
import reporter_config as cfg
# from copy import deepcopy

from ReporterHome import write_to_rabbitmq

"""
2023.08.22 Changed style section to dark mode, per suggestion from Thor
2023.09.06 Support new camera status strings
2023.10.06 Added counting of pause reasons

TODO:
    today_pause_lists  for today info
    create storage for past days
    watch time, and when midnight wraps, push today info to yesterday storage, going back X days; when doing this, write to text files
    
"""




"""
Message format interpretation:

if field 'timestamp' present:
    set timestamp[prt] = ['timestamp']

if field 'model_name' present:          (populated in cbam_printer_gui.py ln 2274-2295)
        (In the future, this will be part of ['state2'] == 'Start Print Job')
    set max_page[prt] = ['total_pages']
    if 'build_id' present:
        set build_id[prt] to ['build_id']
    if 'operator_name' present:
        set operator[prt] = ['operator_name']
    if 'note' present:
        set note[prt] = ['note']

else if 'model_name' not present
    if 'state' present:
        if ['state'] != 'Paused'
            pause_reason[prt] = None    #clear this field if not paused

        if ['state'] == 'Printing page':
            set state[prt] to 'RUNNING'
            set page_num[prt] to ['page_num']
            set build_id[prt] to ['traveler_num']

        elif ['state'] == 'Paused':
            set state[prt] = 'Paused'
            if 'pause_reason' present:
                pause_reason[prt] = ['pause_reason']
            else:
                pause_reason[prt] = None

        elif ['state']  == 'Software startup':
            set state[prt] to 'Software startup'
            set max_page[prt] to ''
            set build_id[prt] to ''
            set note[prt] to ''

        elif ['state'] == 'Start Print Job':
            set state[prt] to 'Start Print Job'

        elif ['state'] == 'FIRMWARE_VERSIONS':
            set state[prt] to 'FIRMWARE_VERSIONS'

Other types w/o 'state':
    'Job_config_file'       < this info is already with the 'model_name' field

"""

# web_target = cfg.web_target                     # "/var/www/html/report.html"
# web_target_short = cfg.web_target_short        # "/var/www/html/report_short.html"
# test_web_target = cfg.test_web_target           # "/home/julowetz/ReporterHome/Data/test.html"
# detail_target_base = cfg.detail_target_base     # "/home/julowetz/ReporterHome/details"     DEPRECATED
problem_pages = cfg.problem_pages               # "/home/julowetz/ReporterHome/Data/problem_pages.txt"
control_list = cfg.control_list                 # ['154', '158', '153']        # <<< Edit this list to change which printers appear on the web page <<<===========

control_list_length = len(control_list)

# lists containing attributes for the printers specified in the control list
build_id = [0] * control_list_length
operator = [''] * control_list_length
note = [''] * control_list_length
page_num = [0] * control_list_length
timestamp = [0] * control_list_length
max_page = [0] * control_list_length
state = [''] * control_list_length
color = ['Gray'] * control_list_length    # used for background color of state info
pause_reason = [None] * control_list_length

fiber = [None] * control_list_length         # added 2023.03.28 JU
sheet_size = [None] * control_list_length
polymer = [None] * control_list_length

platen_camera_status = [None] * control_list_length
outfeed_camera_status = [None] * control_list_length
stacker_camera_status = [None] * control_list_length

platen_camera_color = [None] * control_list_length
outfeed_camera_color = [None] * control_list_length
stacker_camera_color = [None] * control_list_length

# 2023.10.27 JU
platen_camera_throttled = ['x'] * control_list_length
outfeed_camera_throttled = [''] * control_list_length
stacker_camera_throttled = [''] * control_list_length

# 2024.02.08 JU: buffer used to receive source code report, comes in parts because of size
source_code_report = [''] * control_list_length
source_code_report2 = [''] * control_list_length
# after a source_code_report is received, this saves the beginning of that data, so it can be tested for the CHANGED flag
current_source_code_report_header = [''] * control_list_length

status_list = [None] * control_list_length
# status_list is a list of length control_list_length
# each entry in status_list is a list of a variable number of status_entries (could be empty)
# each status_entry is a list of 5 strings (3rd actually an integer)
# For example:
#   status_list = [ prt1_list, prt2_list, prt3_list, prt4_list, ...]    Number of entries = control_list_length (number of printers being reported)
#   prt1_list = [ day1_entry, day2_entry, day3_entry, day4_entry, ... ]      Number of days configured on a PC for it to send; today is NOT part of this list
#   day1_entry = [ 'Monday 3/06', '12%', 45, '10:10', '14:42', 3, 15% of 23]          Entries are:  date, active_time_pct, pages_printed, start_time, end_time, restarted, unattended

# values used to report status for today, for each printer
today_list = [None] * control_list_length
# Each item in today_list is a list of 4 items
#   today_list =  [prt1_today, prt2_today, prt3_today, prt4_today, ...]
#   prt1_today = [ '87%', 123, '07:34', '16:20' ]   which is [ active%, pages, start time, end time]

today_pause_lists = [None] * control_list_length
# Each entry here is a dict with key=pause_reason, value=count greater than 0

# constants to build html later
#header = '<html lang="en"><body><meta http-equiv="refresh" content="30" ><head><style>td {border: 0}</style></head>\n'     # Note: this number is auto web page refresh interval
# *PART-1*
header = """
<html lang="en"><body><meta http-equiv="refresh" content="30" >
<head>
<style>
body {
background-color:#2d2d2d;
}
header {
text-align: right;
    padding: 0 1%;
    }
h1 {font-family: 'Avenir', sans-serif;
font-size: 3em;
    margin:1 0;
padding:0 10;
text-align:left;
color:#FFFFFF;
    font-kerning: auto;
}
h2 {font-family: 'Railway', sans-serif;
color: SlateGrey;
    }
table {
    font-family: 'Avenir', sans-serif;
    padding:4;
    color: #ffffff;
    }
th {
border:0;
    padding:10;
    }
.wrap {
    width: 80%;
    margin: 0 auto;
}
.printer td{
text-align: left;
}        
.progress td {border: 0;
border-left: 1px solid #ddd;
text-align: center;
    padding: 2
    }
.progress td:first-child {
    border-left: none;
}
tr:nth-child(even) {
    background-color: #3D3D3D;
    }
.bold {font-weight: bold}
.tomato {background-color: Tomato}
.dodger {background-color: DodgerBlue}
.yellow {color: blue; background-color: Yellow}
.blue {color: yellow; background-color: blue}
.violet {background-color: Violet}
.lightgray {color: black; background-color: LightGray}
.mediumseagreen {background-color: MediumSeaGreen}
.orange {font-weigtht: 700; color: blue; background-color: Orange}
.red {color: white; background-color: Red}

.row {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  width: 100%;
  margin: 10px 0;
}

.column1{
  display: flex;
  flex-direction: column;
  flex-basis: 100%;
  flex: 1;
  margin: 0 10px;
}

.column2 {
  display: flex;
  flex-direction: column;
  flex-basis: 100%;
  flex: 2;
  margin: 0 10px;
}

</style>
</head>\n
"""


# *PART-2*
date_header = '<header><h2>%s</h2></header>\n'

# *PART-3*
class_wrap = '<div class="wrap"><br>\n'

# *SECTION-1, PART-1*
section_start = """<section class="row"><div class="printer column1" border="1" style="border: 1px solid black; border-radius: 10px;"><h1>%s</h1><table>\n"""

# *SECTION, PART-2*
status_tag = """<tr>
    <td><a href="%s" style="color:#E3D739;" target="_blank" rel="noopener noreferrer">Status:</a></td>
    <td style="background-color:%s;">%s</td>
    <td>%s</td>
</tr>"""
# use following version if we need to flag that the source report file has changes in it
status_tag_changed = """<tr>
    <td><a href="%s" style="color:Blue;background-color:Yellow;font-weight:bold" target="_blank" rel="noopener noreferrer">%s Status:</a></td>
    <td style="background-color:%s;">%s</td>
    <td>%s</td>
</tr>"""

# p_reason = '<tr><td>Pause reason</td><td></td><td style="background-color:Orange;">%s</td><td></td><td></td></tr>\n'
p_reason = """<tr><td>Pause reason:</td><td style="background-color:Orange;">%s</td><td></td></tr>\n"""

# page = '<tr><td>Page</td><td></td><td style="font-weight:bold">%d of %d</td><td></td><td>%s</td></tr>\n'
page = """<tr><td>Page:</td>
    <td class="bold">%d of %d</td>
    <td>%s</td>
</tr>\n"""

# traveler = '<tr><td>Traveler #</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
traveler = """<tr><td>Traveler #:</td><td class="bold">%s</td><td></td></tr>\n"""

# oper_str = '<tr><td>Operator</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
oper_str = """<tr><td>Operator:</td><td class="bold">%s</td><td></td></tr>\n"""

# note_str = '<tr><td>Note</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
note_str = """<tr><td>Note:</td><td class="bold">%s</td><td></td></tr>\n"""

# fiber_str = '<tr><td>Fiber</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
fiber_str = """<tr><td>Fiber:</td><td class="bold">%s</td><td></td></tr>\n"""

# sheet_size_str = '<tr><td>Sheet size</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
sheet_size_str = """<tr><td>Sheet size:</td><td class="bold">%s</td><td></td></tr>\n"""

# polymer_str = '<tr><td>Polymer</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
polymer_str = """<tr><td>Polymer:</td><td class="bold">%s</td><td></td></tr>\n"""

#*SECTION, PART-3*
table_1_end = "</table>\n"


section_footer = '</div></br>\n'

# <th><img src="http://10.1.9.16/CURRENT.jpg??80172489074"" height="300" alt=""/>
# <th><img src="file://10.1.9.1/share/ImpossibleObjects/camera/CURRENT.jpg"" height="300" alt=""/>

# 2024.12.06 JU
printer_image = """
<div class="progress center column3"><table border="1" style='border: 1px solid black; border-radius: 10px;'>
            <tr>
            <th><a href="%s" target="_blank"><img src="%s" " height="300" alt=""/></a>
            </tr>
</table></div>
"""

# 2023.10.27 JU: add additional parameter to show throttled status, if any
# *SECTION, PART-4*  wrap w/ <table>...</table>
platen_str_0 = """<tr><td>Platen Camera:%s</td><td class="%s">%s</td></tr>\n"""
platen_str = """<tr><td><a href="%s" style="color:#E3D739;" target="_blank" rel="noopener noreferrer">Platen Camera:%s</a></td><td class="%s">%s</td></tr>\n"""

outfeed_str_0 = """<tr><td>Outfeed Camera:%s</td><td class="%s">%s</td></tr>\n"""
outfeed_str = """<tr><td><a href="%s" style="color:#E3D739;" target="_blank" rel="noopener noreferrer">Outfeed Camera:%s</a></td><td class="%s">%s</td></tr>\n"""

stacker_str_0 = """<tr><td>Stacker Camera:%s</td><td class="%s">%s</td></tr>\n"""
stacker_str = """<tr><td><a href="%s" style="color:#E3D739;" target="_blank" rel="noopener noreferrer">Stacker Camera:%s</a></td><td class="%s">%s</td></tr>\n"""

# *SECTION, PART-5*
dev_end = '</dev>\n'

# *SECTION, PART-6*     handled in display_status()


final_footer = '</body></html>\n'

detail_index = 0


# ==============================================================================
# Source status web page:
status_header1 = \
    """
    <!DOCTYPE html>
    <html lang="en">
    
    <head>
      <title>    
    """
status_header2 = \
    """
      </title>
      <style>
        /* Set base styles for tables */
        body {
          font-family: 'Avenir', sans-serif;
            background: #3d3d3d;
            color:white;
         }
        h1 {
          font-size: 3em;
          margin: 1 0;
          padding: 0 10;
          text-align: left;
          font-kerning: auto;
        }
        table {
          border-collapse: collapse;
          width: 100%;
          margin-bottom: 1rem;
        }
        
        th, td {
          padding: 0.5rem;
          text-align: left;
          border: 1px solid #ddd;
        }
        
        th {
          background-color: #2D2D2D;
        }
        
        /* Use media queries for responsive adjustments */
        @media only screen and (max-width: 768px) {
          table {
            font-size: 0.8rem;
          }
          
          th, td {
            padding: 0.25rem;
          }
        }
      </style>
    </head>
    
    <body>
    """


# ==============================================================================
def format_as_of(tstamp):
    # what day is timestamp?
    date1 = datetime.date.fromtimestamp(tstamp)
    year1 = date1.year
    month1 = date1.month
    day1 = date1.day

    # what day is today?
    date2 = datetime.date.fromtimestamp(time.time())
    year2 = date2.year
    month2 = date2.month
    day2 = date2.day

    if year1 == year2 and month1 == month2 and day1 == day2:
        return time.strftime("as of %H:%M", time.localtime(tstamp))

    return time.strftime("since %A %B %d, %H:%M", time.localtime(tstamp))   # "since Monday March 15, 17:40"


def count_pause_reasons(report_dict):
    """
    Note: currently 'pause_reason' comes on both 'state' and 'state2' messages; don't double count; just use one of them.

    Look at the current date to see when to roll counts over from today to previous day.
    :param report_dict:
        report_dict['pause_reason']  count occurrances of each type
        report_dict['printer']      this will be 153, 154, 158, etc.; identify the printer it is for

    :return:    True if something changed, False if no change
    """
    if 'pause_reason' not in report_dict:
        return False      # this is not a record we are interested in
    if 'state2' in report_dict:
        return False     # don't double-count, just look at 'state' reports

    printer_name = report_dict.get('printer')
    reason = report_dict.get('pause_reason')

    index = control_list.index(printer_name)
    if index > control_list_length:
        print(f"[{cfg.sys_ver}] BUG in count_pause_reason")
        return

    if today_pause_lists[index] is None:
        today_pause_lists[index] = {}       # initialize fresh dictionary

    if reason in today_pause_lists[index]:
        today_pause_lists[index][reason] += 1
    else:
        today_pause_lists[index][reason] = 1

    return True


def log_page_problems(report_dict):     # TODO: change this to count occurrances of pause reasons per printer, per day
    # Note: "problem_pages.txt" is to record when the printer was paused, or when "set page number" is used
    if 'pause_reason' in report_dict or 'Set_next_page_to_print' in report_dict:
        f = open(problem_pages, 'a')
        #now = datetime.datetime.now()
        ts = datetime.datetime.fromtimestamp(report_dict['timestamp'])
        tag = ts.strftime("%Y-%m-%d %H:%M:%S")
        f.write("%s - %s\n" % (tag, str(report_dict)))
        f.close()


def display_status(prt, output):
    if status_list[prt] is None and today_list[prt] is None:
        return

    progress_table_start = \
        """<div class="progress center column2"><table border="1" style='border: 1px solid black; border-radius: 10px;'>
            <tr>
            <th>Date</th>
            <th>Active</th> 
            <th>Pages</th>
            <th>Start Time</th>
            <th>End Time</th>
            <th>Restarted</th>
            </tr>
        """

    # old version w/ Unattended column
    """<div class="progress center column2"><table border="1" style='border: 1px solid black; border-radius: 10px;'>
        <tr>
        <th>Date</th>
        <th>Active</th> 
        <th>Pages</th>
        <th>Start Time</th>
        <th>End Time</th>
        <th>Restarted</th>
        <th>Unattended</th>
        </tr>
    """

    output.append(progress_table_start)

    day_list = status_list[prt]     # could be empty
    if day_list is not None:
        cnt = len(day_list)
        print(f"[{cfg.sys_ver}] JOE number of history entries: {cnt}")
        for day_item in day_list:
            # first field is the date; it might be in yyyy-mm-dd format, or Weekday mm/dd format
            if type(day_item) is not list:
                print(f"[{cfg.sys_ver}] ---not a list--")
                continue
            if len(day_item) < 7:
                print(f"[{cfg.sys_ver}] ---too few items--")
                continue

            the_date = day_item[0]
            if len(the_date) < 2:
                print(f"[{cfg.sys_ver}] ---invalid date--")
                continue

            # print(f"*** day_item: {day_item}")
            # print(f"*** the_date: {the_date}")
            if '-' in the_date:
                dt = datetime.datetime.strptime(the_date, "%Y-%m-%d")   # reformat the date
                # print(dt)
                the_date = dt.strftime("%a %m/%d")  # Mon 03/24
            # else use as-is

            output.append('<tr>')
            output.append(f'<td>{the_date}</td>')   # Date
            output.append(f'<td style="text-align: center">{day_item[1]}</td>')   # Active Pct
            output.append(f'<td style="text-align: center">{day_item[2]}</td>')   # Pages
            output.append(f'<td style="text-align: center">{day_item[3]}</td>')   # Start time
            output.append(f'<td style="text-align: center">{day_item[4]}</td>')   # End time
            output.append(f'<td style="text-align: center">{day_item[5]}</td>')   # Restarted
            # output.append(f'<td style="text-align: center">{day_item[6]}</td>')   # Unattended
            output.append('</tr>\n')

    # add table line for today
    data = today_list[prt]
    # if data is not None:
    #     cnt2 = len(data)
    #     print(f"JOE number of today entries: {cnt2}")
    if data is not None and len(data) == 7:
        # The date might be a string (use as-is), or a date; if the date is today, change to string, otherwise show as nice date
        the_date = data[0]
        if '-' in the_date:
            # see if still today:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if today_str == the_date:
                the_date = 'Today so far'
            else:
                dt = datetime.datetime.strptime(the_date, "%Y-%m-%d")
                the_date = dt.strftime("%a %m/%d")  # Mon 03/24
        # else use as-is

        output.append('<tr>')
        output.append(f'<td>{the_date}</td>')    # 'Today so far'
        output.append(f'<td style="text-align: center">{data[1]}</td>')    # today pct
        output.append(f'<td style="text-align: center">{data[2]}</td>')    # today pages
        output.append(f'<td style="text-align: center">{data[3]}</td>')    # today start
        output.append(f'<td style="text-align: center">{data[4]}</td>')    # today end
        output.append(f'<td style="text-align: center">{data[5]}</td>')    # Restarted
        # output.append(f'<td style="text-align: center">{data[6]}</td>')    # Unattended
        output.append('</tr>\n')

    output.append('</table></div>')   # end of this table


def database_cmd(report_dict: dict):
    """
    Save data in database; no web page activity done.

    [[maybe use preset formats for updating different tables???]]

    :param report_dict:
            'database': True,
            'printer': name of printer,
            'table': table,
            'row': data to save in database, passed as a string; use literal_eval() to revert to dict
            'action': 'insert' to insert the (new) row in the table, 'update' [?] to update existing row
            'where': this is the where clause used with the update action [?]
            'timestamp': round( time.time(), 3),
            'datetime': datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    :return:    none
    """
    pass


def receive(report_dict):
    # every report entry has 'printer' or 'printer_name' in it
    # find 'index' for which printer this info is for:
    # 0 = #154
    # 1 = #158
    # 2 = ignore this
    # start_time = time.time()
    print(f"[{cfg.sys_ver}] --receive--")
    # details = []
    # details.append("%s : receive ----------" % timestamper())
    # log_page_problems(report_dict)    # obsolete

    ts = datetime.datetime.now()    # TODO: remove/testing
    debug_path = '/home/julowetz/ReporterHomeDev/details'
    this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_10-RECEIVE_start.txt")  # TODO: remove/testing
    with open(this_file, 'w') as f:
        for key, value in report_dict.items():
            f.write(f"{key}: {value}\n")

    if 'database' in report_dict and 'table' in report_dict:
        # this is the new command to send data to the database
        database_cmd(report_dict)
        return

    refresh_pause_page = count_pause_reasons(report_dict)

    print(f"[{cfg.sys_ver}] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(f"[{cfg.sys_ver}] {str(report_dict)}")

    # 2022.05.20 JU: fixed so either format of printer name will work
    # 2023.03.07 JU: changed again so driven by control_list variable defined at head of this file
    printer_name = report_dict['printer']

    if printer_name not in control_list:
        print(f"[{cfg.sys_ver}] !!! Received printer name not in control_list:  {printer_name}")
        log_event("ERROR", "REPORTER", msg="Received printer name not in control_list", printer_name=printer_name, control_list=control_list)
        return

    prt = control_list.index(printer_name)      # this throws exception if printer_name not in the list

    # 2024.02.08 JU: if this contains the key "SOURCE_REPORT_PART" or "SOURCE_REPORT_TEXT" this data is used for
    #   the source code difference report page.
    if 'SOURCE_REPORT_PART' in report_dict:
        content = report_dict['SOURCE_REPORT_PART']
        source_code_report[prt] += content
        return  # wait until entire contents received before doing anything else
    if 'SOURCE_REPORT_TEXT' in report_dict:
        content = report_dict['SOURCE_REPORT_TEXT']
        source_code_report[prt] += content
        create_source_code_page_new(printer_name, prt)      # this clears source_code_report[prt] when done
        return


    # 2024.09.19 JU: NEW version of the status report, more fields, different format
    if 'SOURCE_REPORT2_PART' in report_dict:
        content = report_dict['SOURCE_REPORT2_PART']

        this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_A-content_part.txt")     # TODO: remove/testing
        with open(this_file, 'w') as f:
            f.write(content)

        this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_B-source_code_report2_before_adding_content.txt")    # TODO: remove/testing
        with open(this_file, 'w') as f:
            f.write(source_code_report2[prt])


        source_code_report2[prt] += content

        this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_C-source_code_report2_after_adding_content.txt")     # TODO: remove/testing
        with open(this_file, 'w') as f:
            f.write(source_code_report2[prt])

        return  # wait until entire contents received before doing anything else
    if 'SOURCE_REPORT2_END' in report_dict:
        content = report_dict['SOURCE_REPORT2_END']

        this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_X-content_final.txt")     # TODO: remove/testing
        with open(this_file, 'w') as f:
            f.write(content)

        this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_Y-source_code_report2_before_adding_final_content.txt")    # TODO: remove/testing
        with open(this_file, 'w') as f:
            f.write(source_code_report2[prt])

        source_code_report2[prt] += content


        this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_Z-source_code_report2_after_adding_final_content.txt")     # TODO: remove/testing
        with open(this_file, 'w') as f:
            f.write(source_code_report2[prt])

        print(f"[{cfg.sys_ver}] <<<<<<<<<<<<< creating NEW report  !!!!!!!!!!!!!!!!!!!!>>>>>>>>>>>")
        create_source_code_page_new2(printer_name, prt)      # this clears source_code_report2[prt] when done
        return


    # details.append("Printer index = %d" % prt)
    # All the remaining fields get parsed/used by the one particular printer this message is for
    if report_dict.get('timestamp') is not None:        # 2023.06.21 JU: changed to use get
        ts = float(report_dict['timestamp'])
        timestamp[prt] = format_as_of(ts)
        # details.append("timestamp is present")

    if 'model_name' in report_dict:
        # clear current values and load new ones:
        # details.append("model_name is present")
        if 'build_id' in report_dict:
            build_id[prt] = report_dict['build_id'] 		# from 'build_id'
            # details.append("build_id is present")
        if 'operator_name' in report_dict:
            operator[prt] = report_dict['operator_name']		# from 'operator_name'
            # details.append("operator_name is present")
        if 'note' in report_dict:
            note[prt] = report_dict['note']			# from 'note'
            # details.append("note is present")
        if 'total_pages' in report_dict:
            max_page[prt] = int(report_dict['total_pages'])
            # details.append("max_page = %d" % max_page[prt])

    elif 'state' in report_dict:
        # details.append("state is present")
        if report_dict['state'] != 'Paused':
            pause_reason[prt] = None        # make sure this gets erased for any other state
        if report_dict['state'] == 'Printing page':
            state[prt] = 'RUNNING'
            color[prt] = 'DodgerBlue'
            page_num[prt] = int(report_dict['page_num'])
            build_id[prt] = report_dict['traveler_num']		# yes, traveler_num is the same as build_id in other message
            # details.append("state == Printing page")
        elif report_dict['state'] == 'Paused':
            state[prt] = 'Paused'
            color[prt] = 'Orange'
            # details.append("state == Paused")
            # maybe also show pause reason (if provided)
            if 'pause_reason' in report_dict:
                if len(report_dict['pause_reason']) > 0:
                    pause_reason[prt] = report_dict['pause_reason']
                else:
                    pause_reason[prt] = None
            else:
                pause_reason[prt] = None
        elif report_dict['state'] == 'Software startup':
            state[prt] = 'Software startup'
            color[prt] = 'LightGray'
            operator[prt] = ''  # erase old values if starting again
            note[prt] = ''
            max_page[prt] = ''
            build_id[prt] = ''
            # fiber[prt] = None           # ???
            # sheet_size[prt] = None      # ???
            # polymer[prt] = None         # ???
            # details.append("state == Software startup")
        elif report_dict['state'] == 'Start Print Job':
            state[prt] = 'Start Print Job'
            color[prt] = 'Violet'
            # details.append("state == Start Print Job")
        elif report_dict['state'] == 'Resume printing':
            state[prt] = 'Resume printing'
            color[prt] = 'DodgerBlue'
            # details.append("state == Resume printing")
        elif report_dict['state'] == 'Shutdown':
            state[prt] = 'Shutdown'
            color[prt] = 'Tomato'
            # details.append("state == Shutdown")
        elif report_dict['state'] == 'Cancel Print Job':
            state[prt] = 'Cancelled Job'
            color[prt] = 'Tomato'
            # details.append("state == Cancel Print Job")
        elif report_dict['state'] == 'Print job complete':
            state[prt] = 'Finished!'
            color[prt] = 'MediumSeaGreen'
            # details.append("state == Print job complete")
        else:
            state[prt] = report_dict['state']   # includes 'FIRMWARE_VERSIONS'
            color[prt] = 'Gray'
            # details.append("state is other: %s" % state[prt])

    if 'data2' in report_dict:
        data2 = report_dict['data2']
        # details.append("data2 is present: %s" % data2)
        if data2 == 'camera_status':
            platen = report_dict['platen']
            platen_camera_status[prt] = platen
            platen_camera_color[prt] = set_camera_color(platen)

            outfeed = report_dict['outfeed']
            outfeed_camera_status[prt] = outfeed
            outfeed_camera_color[prt] = set_camera_color(outfeed)

            stacker = report_dict['stacker']
            stacker_camera_status[prt] = stacker

            stacker_camera_color[prt] = set_camera_color(stacker)
            # details.append("Platen = %s, Outfeed = %s, Stacker = %s" % (platen, outfeed, stacker))

    # 2023.03.10 JU: report printer daily activity numbers
    if report_dict.get('today_stats') is not None:        # Today: this will probably be sent out once a minute     2023.06.21 JU: changed to use get
        print(f"[{cfg.sys_ver}]  today_stats found")
        today_stats = report_dict['today_stats']        # example:   '12%,45,10:10,14:42'
        print(f"[{cfg.sys_ver}] today_stats contents: {today_stats}")
        tup = today_stats.split(',')        # [0] = 'Today so far', [1] = active%, [2] = pages, [3] = start_time, [4] = end_time, [5] = restarts, [6] = unattended
        if tup is not None and len(tup) == 7:
            today_list[prt] = tup
        else:
            print(f"[{cfg.sys_ver}] did not save to today_list:  {tup}")
        filename = "Data/today_stats_%d" % prt
        with open(filename, 'w') as f:       # save raw data to file in case web server restarts
            f.write(today_stats)

    if 'job_fiber' in report_dict:
        fiber[prt] = report_dict['job_fiber']

    if 'job_sheet_size' in report_dict:
        sheet_size[prt] = report_dict['job_sheet_size']

    if 'job_polymer' in report_dict:
        polymer[prt] = report_dict['job_polymer']

    # 2023.10.27 JU added
    if 'platen_throttled' in report_dict:
        value1 = report_dict['platen_throttled']
        if value1 is None:
            platen_camera_throttled[prt] = ''
        elif value1.strip() == '0x0':
            platen_camera_throttled[prt] = ''
        elif value1.strip() == '0x50005':
            platen_camera_throttled[prt] = '--throttled NOW--'
        elif value1.strip() == '0x50000':
            platen_camera_throttled[prt] = '--throttled--'
        else:
            # not sure what other values might be here; fix this when I know better
            platen_camera_throttled[prt] = ' %s ' % value1

    if 'outfeed_throttled' in report_dict:
        value2 = report_dict['outfeed_throttled']
        if value2 is None:
            outfeed_camera_throttled[prt] = ''
        elif value2.strip() == '0x0':
            outfeed_camera_throttled[prt] = ''
        elif value2.strip() == '0x50005':
            outfeed_camera_throttled[prt] = '--throttled NOW--'
        elif value2.strip() == '0x50000':
            outfeed_camera_throttled[prt] = '--throttled--'
        else:
            # not sure what other values might be here; fix this when I know better
            outfeed_camera_throttled[prt] = ' %s ' % value2

    if 'stacker_throttled' in report_dict:
        value3 = report_dict['stacker_throttled']
        if value3 is None:
            stacker_camera_throttled[prt] = ''
        elif value3.strip() == '0x0':
            stacker_camera_throttled[prt] = ''
        elif value3.strip() == '0x50005':
            stacker_camera_throttled[prt] = '--throttled NOW--'
        elif value3.strip() == '0x50000':
            stacker_camera_throttled[prt] = '--throttled--'
        else:
            # not sure what other values might be here; fix this when I know better
            stacker_camera_throttled[prt] = ' %s ' % value3


    if report_dict.get('hist_stats') is not None:     # Previous days: this is only sent out when the printer starts, so someone manually runs the report    2023.06.21 JU: changed to use get
        hist_stats = report_dict['hist_stats']
        tup_days = hist_stats.split('|')    # day entries separated by '|'
        prt_list = []
        for day in tup_days:
            tup_items = day.split(',')      # for one day, the entries are separated by commas; ex: 'Monday 3/06,12%,45,10:10,14:42,5,0% of 5'
            prt_list.append(tup_items)
        status_list[prt] = prt_list

        filename = "Data/hist_stats_%d" % prt       # save raw data to file in case web server restarts
        with open(filename, 'w') as f:
            f.write(hist_stats)

    """
    Build the output string as list; concat later
    
    Current datetime
    
    Printer #999
    Status		[state][color] as of 12:59
    Page		[page_num] of [max]  xxx%
    Traveler	[build_id]
    Operator	[operator]		# optional
    Note		[note]			# optional
    
    """

    # Rebuild the entire page, for all printers

    # 'normal' page, now includes camera images
    norm_output = [header,
              date_header % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"),
              class_wrap
              ]

    # terse page, no daily stats
    short_output = [header,
                    date_header % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"),
                    class_wrap
                    ]

    # original page, no images
    orig_output = [header,
                   date_header % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"),
                   class_wrap
                   ]


    for i, printer in enumerate(control_list):
        #for i in range(2):
        # details.append("Page %d" % i)
        if printer.isnumeric():
            nice_name = f"Printer #{printer}"
        else:
            nice_name = printer
        section_output = []
        section_output.append(section_start % nice_name)
        http_page = cfg.http_source_report % printer    # 2024.02.08 JU: add link to source code report

        # change the tag text and color if the change report starts w/ the word "CHANGED"
        #if current_source_code_report_header[i].startswith('CHANGED'):
        msg1 = current_source_code_report_header[i]
        if msg1.find('CHANGED') >= 0:
            #print(f'[{cfg.sys_ver}] CHANGED FOUND ~~~~~~~~~~~~~~~~~~, msg = {msg1}')
            #print(f'[DEBUG] CHANGED FOUND ~~~~~~~~~~~~~~~~~~, msg = {msg1}')
            tup = current_source_code_report_header[i].split(' ')
            msg = tup[0]
            # section_output.append(status_tag_changed % (http_page, color[i], state[i], timestamp[i]))   # changed
            section_output.append(status_tag_changed % (http_page, msg, color[i], state[i], timestamp[i]))   # changed
        else:
            section_output.append(status_tag % (http_page, color[i], state[i], timestamp[i]))       # not changed
            #print(f'[{cfg.sys_ver}] CHANGED *NOT* FOUND ~~~~~~~~~~~~~~~~~~, msg = {msg1}')
            #print(f'[DEBUG] CHANGED *NOT* FOUND ~~~~~~~~~~~~~~~~~~, msg = {msg1}')

        if state[i] == 'Paused' and pause_reason[i] is not None:
            section_output.append(p_reason % pause_reason[i])
        # calc percent complete, if appropriate
        try:
            p = int(page_num[i])
            m = int(max_page[i])
            if p > 0 and m > 0:
                complete = "%d%%" % ((p * 100) // m)
            else:
                complete = ""
            section_output.append(page % (page_num[i], max_page[i], complete))
        except:
            section_output.append(page % (page_num[i], 0, ""))

        section_output.append(traveler % build_id[i])
        if operator is not None and operator[i] is not None and len(operator[i]) > 0:
            section_output.append(oper_str % operator[i])
        if note is not None and note[i] is not None and len(note[i]) > 0:
            section_output.append(note_str % note[i])

        if fiber is not None and fiber[i] is not None and len(fiber[i]) > 0:
            section_output.append(fiber_str % fiber[i])

        if sheet_size is not None and sheet_size[i] is not None and len(sheet_size[i]) > 0:
            section_output.append(sheet_size_str % sheet_size[i])

        if polymer is not None and polymer[i] is not None and len(polymer[i]) > 0:
            section_output.append(polymer_str % polymer[i])
        section_output.append('</table>')

        # TODO: change this eventually so a camera_mode of NORMAL is not shown on web page, but all other modes/states are displayed
        # TODO: this is to reduce the amount of screen space taken up by each printer section, so we can eventually have 4 (or 5) displayed.
        section_output.append('<table>')
        if platen_camera_status[i] is not None:
            section_output.append(platen_str % (cfg.platen_image_pages[i], platen_camera_throttled[i], platen_camera_color[i], platen_camera_status[i]))
        if outfeed_camera_status[i] is not None:
            if cfg.outfeed_image_pages[i] is None:
                section_output.append(outfeed_str_0 % (outfeed_camera_throttled[i], outfeed_camera_color[i], outfeed_camera_status[i]))
            else:
                section_output.append(outfeed_str % (cfg.outfeed_image_pages[i], outfeed_camera_throttled[i], outfeed_camera_color[i], outfeed_camera_status[i]))
        if stacker_camera_status[i] is not None:
            section_output.append(stacker_str % (cfg.stacker_image_pages[i], stacker_camera_throttled[i], stacker_camera_color[i], stacker_camera_status[i]))
        section_output.append('</table>')

        section_output.append(section_footer)

        # 2023.03.10 JU
        status_output = []
        display_status(i, status_output)       # reads content from status_list[], today_list[]


        norm_output += section_output
        orig_output += section_output
        short_output += section_output

        norm_output += status_output
        orig_output += status_output
        short_output.append('</section>')

        # image for printer; ONLY USE FOR ONE OF THE PAGES GENERATED
        now = datetime.datetime.now()
        milli_str = now.strftime("%f")
        image_name = cfg.printer_images[i] % milli_str
        just_name = cfg.printer_images[i][0:-3]
        norm_output.append(printer_image % (just_name, image_name))
        norm_output.append('</section>')

        # build copy without images
        orig_output.append('</section>')

        print(f'[DEBUG] Page built: {norm_output}')


    # add linkS at the bottom of the page to switch between formats
    to_terse = f'<p>Terse version of report <a href="{cfg.http_terse}">TERSE</a>.</p>'
    to_verbose = f'<p>Verbose version of report <a href="{cfg.http_verbose}">VERBOSE</a>.</p>'
    to_orig = f'<p>Original version of report <a href="{cfg.http_orig}">VERBOSE</a>.</p>'

    # Normal page, show links to Orig, terse
    norm_output.append(to_terse)
    norm_output.append(to_orig)

    # Terse page, show links to Normal, Orig
    short_output.append(to_verbose)
    short_output.append(to_orig)

    # Orig page, show links to Normal, terse
    orig_output.append(to_verbose)
    orig_output.append(to_terse)

    # Final footer for all pages
    norm_output.append(final_footer)
    short_output.append(final_footer)
    orig_output.append(final_footer)


    # convert lists into strings
    total = ''.join(norm_output)
    short_total = ''.join(short_output)
    orig_total = ''.join(orig_output)


    # save strings for web display
    if cfg.use_rabbitmq:
        write_to_rabbitmq(cfg.base_web_target, total)
        with open(os.path.join('Data', cfg.base_web_target), 'w') as file:  # make a local copy of the file
            file.write(total)

        write_to_rabbitmq(cfg.base_web_target_short, short_total)
        with open(os.path.join('Data', cfg.base_web_target_short), 'w') as file:  # make a local copy of the file
            file.write(short_total)

        write_to_rabbitmq(cfg.base_web_target_orig, orig_total)
        with open(os.path.join('Data', cfg.base_web_target_orig), 'w') as file:  # make a local copy of the file
            file.write(orig_total)

    else:
        f = open(cfg.web_target, 'w')
        f.write(total)                      # <<<< Write updated web page (full) here
        f.close()

        f = open(cfg.web_target_short, 'w')
        f.write(short_total)                # <<<< Write updated web page (terse) here
        f.close()

        f = open(cfg.web_target_orig, 'w')
        f.write(orig_total)                # <<<< Write updated web page (original (no image)) here
        f.close()


    if refresh_pause_page:
        pass    # TODO: update web page showing pause reasons


# ==============================================================================================
def create_source_code_page_new(printer_name, prt):
    # This is the OLD format for the source code change report:
    # Section 1: Source code difference report for printer...
    # Section 2: Changed Individual files
    # Section 3: Current Firmware versions
    # Section 4: <extra blank line; skip>
    # Section 5: Platen Camera source code report...
    # Section 6: Outfeed Camera source code report...
    # Section 7: Stacker Camera source code report
    # append standard ending text here to finish

    section = 1
    sub_section = 0   # 0 = reading section title, 1= section separator(ignore),
        # 2=section content line, read until blank found then incr section
    tup = source_code_report[prt].split('\n')
    lines = []
    lines.append(status_header1)
    lines.append(printer_name)
    lines.append(status_header2)
    if source_code_report[prt].startswith('CHANGED'):
        lines.append("<p>CHANGED1 means printer code in SWZP or its Python libraries has changed")
        lines.append("<p>CHANGED2 means the firmware compile date(s) have changed")
        lines.append("<p>CHANGED3 means the camera code in one or more Raspberry Pi's have changed")
        lines.append("<p>If more than one section changed, the numbers will concantinate, ex. CHANGED123")
    for line in tup:
        if sub_section == 0:
            if len(line) < 5:
                # this is an extra blank line; ignore it
                continue
            if "Reminder:" in line:
                # this starts the final section; just copy data and stop here
                lines.append("<p>Reminder: this report only updates when the printer software restarts. Any source code changes to either the PC or Raspberry Pi code will not be reflected here until the printer next restarts.")
                # lines.append("<p>To return to the previous page use the browser Back button")     # No longer needed because links open in new tabs
                lines.append("</body></html>")
                break
            # reading header line
            lines.append(f"<h2>{line}</h2>")
            if "not available" in line:
                # special case where no text follows this; leave sub_section = 0
                section += 1
                continue
            sub_section += 1
            continue
        if sub_section == 1:
            # skip this line; use it to start table
            lines.append(f'<table class="section-{section}">')
            sub_section += 1
            continue

        # else sub_section == 2
        if len(line) < 5:
            # this line is blank; it separates sections
            lines.append("</table>")
            section += 1
            sub_section = 0
            continue

        # separate content line into 2 or 3 parts separated by ':'
        if section == 3:
            tup = line.split(':', 2)    # only for firmware
        else:
            tup = line.split(':', 1)
        if len(tup) not in [2, 3]:
            # error
            lines.append(f"<p>Error: {line}")
        else:
            tup2 = tup[1].split(',')
            if len(tup2) > 1:
                # make sure comma separated lists include space after the comma
                lines2 = []
                for entry in tup2:
                    lines2.append(entry)
                new_value = ", ".join(lines2)
                lines.append(f"<tr><th>{tup[0]}</th><td>{new_value}</td></tr>")
            else:
                if len(tup) == 3:
                    lines.append(f"<tr><th>{tup[0]}</th><td>{tup[1]}</td><td>{tup[2]}</td></tr>")   # firmware line
                else:
                    lines.append(f"<tr><th>{tup[0]}</th><td>{tup[1]}</td></tr>")


    formatted_lines = "\n".join(lines)

    # 2024.09.25 JU: write the output RabbitMQ, and let the webpub service write it to the /var/www/html directory
    #  This way, ReporterHome doesn't need to run as root.


    if cfg.use_rabbitmq:
        write_to_rabbitmq(f"source_{printer_name}", formatted_lines)
    else:
        # #filename = f"/var/www/html/source_{printer_name}.html"
        filename = cfg.source_report % printer_name
        with open(filename, 'w') as f:
            f.write(formatted_lines)

    current_source_code_report_header[prt] = source_code_report[prt][0:20]      # save start of this file
    source_code_report[prt] = ''        # clear for next time


# ==============================================================================================
def create_source_code_page_new2(printer_name, prt):
    """
    New format for changed report.
    Control line format:
        <tag> \t p \t content_to_display_with_<p>
        <tag> \t h2 \t content_to_display_surrounded_by_<h2>_</h2>
        <tag> \t table      following lines displayed in a table; table lines continue until next <tag>
        Lines in table have fields separated by tab
    """
    in_table = False
    class_section = 0       # used to provide unique section name for table class

    tup = source_code_report2[prt].split('\n')
    assert status_header1 is not None
    assert printer_name is not None
    assert status_header2 is not None
    lines = [status_header1, printer_name, status_header2]      # html output built here
    #if source_code_report2[prt].startswith('<tag>\th2\tCHANGED'):
    if tup[0].find('CHANGED') >= 0:
        lines.append("<p>CHANGED1 means printer code in SWZP or its Python libraries has changed")
        lines.append("<p>CHANGED2 means the firmware compile date(s) have changed")
        lines.append("<p>CHANGED3 means the camera code in one or more Raspberry Pi's have changed")
        lines.append("<p>If more than one section changed, the numbers will concantinate, ex. CHANGED123")

    for line in tup:
        parts = line.split('\t')  # split line by tabs, for use later
        if in_table:
            # see if end of table
            if line.startswith('<tag>'):
                in_table = False
                lines.append("</table>")
                # let the remaining code handle this new line below

            else:
                # this is a line for the table; use the line split up by tabs and place in table
                one_line = ["<tr>"]
                for part in parts:
                    one_line.append(f"<td>{part}</td>")
                one_line.append(f"</tr>")
                join1 = "".join(one_line)
                assert join1 is not None
                lines.append(join1)
                continue

        # line really should start with '<tag>\t'; see which command it is
        if line.startswith('<tag>\ttable'):
            in_table = True
            class_section += 1
            lines.append(f'<table class="section-{class_section}">')
            continue
        if line.startswith('<tag>\th2'):
            # this is a header line; there should only be 1 section after the 'h2\t' part
            msg = str(parts[2:])
            if msg.startswith("['"):
                msg = msg[2:]
            if msg.endswith("']"):
                msg = msg[:-2]
            # print(f'[{cfg.sys_ver}] Header2 content: {msg}  ===================== Line:  {parts}')
            lines.append(f"<h2>{msg}</h2>")     # clean up extra characters around header info (why?)
            continue
        # todo: add support for other headers here?

        if line.startswith('<tag>\tp'):
            lines.append(f"<p>{parts[2:]}</p>")
            continue

        # not sure how to handle this
        lines.append(lines.append(f"<p>Problem: {line}</p>"))

    """
    Idea: to avoid needing to have root privileges, I could write this to a queue and have another server
    running under root that reads from the queue and writes to the html directory. This way the web page
    logic could run under my (or someone's) personal account; it would help with debugging.
    """

    for ck in lines:
        if ck is None:
            print("Found problem line")

    formatted_lines = "\n".join(lines)

    if cfg.use_rabbitmq:
        write_to_rabbitmq(f"source_{printer_name}.html", formatted_lines)
    else:
        # filename = f"/var/www/html/source_{printer_name}.html"
        filename = cfg.source_report % printer_name
        with open(filename, 'w') as f:
            f.write(formatted_lines)

    # TODO: remove/testing
    debug_path = '/home/julowetz/ReporterHomeDev/debug2'
    ts = datetime.datetime.now()
    this_file = os.path.join(debug_path, f"{ts.strftime('%m_%d__%H-%M-%S_%f')}_source_{printer_name}.txt")
    with open(this_file, 'w') as f:
        f.write(formatted_lines)


    temp = source_code_report2[prt][0:20]      # save start of this file
    if temp.startswith('<tag'):
        current_source_code_report_header[prt] = temp.split('\t')[2]    # line starts with
    else:
        current_source_code_report_header[prt] = temp
    source_code_report2[prt] = ''        # clear for next time


# ==============================================================================================
def catchup(filename):
    # reload existing report file so web page shows most recent values
    # 2023.02.15 JU: only load most recent report data to rebuild the web page

    # retrieve most recent history items from cache files
    for i in range(control_list_length):
        filename1 = "Data/today_stats_%d" % i
        if os.path.isfile(filename1):
            print(f"[{cfg.sys_ver}] FOUND FILE: {filename1}")
            with open(filename1) as f:
                today_stats = f.read()      # todo: check to see if needs strip()
                today_list[i] = today_stats.split(',')

        filename2 = "Data/hist_stats_%d" % i
        if os.path.isfile(filename2):
            print(f"[{cfg.sys_ver}] FOUND FILE: {filename2}")
            with open(filename2) as f:
                hist_stats = f.read()
                tup_days = hist_stats.split('|')  # day entries separated by '|'
                prt_list = []
                for day in tup_days:
                    tup_items = day.split(',')
                    prt_list.append(tup_items)
                status_list[i] = prt_list

    # count number of lines in the source data; only care about last few records
    line_count = 0
    try:
        with open(filename, 'r') as fp:
            line_count = len(fp.readlines())

        print("[{cfg.sys_ver}] Loading recent reports to web page...")
        g = open(filename, 'r')
        count = 0
        skip_lines = line_count - 300       # skip all but the last 300 lines TODO: adjust this?
        for line in g:
            count += 1
            if count < skip_lines:
                continue
            res = ast.literal_eval(line)
            receive(res)
        g.close()
        print("[{cfg.sys_ver}] Web page now current")
    except:
        print(f"[{cfg.sys_ver}] No {filename}, run anyway")

    return line_count

def set_camera_color(status):
    # Working, Disabled, Partial, Not active, Not configured
    """
    New status strings that can be received here:
        "Camera is OK",             x # camera_mode = NORMAL
        "Camera is OK",             x # camera_mode = NORMAL   (obsolete)
        "Camera ignores errors",     # camera_mode = REPORT_SUCCESS
        "Camera Image Capture OK",   # camera_mode = IMAGE_ONLY
        "Camera DOWN",              x # camera did not connect when printer started
        "Camera Not Working",       x # camera connected to printer, but later something went wrong and camera disabled itself
        "camera not configured",    x # camera not configured in machine.cfg file
        "Software Error!",           # software error (hasn't happened; checks for certain conditions)
        "in TESTMODE",
        "Camera Started"            x # camera initially connected to printer, but printer has not taken any images yet
    """

    # Reminder: all these color strings must be declared in header html (case-insensitive)
    if 'OVRD' in status:
        return 'Red'
    if 'Disabled' in status or 'Not Working' in status:      # check this before checking 'Working' below
        return 'Violet'
    if 'Hung!' in status or 'hung' in status:      # check this before checking 'Working' below
        return 'orange'
    if 'Image Capture OK' in status:        # check this before checking "OK" below
        return 'Blue'
    if "Not configured" in status or 'not configured' in status or 'Not Configured' in status:
        return 'LightGray'
    if "Working" in status or 'OK' in status or 'Started' in status:
        return 'MediumSeaGreen'
    if "Not active" in status or 'DOWN' in status:
        return 'Tomato'
    if status == "Partial":
        return 'Tomato'
    if 'ignores errors' in status or 'Ignores Errors' in status:
        return 'Yellow'
    else:
        return 'Dodger'



if __name__ == '__main__':
    # data1 = {'state': 'Paused', 'printer': 'SWZP_158', 'timestamp': 1646255536.707}
    # receive(data1)
    set_logger()  # calls to log_event allowed **AFTER** this point
    testfile = "C:/Users/Joe/PycharmProjects/ReporterHome/medium.txt"
    catchup(testfile)
