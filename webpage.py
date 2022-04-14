import datetime
import ast
import time

# web_target = "C:/temp/test.html"
import dateutil.rrule

web_target = "/home/pi/ImpossibleObjects/report.html"
test_web_target = "/home/pi/ImpossibleObjects/test.html"

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
final_footer = '</body></html>\n'


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


def receive(report_dict):
    # every report entry has 'printer' or 'printer_name' in it
    # find 'index' for which printer this info is for:
    # 0 = #154
    # 1 = #158
    # 2 = ignore this
    log_page_problems(report_dict)
    if 'printer_name' in report_dict:
        if report_dict['printer_name'] == '154':
            prt = 0
        elif report_dict['printer_name'] == '158':
            prt = 1
        else:
            prt = 2		# ignore for now
    else:
        if report_dict['printer'] == 'SWZP_154':
            prt = 0
        elif report_dict['printer'] == 'SWZP_158':
            prt = 1
        else:
            prt = 2

    # All the remaining fields get parsed/used by the one particular printer this message is for
    if 'timestamp' in report_dict:
        ts = float(report_dict['timestamp'])
        # timestamp[prt] = time.strftime("as of %H:%M", time.localtime(ts))
        timestamp[prt] = format_as_of(ts)
    if 'model_name' in report_dict:
        # clear current values and load new ones:
        if 'build_id' in report_dict:
            build_id[prt] = report_dict['build_id'] 		# from 'build_id'
        if 'operator_name' in report_dict:
            operator[prt] = report_dict['operator_name']		# from 'operator_name'
        if 'note' in report_dict:
            note[prt] = report_dict['note']			# from 'note'
        max_page[prt] = int(report_dict['total_pages'])

    elif 'state' in report_dict:
        if report_dict['state'] != 'Paused':
            pause_reason[prt] = None        # make sure this gets erased for any other state
        if report_dict['state'] == 'Printing page':
            state[prt] = 'RUNNING'
            color[prt] = 'DodgerBlue'
            page_num[prt] = int(report_dict['page_num'])
            build_id[prt] = report_dict['traveler_num']		# yes, traveler_num is the same as build_id in other message
        elif report_dict['state'] == 'Paused':
            state[prt] = 'Paused'
            color[prt] = 'Orange'
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
        elif report_dict['state'] == 'Start Print Job':
            state[prt] = 'Start Print Job'
            color[prt] = 'Violet'
        elif report_dict['state'] == 'Resume printing':
            state[prt] = 'Resume printing'
            color[prt] = 'DodgerBlue'
        elif report_dict['state'] == 'Shutdown':
            state[prt] = 'Shutdown'
            color[prt] = 'Tomato'
        elif report_dict['state'] == 'Cancel Print Job':
            state[prt] = 'Cancelled Job'
            color[prt] = 'Tomato'
        elif report_dict['state'] == 'Print job complete':
            state[prt] = 'Finished!'
            color[prt] = 'MediumSeaGreen'
        else:
            state[prt] = report_dict['state']   # ???
            color[prt] = 'Gray'

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
    output = []
    output.append(header)
    output.append("<h2>%s</h2>\n" % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"))
    for i in range(2):
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
        output.append(section_footer)
    output.append(final_footer)

    total = ''.join(output)
    f = open(web_target, 'w')
    f.write(total)
    f.close()

    # make a special test page for 'other' printer
    i = 2
    output = []
    output.append(header)
    output.append("<h2>%s</h2>\n" % datetime.datetime.now().strftime("%Y-%m-%d -- %H:%M:%S"))
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
    output.append(section_footer)
    output.append(final_footer)

    total = ''.join(output)
    f = open(test_web_target, 'w')
    f.write(total)
    f.close()


def catchup(filename):
    # reload existing report file so web page shows most recent values
    print("Loading previous reports to web page...")
    g = open(filename,'r')
    for line in g:
        res = ast.literal_eval(line)
        receive(res)
    g.close()
    print("Web page now current")


if __name__ == '__main__':
    # data1 = {'state': 'Paused', 'printer': 'SWZP_158', 'timestamp': 1646255536.707}
    # receive(data1)
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



