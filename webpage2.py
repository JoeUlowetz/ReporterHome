# webpage2.py       New version of logic, using "state2" messages
"""
NEW Message format interpretation, uses 'state2' (and 'data2' ??)

'state2' just for printing start and start/stop
'data2' to save data; ['data2'] == 'reset': clear any saved data

['data2'] == 'FIRMWARE_VERSIONS'
['data2'] == 'reset'   -> command to clear saved data

Field needed by web page2:
    state2[prt]
    max_page[prt]
    build_id[prt]
    operator[prt]
    note[prt]
    pause_reason[prt]

Report messages:

Every 'state2' report should include the 'timestamp' field; this is used to populate the "as of 99:99" time field on the status line of the web page
"state2": "Software startup"
"state2": "Printing page: start", "page_num": page_num
"state2": "Printing page: end", "page_num": page_num
"state2": "TEST page: start"
"state2": "Start Print Job", **job_info     includes: 'model_name', 'total_pages', 'machine_configuration', 'configuration'(job), 'operator_name', 'note', 'build_id', 'first_page_num'
"state2": "Pre-print job cmd", "action": start
"state2": "Post-print job cmd", "action": start
"state2": "Cancel Print Job"
"state2": "Paused",
"state2": "Paused", "pause_reason": reason, "page_num": self.next_page_num
"state2": "Resume printing",
"state2": "Print job complete",     cbam_printer_gui.py, stop_print_job(): change this to reflect status_type for stopping
"state2": "Shutdown",

"data2": 'reset'        <-- THIS IS A COMMAND TO ERASE CURRENT SAVED INFO, to prepare for new job
"data2": "FIRMWARE_VERSIONS", "FIRMWARE_VERSIONS": payload
"data2": "set_next_page", "set_next_page": page_num     TODO
'data2': 'camera_status', 'platen': 'Not active', 'outfeed': 'Working', 'stacker': 'Working',

Do not put "data2" and "state2" keys in the same record.

---------------------------------------------------------------------------
timestamp[prt] = format_as_of(['timestamp'])

if field 'model_name' present:          (populated in cbam_printer_gui.py ln 2274-2295)
        (In the future, this will be part of ['state2'] == 'Start Print Job'
    set max_page[prt] = ['total_pages']
    if 'build_id' present:
        set build_id[prt] to ['build_id']
    if 'operator_name' present:
        set operator[prt] = ['operator_name']
    if 'note' present:
        set note[prt] = ['note']

else if 'model_name' not present
    if 'state2' present:
        if ['state2'] != 'Paused'
            pause_reason[prt] = None    #clear this field if not paused

        if ['state2'] == 'Printing page':
            set state2[prt] to 'RUNNING'
            set page_num[prt] to ['page_num']
            set build_id[prt] to ['traveler_num']

        elif ['state2'] == 'Paused':
            set state2[prt] = 'Paused'
            if 'pause_reason' present:
                pause_reason[prt] = ['pause_reason']
            else:
                pause_reason[prt] = None

        elif ['state2']  == 'Software startup':
            set state2[prt] to 'Software startup'
            set max_page[prt] to ''
            set build_id[prt] to ''
            set note[prt] to ''

        elif ['state2'] == 'Start Print Job':
            set state2[prt] to 'Start Print Job'

        elif ['state2'] == 'FIRMWARE_VERSIONS':
            set state2[prt] to 'FIRMWARE_VERSIONS'



"""
import datetime
import ast
import time
from logger import set_logger, log_event


web_target = "/home/pi/ImpossibleObjects/report.html"
problem_pages = "/home/pi/ImpossibleObjects/ReporterHome/problem_pages.txt"

# lists containing attributes for the printers
printer = ['Printer #154', 'Printer #158', 'Joe-printer']
build_id = [0, 0, 0]
operator = ['', '', '']
note = ['', '', '']
page_num = [0, 0, 0]
timestamp = [0, 0, 0]
max_page = [0, 0, 0]
state2 = ['', '', '']
color = ['Gray', 'Gray', 'Gray']    # used for background color of state2 info
pause_reason = [None, None, None]

platen_camera_status = [None, None, None]
outfeed_camera_status = [None, None, None]
stacker_camera_status = [None, None, None]

platen_camera_color = [None, None, None]
outfeed_camera_color = [None, None, None]
stacker_camera_color = [None, None, None]

# constants to build html later
header = '<html lang="en"><body><meta http-equiv="refresh" content="10" >\n'     # Note: this number is auto web page refresh interval
section_header = "<h1>%s</h1>\n"
status = '<table><tr><td>Status</td><td></td><td style="background-color:%s;">%s</td><td></td><td>%s</td></tr>\n'
p_reason = '<tr><td>Pause reason</td><td></td><td style="background-color:Orange;">%s</td><td></td><td></td></tr>\n'
page = '<tr><td>Page</td><td></td><td style="font-weight:bold">%d of %d</td><td></td><td>%s</td></tr>\n'
traveler = '<tr><td>Traveler #</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
oper_str = '<tr><td>Operator</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
note_str = '<tr><td>Note</td><td></td><td style="font-weight:bold">%s</td><td></td><td></td></tr>\n'
section_footer = '</table></br>\n'

platen_str = '<table><tr><td>Platen camera:</td><td></td><td style="background-color:%s;">%s</td><td></td></tr>\n'
outfeed_str = '<table><tr><td>Outfeed camera:</td><td></td><td style="background-color:%s;">%s</td><td></td></tr>\n'
stacker_str = '<table><tr><td>Stacker camera:</td><td></td><td style="background-color:%s;">%s</td><td></td></tr>\n'

final_footer = '</body></html>\n'


# =========================================

def catchup2(filename, test_mode):
    # reload existing report file so web page shows most recent values
    print("Loading previous reports to web page...")
    try:
        g = open(filename, 'r')
        for line in g:
            if len(line) < 5:
                continue        # probably a blank line
            res = ast.literal_eval(line)        # turn the text line back into a dictionary object
            receive2(res, test_mode)
        g.close()
        print("Web page now current")
    except OSError as e:
        print("No previous data to load")


def receive2(report_dict, test_mode):
    # New web page logic; it only uses entries that contain the key "state2" or "data2"
    # Every report entry always has the following keys:
    #   'printer'       Values are: 'SWZP_154', 'SWZP_158', 'Joe-printer'
    #   'timestamp'     raw time seconds
    #   'datetime'      string time in format: "%Y-%m-%d_%H:%M:%S"
    #
    # find 'index' for which printer this info is for:
    # 0 = #154
    # 1 = #158
    # 2 = 'Joe-printer', only show for testing

    log_page_problems(report_dict)

    if 'state2' not in report_dict and 'data2' not in report_dict:
        # log_event("ERROR", "REPORTER", msg="Received message did not contain state2 key", **report_dict)
        # Ignore, this is probably old version during transition period
        return

    # ***********************************************************************************************
    # ** This section decodes the report record and updates the fields for the appropriate printer **
    # ***********************************************************************************************
    if 'printer' in report_dict:
        # 2022.05.20 JU: fixed so either format of printer name will work
        if report_dict['printer'] in ['154', 'SWZP_154']:
            prt = 0
        elif report_dict['printer'] in ['158', 'SWZP_158']:
            prt = 1
        else:
            prt = 2
    else:
        log_event("ERROR", "REPORTER", msg="Received message did not specify printer", **report_dict)
        return

    if 'timestamp' in report_dict:
        ts = float(report_dict['timestamp'])
        timestamp[prt] = format_as_of(ts)

    # TODO: CHANGE THIS TO 'data2' logic
    if 'data2' in report_dict:
        data2 = report_dict['data2']
        if data2 == 'reset':
            # clear all the variables for this printer
            state2[prt] = ''
            operator[prt] = ''
            build_id[prt] = ''
            note[prt] = ''
            max_page[prt] = ''
            page_num[prt] = ''
            pause_reason[prt] = ''

        elif data2 == 'FIRMWARE_VERSIONS':
            pass    # TODO

        elif data2 == 'camera_status':
            platen = report_dict['platen']
            platen_camera_status[prt] = platen
            platen_camera_color[prt] = set_camera_color(platen)

            outfeed = report_dict['outfeed']
            outfeed_camera_status[prt] = outfeed
            outfeed_camera_color[prt] = set_camera_color(outfeed)

            stacker = report_dict['stacker']
            stacker_camera_status[prt] = stacker
            stacker_camera_color[prt] = set_camera_color(stacker)


        # TODO: else: others...

    if 'state2' in report_dict:
        if report_dict['state2'] != 'Paused':
            pause_reason[prt] = None  # make sure this gets erased for any other state2

        if "Printing page: start" in report_dict:
            page_num[prt] = report_dict['page_num']
            # TODO: more

        elif "Printing page: end" in report_dict:
            page_num[prt] = report_dict['page_num']
            # TODO: more

        elif "TEST page: start" in report_dict:
            pass    # TODO: more

        elif "Start Print Job" in report_dict:
            # 'model_name',
            max_page[prt] = report_dict['total_pages']
            #'machine_configuration',
            # 'configuration'(job),
            operator[prt] = report_dict['operator_name']
            note[prt] = report_dict['note']
            build_id[prt] = report_dict['build_id']
            # 'first_page_num'
            # other fields from **job_info also available if desired

        elif "Pre-print job cmd" in report_dict:
            pass    # TODO: more
            # "action": start

        elif "Post-print job cmd" in report_dict:
            pass    # TODO: more
            # "action": start

        elif "Cancel Print Job" in report_dict:
            pass    # TODO: more

        elif "Paused" in report_dict:
            if "pause_reason" in report_dict:
                pause_reason[prt] = report_dict["pause_reason"]
            pass    # TODO: more
            # "page_num": self.next_page_num

        elif "Resume printing" in report_dict:
            pass    # TODO: more

        elif "Software startup" in report_dict:
            pass    # TODO: more

        """
        "Print job complete",     cbam_printer_gui.py, stop_print_job(): change this to reflect status_type for stopping
        "Shutdown",

        """

        # **** OLD CODE BELOW ******************************
        if report_dict['state2'] == 'Printing page':
            state2[prt] = 'RUNNING'
            color[prt] = 'DodgerBlue'
            page_num[prt] = int(report_dict['page_num'])
            build_id[prt] = report_dict['traveler_num']  # yes, traveler_num is the same as build_id in other message
        elif report_dict['state2'] == 'Paused':
            state2[prt] = 'Paused'
            color[prt] = 'Orange'
            # maybe also show pause reason (if provided)
            if 'pause_reason' in report_dict:
                if len(report_dict['pause_reason']) > 0:
                    pause_reason[prt] = report_dict['pause_reason']
                else:
                    pause_reason[prt] = None
            else:
                pause_reason[prt] = None
        elif report_dict['state2'] == 'Software startup':
            state2[prt] = 'Software startup'
            color[prt] = 'LightGray'
            operator[prt] = ''  # erase old values if starting again
            note[prt] = ''
            max_page[prt] = ''
            build_id[prt] = ''
        elif report_dict['state2'] == 'Start Print Job':
            state2[prt] = 'Start Print Job'
            color[prt] = 'Violet'
        elif report_dict['state2'] == 'Resume printing':
            state2[prt] = 'Resume printing'
            color[prt] = 'DodgerBlue'
        elif report_dict['state2'] == 'Shutdown':
            state2[prt] = 'Shutdown'
            color[prt] = 'Tomato'
        elif report_dict['state2'] == 'Cancel Print Job':
            state2[prt] = 'Cancelled Job'
            color[prt] = 'Tomato'
        elif report_dict['state2'] == 'Print job complete':
            state2[prt] = 'Finished!'
            color[prt] = 'MediumSeaGreen'
        else:
            state2[prt] = report_dict['state2']  # ???
            color[prt] = 'Gray'

    """
    Build the output string as list; concat later

    Current datetime

x2:	Printer #999
    Status		[state2][color] as of 12:59
    Page		[page_num] of [max]  xxx%
    Traveler	[build_id]
    Operator	[operator]		# optional
    Note		[note]			# optional

    """
    # if prt > 1:
    #    return		# don't bother updating if this is not one of the 2 main printers

    # Rebuild the entire page, for both printers or only one, depending on testmode
    if test_mode:
        printers = [2, ]     # Joe-printer
    else:
        printers = [0, 1]   # 154 & 158

    output = [header, "<h2>%s</h2>\n" % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S")]
    for i in printers:
        output.append(section_header % printer[i])
        output.append(status % (color[i], state2[i], timestamp[i]))
        if state2[i] == 'Paused' and pause_reason[i] is not None:
            output.append(p_reason % pause_reason[i])
        # calc percent complete, if appropriate
        try:
            p = int(page_num[i])
            m = int(max_page[i])
            if p > 0 and m > 0:
                complete = "%d%%" % ((p * 100) // m)
            else:
                complete = ""
            output.append(page % (page_num[i], max_page[i], complete))
        except:
            output.append(page % (page_num[i], 0, ""))

        output.append(traveler % build_id[i])
        if len(operator[i]) > 0:
            output.append(oper_str % operator[i])
        if len(note[i]) > 0:
            output.append(note_str % note[i])

        if platen_camera_status[i] is not None:
            line = platen_str % (platen_camera_color[i], platen_camera_status[i])
            output.append(line)
        if outfeed_camera_status[i] is not None:
            output.append(outfeed_str % (outfeed_camera_color[i], outfeed_camera_status[i]))
        if stacker_camera_status[i] is not None:
            output.append(stacker_str % (stacker_camera_color[i], stacker_camera_status[i]))

        output.append(section_footer)
    output.append(final_footer)

    total = ''.join(output)
    f = open(web_target, 'w')
    f.write(total)
    f.close()


# ======== Helper Functions =============================================================
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


def log_page_problems(report_dict):
    if 'pause_reason' in report_dict or 'Set_next_page_to_print' in report_dict:
        f = open(problem_pages, 'a')
        #now = datetime.datetime.now()
        ts = datetime.datetime.fromtimestamp(report_dict['timestamp'])
        tag = ts.strftime("%Y-%m-%d %H:%M:%S")
        f.write("%s - %s\n" % (tag, str(report_dict)))
        f.close()


def set_camera_color(status):
    # Working, Disabled, Partial, Not active, Not configured
    if status == "Not configured":
        return 'LightGray'
    if status == "Working":
        return 'MediumSeaGreen'
    if status == "Not active":
        return 'Tomato'
    if status == "Partial":
        return 'Tomato'
    if status == 'Disabled':
        return 'Violet'
    else:
        return 'DodgerBlue'


if __name__ == '__main__':
    # data1 = {'state2': 'Paused', 'printer': 'SWZP_158', 'timestamp': 1646255536.707}
    # receive(data1)
    set_logger()  # calls to log_event allowed **AFTER** this point
    testfile = "C:/Users/Joe/PycharmProjects/ReporterHome/medium.txt"
    catchup2(testfile)
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



