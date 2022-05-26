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
import datetime
import ast
import time
from logger import set_logger
import os

# web_target = "C:/temp/test.html"
# import dateutil.rrule

web_target = "/home/pi/ImpossibleObjects/report.html"
test_web_target = "/home/pi/ImpossibleObjects/test.html"
detail_target_base = "/home/pi/ImpossibleObjects/ReporterHome/details"

problem_pages = "/home/pi/ImpossibleObjects/ReporterHome/problem_pages.txt"

# lists containing attributes for the printers
printer = ['Printer #154', 'Printer #158', 'Test Printer']
build_id = [0, 0, 0]
operator = ['', '', '']
note = ['', '', '']
page_num = [0, 0, 0]
timestamp = [0, 0, 0]
max_page = [0, 0, 0]
state = ['', '', '']
color = ['Gray', 'Gray', 'Gray']    # used for background color of state info
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

detail_index = 0


def timestamper():
    nowt = datetime.datetime.now()
    return nowt.strftime("%H:%M:%S ")


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
    # Note: "problem_pages.txt" is to record when the printer was paused, or when "set page number" is used
    if 'pause_reason' in report_dict or 'Set_next_page_to_print' in report_dict:
        f = open(problem_pages, 'a')
        #now = datetime.datetime.now()
        ts = datetime.datetime.fromtimestamp(report_dict['timestamp'])
        tag = ts.strftime("%Y-%m-%d %H:%M:%S")
        f.write("%s - %s\n" % (tag, str(report_dict)))
        f.close()


def receive(report_dict):
    # every report entry has 'printer' or 'printer_name' in it
    # find 'index' for which printer this info is for:
    # 0 = #154
    # 1 = #158
    # 2 = ignore this
    print("--receive--")
    details = []
    details.append("%s : receive ----------" % timestamper())
    log_page_problems(report_dict)
    if 'printer_name' in report_dict:
        printer_name = report_dict['printer_name']
        if printer_name == '154':
            prt = 0
            details.append("0: printer_name == 154")
        elif printer_name == '158':
            prt = 1
            details.append("1: printer_name == 158")
        else:
            prt = 2		# ignore for now
            details.append("2: printer_name == something else: %s" % printer_name)

    else:
        # 2022.05.20 JU: fixed so either format of printer name will work
        printer_name = report_dict['printer']
        if report_dict['printer'] in ['154', 'SWZP_154']:
            prt = 0
            details.append("0: printer == %s" % printer_name)
        elif report_dict['printer'] in ['158', 'SWZP_158']:
            prt = 1
            details.append("1: printer == %s" % printer_name)
        else:
            prt = 2
            details.append("2: printer == %s" % printer_name)

    details.append("Printer index = %d" % prt)
    # All the remaining fields get parsed/used by the one particular printer this message is for
    if 'timestamp' in report_dict:
        ts = float(report_dict['timestamp'])
        timestamp[prt] = format_as_of(ts)
        details.append("timestamp is present")

    if 'model_name' in report_dict:
        # clear current values and load new ones:
        details.append("model_name is present")
        if 'build_id' in report_dict:
            build_id[prt] = report_dict['build_id'] 		# from 'build_id'
            details.append("build_id is present")
        if 'operator_name' in report_dict:
            operator[prt] = report_dict['operator_name']		# from 'operator_name'
            details.append("operator_name is present")
        if 'note' in report_dict:
            note[prt] = report_dict['note']			# from 'note'
            details.append("note is present")
        max_page[prt] = int(report_dict['total_pages'])
        details.append("max_page = %d" % max_page[prt])

    elif 'state' in report_dict:
        details.append("state is present")
        if report_dict['state'] != 'Paused':
            pause_reason[prt] = None        # make sure this gets erased for any other state
        if report_dict['state'] == 'Printing page':
            state[prt] = 'RUNNING'
            color[prt] = 'DodgerBlue'
            page_num[prt] = int(report_dict['page_num'])
            build_id[prt] = report_dict['traveler_num']		# yes, traveler_num is the same as build_id in other message
            details.append("state == Printing page")
        elif report_dict['state'] == 'Paused':
            state[prt] = 'Paused'
            color[prt] = 'Orange'
            details.append("state == Paused")
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
            details.append("state == Software startup")
        elif report_dict['state'] == 'Start Print Job':
            state[prt] = 'Start Print Job'
            color[prt] = 'Violet'
            details.append("state == Start Print Job")
        elif report_dict['state'] == 'Resume printing':
            state[prt] = 'Resume printing'
            color[prt] = 'DodgerBlue'
            details.append("state == Resume printing")
        elif report_dict['state'] == 'Shutdown':
            state[prt] = 'Shutdown'
            color[prt] = 'Tomato'
            details.append("state == Shutdown")
        elif report_dict['state'] == 'Cancel Print Job':
            state[prt] = 'Cancelled Job'
            color[prt] = 'Tomato'
            details.append("state == Cancel Print Job")
        elif report_dict['state'] == 'Print job complete':
            state[prt] = 'Finished!'
            color[prt] = 'MediumSeaGreen'
            details.append("state == Print job complete")
        else:
            state[prt] = report_dict['state']   # includes 'FIRMWARE_VERSIONS'
            color[prt] = 'Gray'
            details.append("state is other: %s" % state[prt])

    if 'data2' in report_dict:
        data2 = report_dict['data2']
        details.append("data2 is present: %s" % data2)
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
            details.append("Platen = %s, Outfeed = %s, Stacker = %s" % (platen, outfeed, stacker))
    """
    Build the output string as list; concat later
    
    Current datetime
    
x2:	Printer #999
    Status		[state][color] as of 12:59
    Page		[page_num] of [max]  xxx%
    Traveler	[build_id]
    Operator	[operator]		# optional
    Note		[note]			# optional
    
    """
    # if prt > 1:
    #    return		# don't bother updating if this is not one of the 2 main printers

    # Rebuild the entire page, for both printers
    details.append("--> Generating HTML")
    output = []
    output.append(header)
    output.append("<h2>%s</h2>\n" % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"))
    for i in range(2):
        details.append("Page %d" % i)
        output.append(section_header % printer[i])
        output.append(status % (color[i], state[i], timestamp[i]))
        if state[i] == 'Paused' and pause_reason[i] is not None:
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

    total2 = '\n'.join(output)
    details.append("--> Result HTML:")
    details.append(total2)
    detail = '\n'.join(details)

    global detail_index
    detail_filename = "details_%02d.txt" % detail_index
    full_filename = os.path.join(detail_target_base, detail_filename)
    print(full_filename)
    f = open(full_filename, 'w')
    f.write(detail)
    f.close()
    detail_index += 1
    detail_index = detail_index % 100       # keep last 100 details


def catchup(filename):
    # reload existing report file so web page shows most recent values
    print("Loading previous reports to web page...")
    g = open(filename, 'r')
    for line in g:
        res = ast.literal_eval(line)
        receive(res)
    g.close()
    print("Web page now current")


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
