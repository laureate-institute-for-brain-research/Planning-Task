
import StimToolLib, os, random, operator, shutil
from psychopy import visual, core, event, data, gui

#data mover: move files generated during a session.  This way they can be generated locally (more reliable) and then copied onto network storage.

class GlobalVars:
    #This class will contain all module specific global variables
    #This way, all of the variables that need to be accessed in several functions don't need to be passed in as parameters
    #It also avoids needing to declare every global variable global at the beginning of every function that wants to use it
    def __init__(self):
        self.win = None #the window where everything is drawn
        self.output = None

event_types = {'RESPONSE':1, 
    'TASK_END':StimToolLib.TASK_END}
    
def error_try_again(txt):
    error_msg = gui.Dlg(title="ERROR")
    error_msg.addText(txt)
    error_msg.addField('Try again?', choices=['yes', 'no'], initial='yes')
    error_msg.show()
    thisInfo = error_msg.data
    if thisInfo[0] == 'yes':
        return True
    return False
    
def move_one(source, destination):
    #move all files in a source folder to a destination folder
    if not os.path.exists(destination):
        while True:
            try:
                os.makedirs(destination)
                break
            except:
                if not error_try_again('Had trouble making destination: ' + destination + ' Check network connectivity and permissions.'):
                    return
    if source == 'output_dir':
        source = g.session_params['output_dir']
    while True:
        try:
            all_files = os.listdir(source)
            break
        except:
            if not error_try_again('Had trouble finding ' + source + ' Check network connectivity and that the files/folders exist.'):
                return
    for f in all_files:
        full_path = os.path.join(source, f)
        while True:
            #keep retrying individual files if they fail--unless the user decides not to
            try:
                shutil.move(full_path, destination)
                break
            except:
                if not error_try_again('Had trouble moving ' + source + ' to ' + destination + '. Check network connectivity and that the files/folders exist.'):
                    break
    
    
def run(session_params, run_params):
    global g
    g = GlobalVars()
    g.session_params = session_params
    g.run_params = StimToolLib.get_var_dict_from_file(os.path.dirname(__file__) + '/DM.Default.params', {})
    g.run_params.update(run_params)
    try:
        run_try()
        g.status = 0
    except StimToolLib.QuitException as q:
        g.status = -1
    except Exception as e:
        StimToolLib.error_popup('UNKNOWN ERROR MOVING FILES: ' + e + '\nMake sure the data files for this session get moved to the appropriate location')
    StimToolLib.task_end(g)
    return g.status
        
def run_try():  
    pass
    myDlg = gui.Dlg(title="Data Mover")
    #question_lists = [f for f in os.listdir(os.path.join(os.path.dirname(__file__))) if f.endswith('.schedule')] 
    schedules = [f for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.schedule')]
    if not g.session_params['auto_advance']:
        myDlg.addField('Movement Params', choices=schedules, initial=g.run_params['run'])
        myDlg.show()  # show dialog and wait for OK or Cancel
        if myDlg.OK:  # then the user pressed OK
            thisInfo = myDlg.data
        else:
            #print 'QUIT!'
            return -1#the user hit cancel so exit 
        g.run_params['run'] = thisInfo[0]
    schedule_file = os.path.join(os.path.dirname(__file__), g.run_params['run'])
    #StimToolLib.general_setup(g)
    g.clock = core.Clock()
    start_time = data.getDateStr()
    
    param_file = g.run_params['run'][0:-9] + '.params' #every .schedule file can (probably should) have a .params file associated with it to specify running parameters (including part of the output filename)
    StimToolLib.get_var_dict_from_file(os.path.join(os.path.dirname(__file__), param_file), g.run_params)
    #g.prefix = StimToolLib.generate_prefix(g)
    #fileName = os.path.join(g.prefix + '.csv')
    
    #g.prefix = 'R-' + g.session_params['SID'] + '-Admin_' + str(g.session_params['raID']) + '-run_1' + '-' +  start_time 
    #fileName = os.path.join(os.path.dirname(__file__), 'data/' + g.prefix +  '.csv')
    #g.output= open(fileName, 'w')
    sorted_events = sorted(event_types.iteritems(), key=operator.itemgetter(1))
    #g.output.write('Original File Name:,' + fileName + ',Time:,' + start_time + ',Parameter File:,' +  schedule_file + ",Event Codes:," + str(sorted_events) + '\n')
    #g.output.write('trial_number,trial_type,event_code,absolute_time,response_time,response,result\n')
    #StimToolLib.task_start(StimToolLib.DATA_MOVER_CODE, g) #send message that this task is starting
    
    instruct_onset = g.clock.getTime()
    
    input_file = open(schedule_file, 'r')
    g.trial = 0
    for line in input_file.readlines()[1:]: #discard the header
        l = line.split()
        q_start = g.clock.getTime()
        move_one(l[0], os.path.join(l[1], start_time))
        now = g.clock.getTime()
        g.trial = g.trial + 1
        
    
    
    
    

  
 


