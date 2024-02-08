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
from copy import deepcopy

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

web_target = cfg.web_target                     # "/var/www/html/report.html"
web_target_short = cfg.web_target_short        # "/var/www/html/report_short.html"
# test_web_target = cfg.test_web_target           # "/home/julowetz/ReporterHome/Data/test.html"
detail_target_base = cfg.detail_target_base     # "/home/julowetz/ReporterHome/details"     DEPRECATED
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

# 2024.02.08 JU: add source code report page storage
source_code_report = [''] * control_list_length

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
# status = '<table><tr><td>Status</td><td style="background-color:%s;">%s</td><td></td><td>%s</td></tr>\n'
status = """<tr>
    <td><a href="%s" style="color:#ffffff;">Status:</a></td>
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

# 2023.10.27 JU: add additional parameter to show throttled status, if any
# *SECTION, PART-4*  wrap w/ <table>...</table>
platen_str = """<tr><td>Platen Camera:%s</td><td class="%s">%s</td></tr>\n"""

outfeed_str = """<tr><td>Outfeed Camera:%s</td><td class="%s">%s</td></tr>\n"""

stacker_str = """<tr><td>Stacker Camera:%s</td><td class="%s">%s</td></tr>\n"""

# *SECTION, PART-5*
dev_end = '</dev>\n'

# *SECTION, PART-6*     handled in display_status()


final_footer = '</body></html>\n'

detail_index = 0


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
        report_dict['printer']      this will be 153, 154, 158, etc; identify the printer it is for

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
        print("BUG in count_pause_reason")
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
        print(f"JOE number of history entries: {cnt}")
        for day_item in day_list:
            # first field is the date; it might be in yyyy-mm-dd format, or Weekday mm/dd format
            if type(day_item) is not list:
                print("---not a list--")
                continue
            if len(day_item) < 7:
                print("---too few items--")
                continue

            the_date = day_item[0]
            if len(the_date) < 2:
                print("---invalid date--")
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


def receive(report_dict):
    # every report entry has 'printer' or 'printer_name' in it
    # find 'index' for which printer this info is for:
    # 0 = #154
    # 1 = #158
    # 2 = ignore this
    start_time = time.time()
    print("--receive--")
    # details = []
    # details.append("%s : receive ----------" % timestamper())
    # log_page_problems(report_dict)    # obsolete
    refresh_pause_page = count_pause_reasons(report_dict)

    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    print(report_dict)

    # 2022.05.20 JU: fixed so either format of printer name will work
    # 2023.03.07 JU: changed again so driven by control_list variable defined at head of this file
    printer_name = report_dict['printer']

    if printer_name not in control_list:
        print(f"!!! Received printer name not in control_list:  {printer_name}")
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

        create_source_code_page(printer_name, prt)      # this clears source_code_report[prt] when done


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
        print(f"JOE  today_stats found")
        today_stats = report_dict['today_stats']        # example:   '12%,45,10:10,14:42'
        print(f"JOE  today_stats contents: {today_stats}")
        tup = today_stats.split(',')        # [0] = 'Today so far', [1] = active%, [2] = pages, [3] = start_time, [4] = end_time, [5] = restarts, [6] = unattended
        if tup is not None and len(tup) == 7:
            today_list[prt] = tup
        else:
            print(f"JOE  did not save to today_list:  {tup}")
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
    # details.append("--> Generating HTML")
    output = []
    output.append(header)
    output.append(date_header % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"))
    output.append(class_wrap)

    short_output = []
    short_output.append(header)
    short_output.append(date_header % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"))
    short_output.append(class_wrap)

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
        section_output.append(status % (http_page, color[i], state[i], timestamp[i]))
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
            section_output.append(platen_str % (platen_camera_throttled[i], platen_camera_color[i], platen_camera_status[i]))
        if outfeed_camera_status[i] is not None:
            section_output.append(outfeed_str % (outfeed_camera_throttled[i], outfeed_camera_color[i], outfeed_camera_status[i]))
        if stacker_camera_status[i] is not None:
            section_output.append(stacker_str % (stacker_camera_throttled[i], stacker_camera_color[i], stacker_camera_status[i]))
        section_output.append('</table>')

        section_output.append(section_footer)

        # 2023.03.10 JU
        status_output = []
        display_status(i, status_output)       # reads content from status_list[], today_list[]

        output += section_output
        output += status_output
        output.append('</section>')

        # build copy without status_output
        short_output += section_output
        short_output.append('</section>')


    # add link at the bottom of the page to switch between formats
    to_terse = f'<p>Terse version of report <a href="{cfg.http_terse}">TERSE</a>.</p>'
    to_verbose = f'<p>Verbose version of report <a href="{cfg.http_verbose}">VERBOSE</a>.</p>'

    # duration = time.time() - start_time
    # output.append(final_footer % duration)
    output.append(to_terse)
    output.append(final_footer)
    short_output.append(to_verbose)
    short_output.append(final_footer)

    total = ''.join(output)
    f = open(web_target, 'w')
    f.write(total)                      # <<<< Write updated web page (full) here
    f.close()

    short_total = ''.join(short_output)
    f = open(web_target_short, 'w')
    f.write(short_total)                # <<<< Write updated web page (terse) here
    f.close()

    if refresh_pause_page:
        pass    # TODO: update web page showing pause reasons

        # temp code  DOESN'T WORK FOR SOME REASON:
        """
        
        ----------------------------------------
        Exception happened during processing of request from ('10.1.10.110', 59982)
        Traceback (most recent call last):
          File "/usr/lib64/python3.6/socketserver.py", line 320, in _handle_request_noblock
            self.process_request(request, client_address)
          File "/usr/lib64/python3.6/socketserver.py", line 351, in process_request
            self.finish_request(request, client_address)
          File "/usr/lib64/python3.6/socketserver.py", line 364, in finish_request
            self.RequestHandlerClass(request, client_address, self)
          File "/usr/lib64/python3.6/socketserver.py", line 724, in __init__
            self.handle()
          File "ReporterHome.py", line 157, in handle
            webpage.receive(input_data_dict)    # <<<<<<<<<<< This is where OLD web page gets updated
          File "/home/julowetz/ReporterHomeDev/webpage.py", line 793, in receive
            for key, value in today_pause_lists[index]:
        ValueError: too many values to unpack (expected 2)
        ----------------------------------------



        with open('pause_reasons.txt', 'w') as f:
            for index in range(control_list_length):
                printer = control_list[index]
                f.write(f"\nPrinter #{printer}\n")
                if today_pause_lists[index] is not None:
                    if type(today_pause_lists[index]) is dict:
                        for key, value in today_pause_lists[index]:
                            f.write('%-10s  %d' % (key, value))
                    else:
                        f.write('Type of list: %s' % str(type(today_pause_lists[index])))
                else:
                    f.write('No entries for this printer')
        """


# ==============================================================================================
def create_source_code_page(printer_name, prt):
    pass
    # stuff happens here
    tup = source_code_report[prt].split('\n')
    lines = [f"<title>{printer_name} source report</title><head></head><body>", ]
    for line in tup:
        lines.append(f"{line}<br>")
    lines.append("</body>")

    formatted_lines = "\n".join(lines)
    filename = f"/var/www/html/source_{printer_name}.html"
    with open(filename, 'w') as f:
        f.write(formatted_lines)


    source_code_report[prt] = ''        # clear for next time



# ==============================================================================================
def catchup(filename):
    # reload existing report file so web page shows most recent values
    # 2023.02.15 JU: only load most recent report data to rebuild the web page

    # retrieve most recent history items from cache files
    for i in range(control_list_length):
        filename1 = "Data/today_stats_%d" % i
        if os.path.isfile(filename1):
            print(f"FOUND FILE: {filename1}")
            with open(filename1) as f:
                today_stats = f.read()      # todo: check to see if needs strip()
                today_list[i] = today_stats.split(',')

        filename2 = "Data/hist_stats_%d" % i
        if os.path.isfile(filename2):
            print(f"FOUND FILE: {filename2}")
            with open(filename2) as f:
                hist_stats = f.read()
                tup_days = hist_stats.split('|')  # day entries separated by '|'
                prt_list = []
                for day in tup_days:
                    tup_items = day.split(',')
                    prt_list.append(tup_items)
                status_list[i] = prt_list

    # count number of lines in the source data; only care about last few records
    try:
        with open(filename, 'r') as fp:
            line_count = len(fp.readlines())

        print("Loading recent reports to web page...")
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
        print("Web page now current")
    except:
        print(f"No {filename}, run anyway")


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

    # Reminder: all these color strings must be declared in header html (case insensitive)
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
    # g = open(testfile, 'r')
    # i = 0
    # for line in g:
    #     i += 1
    #     res = ast.literal_eval(line)
    #     receive(res)
    #     print(res)
    #     if i % 50 == 0:
    #         time.sleep(3)
    # g.close()
