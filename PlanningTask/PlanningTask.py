
import StimToolLib, os, random, operator
from psychopy import visual, core, event, data, gui, sound
import itertools

# Planning Task
# Markov-Decision Making

class GlobalVars:
    #This class will contain all module specific global variables
    #This way, all of the variables that need to be accessed in several functions don't need to be passed in as parameters
    #It also avoids needing to declare every global variable global at the beginning of every function that wants to use it
    def __init__(self):
        self.win = None #the window where everything is drawn
        self.clock = None #global clock used for timing
        self.x = None #X fixation stimulus
        self.output = None #The output file
        self.msg = None
        self.ideal_trial_start = None #ideal time the current trial started
        self.this_trial_output = '' #will contain the text output to #print for the current trial
        self.trial = None #trial number
        self.trial_type = None #current trial type
        self.offset = 0.008 #8ms offset--request window flip this soon before it needs to happen->should get precise timing this way
        self.break_instructions = ['''You may now take a short break.''']
        self.line_location_range = 24
        self.defaultColor = "#808080" # Default color for the boxes
        self.goalColor = "#FF0000" # Color of the Goal Box during Training
        self.goalTextColor = '#FFFFFF'
        self.targetColor = '#FFFFFF'
        self.targetOutline = '#00FF00'
        self.show_transitions = False
        self.rectangleSize = .15
        self.skipped = False
        self.points = 0
        self.hand = 'right'
        self.errorMax = 1 # Can only make this much error
        #self.line_location_range = 0.7 #amount the lines (vertical and horizontal) can move left/right and up/down

        # Key - Value pair, 
        # Key is the current state, 
        # Value is dictionary corresonding to next state by choosing 'left' or right
        self.states = {
            1 : {
                'left': {
                    'state': 2,
                    'value': 140
                },
                'right': {
                    'state': 4,
                    'value': 20,
                }
            },
            2 : {
                'left': {
                    'state': 3,
                    'value': -20
                },
                'right': {
                    'state': 5,
                    'value': -70
                }
            },
            3 : {
                'left': {
                    'state': 6,
                    'value': -70
                },
                'right': {
                    'state': 4,
                    'value': -20
                }
            },
            4 : {
                'left': {
                    'state': 2,
                    'value': 20
                },
                'right': {
                    'state': 5,
                    'value': -20
                }
            },
            5 : {
                'left': {
                    'state': 1,
                    'value': -70
                },
                'right': {
                    'state': 6,
                    'value': -20
                }
            },
            6 : {
                'left': {
                    'state': 3,
                    'value': 20
                },
                'right': {
                    'state': 1,
                    'value': -20
                }
            }
        }

        self.pathColor = {
            'left': 'blue',
            'right': 'yellow'
        }




event_types = {
    'INSTRUCT_ONSET':1,
    'TASK_ONSET':2,
    'TRIAL_ONSET':3,
    'PLANNING_ONSET':4,
    'RESPONSE_ONSET': 5,
    'ANIMATION_ONSET': 6,
    'FIXATION_ONSET':7, 
    'RESPONSE':8,
    'FEEDBACK' : 9,
    'OUTCOME': 10,
    'BREATHING_LOAD': 11,
    'EXTENDING_TIME': 12,
    'TASK_END':StimToolLib.TASK_END
    }


def show_fixation(trial_start, duration):
    """
    Show Fixation 
    """

    StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['FIXATION_ONSET'], trial_start, 'NA', 'NA', duration, g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
    g.fixation.draw()
    g.win.flip()
    StimToolLib.just_wait(g.clock, trial_start + duration - g.offset) # wait


def getPossilbeTransitions(depth):
    """
    Get the possible transistions
    """
    transitions = []
    stuff = [1, 2]
    for subset in list(itertools.combinations_with_replacement(['left', 'right'], depth) ):
        transitions.append(list(subset))
    return transitions

def getSum(points):
    """
    Return the summ of given an array of integers
    """
    final_point = 0
    for point in points:
        final_point = final_point + point
    return final_point

def getPoints(start_state, transitions):
    """
    Returns the points in each transition
    """
    points = []
    current_state = start_state
    for transition in transitions:
        value_point = g.states[current_state][transition]['value']
        points.append(value_point)
        current_state = g.states[current_state][transition]['state']
    return points

def isOLLTrial(initial_state, depth):
    """
    Returns True if the maximum possible points requires a large loss
    """
    maxPoints = -1000
    isOLL = False
    #largest_loss_possible = getLargestLossPosssible(initial_state, depth)
    for transitions in getPossilbeTransitions(depth):
        points_path = getPoints(initial_state, transitions)
        totalPoints = getSum(points_path)
        # Sum only where exists an LL
        if (totalPoints >= maxPoints): maxPoints = totalPoints

    # maxPoints should now be set 
    # iteate again to see if that max points includes a large loss
    for transitions in getPossilbeTransitions(depth):
        points_path = getPoints(initial_state, transitions)
        totalPoints = getSum(points_path)
        # Sum only where exists an LL
        if (totalPoints == maxPoints) and (-70 in points_path):
            isOLL = True
    return maxPoints, isOLL


def getAversivePruningPoints(initial_state, depth):
    """
    Get 2nd best max points
    Used for OLL trials
    """
    points = []
    for transitions in getPossilbeTransitions(depth):
        points_path = getPoints(initial_state, transitions)
        points.append(getSum(points_path))
    
    # sort unique
    unique_points = list(set(points))
    unique_points.sort(reverse = True)
    #print(unique_points)
    return unique_points[1]


def getOutcome(start_state, depth, transitions):
    """
    Return the outcomes
    1) ONLL Correct         | Optimal sequence where this odes not include large los
    2) OLL Correct          | Optimal sequence where this includes a large loss
    3) Aversive Pruning     | The best sequence that avoids large loss. 
    4) ONLL Error           | subOptimal sequence but includes large loss
    5) OLL Error            | suboptimal sequence that avoicd large loss
    6) Miss: Did not enter enough moves
    """
    if len(transitions) < depth: return 'Miss'

    # 
    #largest_loss_possible = getLargestLossPosssible(start_state, depth)
    #largest_points_possible = getMaxPointsPossible(start_state, depth)

    points_path = getPoints(start_state, transitions)
    points_earned = getSum(points_path)

    
    # Avoid larger loss and got the most opints without LL

    maxPoints, isOLL = isOLLTrial(start_state, depth)
    avPoints = getAversivePruningPoints(start_state, depth)
    
    if isOLL:
        if points_earned == maxPoints: return 'OLL Correct'
        else:
            if points_earned == avPoints:
                return 'Aversive Pruning'
            else:
                return 'OLL Error'
    else:
        if points_earned == maxPoints: return 'ONLL Correct'
        if points_earned != maxPoints: return 'ONLL Error'



def run(session_params, run_params):
    global g
    g = GlobalVars()
    g.session_params = session_params
    g.run_params = StimToolLib.get_var_dict_from_file(os.path.dirname(__file__) + '/PlanningTask.Default.params', {})
    g.run_params.update(run_params)
    
    #print os.path.exists(os.path.dirname(__file__) + '/PlanningTask.Default.params')
    try:
        run_try()
        g.status = 0
    except StimToolLib.QuitException as q:
        g.status = -1
    StimToolLib.task_end(g)
    return g.status
        

def getNextButton(start_state, goal_state):
    """
    Give the start and goal_state
    Return Key Required to get that state, i.e 'left or right
    """

    if g.states[start_state]['left']['state'] == goal_state: return 'left'
    if g.states[start_state]['right']['state'] == goal_state: return 'right'
    
    return None

def resetStates():
    """
    Sets all the states to default
    """
    g.states[1]['stim'].size = [g.rectangleSize,g.rectangleSize]
    g.states[1]['stim'].fillColor=g.defaultColor
    g.states[1]['stim'].lineColor = g.defaultColor
    g.states[1]['stim'].pos = (.2,.3)
    #g.states[1]['stim'].setAutoDraw(True)



    g.states[2]['stim'].size = [g.rectangleSize,g.rectangleSize]
    g.states[2]['stim'].fillColor=g.defaultColor
    g.states[2]['stim'].lineColor = g.defaultColor
    g.states[2]['stim'].pos = (-.2,.3)
    #g.states[2]['stim'].setAutoDraw(True)


    g.states[3]['stim'].size = [g.rectangleSize,g.rectangleSize]
    g.states[3]['stim'].fillColor=g.defaultColor
    g.states[3]['stim'].lineColor = g.defaultColor
    g.states[3]['stim'].pos = (-.4,0)
    #g.states[3]['stim'].setAutoDraw(True)


    g.states[4]['stim'].size = [g.rectangleSize,g.rectangleSize]
    g.states[4]['stim'].fillColor=g.defaultColor
    g.states[4]['stim'].lineColor = g.defaultColor
    g.states[4]['stim'].pos = (-.2,-.4)
    #g.states[4]['stim'].setAutoDraw(True)


    g.states[5]['stim'].size = [g.rectangleSize,g.rectangleSize]
    g.states[5]['stim'].fillColor=g.defaultColor
    g.states[5]['stim'].lineColor = g.defaultColor
    g.states[5]['stim'].pos = (.2,-.4)
    #g.states[5]['stim'].setAutoDraw(True)


    g.states[6]['stim'].size = [g.rectangleSize,g.rectangleSize]
    g.states[6]['stim'].fillColor=g.defaultColor
    g.states[6]['stim'].lineColor = g.defaultColor
    g.states[6]['stim'].pos = (.4,0)
    #g.states[6]['stim'].setAutoDraw(True)
 

def setStates():
    """
    Sets all the states to default
    """
    g.states[1]['stim'] = visual.Rect(g.win, size = [g.rectangleSize,g.rectangleSize], units = 'norm', fillColor=g.defaultColor, lineColor = g.defaultColor, pos = (.2,.3) )
    g.states[2]['stim'] = visual.Rect(g.win, size = [g.rectangleSize,g.rectangleSize], units = 'norm', fillColor=g.defaultColor, lineColor = g.defaultColor, pos = (-.2,.3))
    g.states[3]['stim'] = visual.Rect(g.win, size = [g.rectangleSize,g.rectangleSize], units = 'norm', fillColor=g.defaultColor, lineColor = g.defaultColor, pos = (-.4,0) )
    g.states[4]['stim'] = visual.Rect(g.win, size = [g.rectangleSize,g.rectangleSize], units = 'norm', fillColor=g.defaultColor, lineColor = g.defaultColor, pos = (-.2,-.4))
    g.states[5]['stim'] = visual.Rect(g.win, size = [g.rectangleSize,g.rectangleSize], units = 'norm', fillColor=g.defaultColor, lineColor = g.defaultColor, pos = (.2,-.4))
    g.states[6]['stim'] = visual.Rect(g.win, size = [g.rectangleSize,g.rectangleSize], units = 'norm', fillColor=g.defaultColor, lineColor = g.defaultColor, pos = (.4,0) )


def setTransitions():
    """
    Set Stim Transitions
    """
    g.states[1]['left']['arrow'] = visual.ShapeStim(g.win, vertices = [(.18,.42), (-.10, .42), (-.10, .44), (-.18, .4), (-.10, .36), (-.10, .38), (.18, .38)], size=.5, lineColor='white', units = 'norm', pos = (0,.1))
    g.states[1]['left']['valueText'] = visual.TextStim(g.win, text = '+' + str(g.states[1]['left']['value']) , units = 'norm', pos = (0,.4), height = .08)

    g.states[1]['right']['arrow'] = visual.ShapeStim(g.win, vertices = [(-.22, -.54), (-.22, .28), (-.24, .28), (-.2, .38), (-.16, .28), (-.18 , .28), (-.18, -.54)], size=.5, lineColor='white', units = 'norm', pos = (-.1,0), ori = 210)
    g.states[1]['right']['valueText'] = visual.TextStim(g.win, text = '+' + str(g.states[1]['right']['value']) , units = 'norm', pos = (.1,0), height = .08)
    

    g.states[2]['left']['arrow'] = visual.ShapeStim(g.win, vertices = [(.18,.42), (-.10, .42), (-.10, .44), (-.18, .4), (-.10, .36), (-.10, .38), (.18, .38)], size=.5, lineColor='white', units = 'norm', pos = (-.18,.08), ori = 300)
    g.states[2]['left']['valueText'] = visual.TextStim(g.win, text = str(g.states[2]['left']['value']) , units = 'norm', pos = (-.4,.30), height = .08)

    g.states[2]['right']['arrow'] = visual.ShapeStim(g.win, vertices = [(-.22, -.54), (-.22, .28), (-.24, .28), (-.2, .38), (-.16, .28), (-.18 , .28), (-.18, -.54)], size=.5, lineColor='white', units = 'norm', pos = (-.1,-.13), ori = 145)
    g.states[2]['right']['valueText'] = visual.TextStim(g.win, text = str(g.states[2]['right']['value']) , units = 'norm', pos = (0,0), height = .08)

    g.states[3]['left']['arrow'] = visual.ShapeStim(g.win, vertices = [(-.22, -.54), (-.22, .28), (-.24, .28), (-.2, .38), (-.16, .28), (-.18 , .28), (-.18, -.54)], size=.5, lineColor='white', units = 'norm', pos = (0.04,- 0.1), ori= 90)
    g.states[3]['left']['valueText'] = visual.TextStim(g.win, text = str(g.states[3]['left']['value']) , units = 'norm', pos = (0,.1), height = .08)


    g.states[3]['right']['arrow'] = visual.ShapeStim(g.win, vertices = [(.18,.42), (-.10, .42), (-.10, .44), (-.18, .4), (-.10, .36), (-.10, .38), (.18, .38)], size=.5, lineColor='white', units = 'norm', pos = (-.18,-.1), ori = 235)
    g.states[3]['right']['valueText'] = visual.TextStim(g.win, text = str(g.states[3]['right']['value']) , units = 'norm', pos = (-.4,-.30), height = .08)

    g.states[4]['left']['arrow'] = visual.ShapeStim(g.win, vertices = [(-.22, -.54), (-.22, .28), (-.24, .28), (-.2, .38), (-.16, .28), (-.18 , .28), (-.18, -.54)], size=.5, lineColor='white', units = 'norm', pos = (-.1,0))
    g.states[4]['left']['valueText'] = visual.TextStim(g.win, text = '+' + str(g.states[4]['left']['value']) , units = 'norm', pos = (-.14,0), height = .08)
    
    g.states[4]['right']['arrow'] = visual.ShapeStim(g.win, vertices = [(.18,.42), (-.10, .42), (-.10, .44), (-.18, .4), (-.10, .36), (-.10, .38), (.18, .38)], size=.5, lineColor='white', units = 'norm', pos = (0,-.2), ori = 180)
    g.states[4]['right']['valueText'] = visual.TextStim(g.win, text = str(g.states[4]['right']['value']) , units = 'norm', pos = (0,-.3), height = .08)

    g.states[5]['left']['arrow'] = visual.ShapeStim(g.win, vertices = [(-.22, -.54), (-.22, .28), (-.24, .28), (-.2, .38), (-.16, .28), (-.18 , .28), (-.18, -.54)], size=.5, lineColor='white', units = 'norm', pos = (.3,0))
    g.states[5]['left']['valueText'] = visual.TextStim(g.win, text = str(g.states[5]['left']['value']) , units = 'norm', pos = (.14,0), height = .08)

    g.states[5]['right']['arrow'] = visual.ShapeStim(g.win, vertices = [(.18,.42), (-.10, .42), (-.10, .44), (-.18, .4), (-.10, .36), (-.10, .38), (.18, .38)], size=.5, lineColor='white', units = 'norm', pos = (.18,-.12), ori = 115)
    g.states[5]['right']['valueText'] = visual.TextStim(g.win, text = str(g.states[5]['right']['value']) , units = 'norm', pos = (.4,-.30), height = .08)

    g.states[6]['left']['arrow'] = visual.ShapeStim(g.win, vertices = [(-.22, -.54), (-.22, .28), (-.24, .28), (-.2, .38), (-.16, .28), (-.18 , .28), (-.18, -.54)], size=.5, lineColor='white', units = 'norm', pos = (-.04,0.1), ori= 270)
    g.states[6]['left']['valueText'] = visual.TextStim(g.win, text = '+' + str(g.states[6]['left']['value']) , units = 'norm', pos = (0,.1), height = .08)

    g.states[6]['right']['arrow'] = visual.ShapeStim(g.win, vertices = [(.18,.42), (-.10, .42), (-.10, .44), (-.18, .4), (-.10, .36), (-.10, .38), (.18, .38)], size=.5, lineColor='white', units = 'norm', pos = (.18,.1), ori = 60)
    g.states[6]['right']['valueText'] = visual.TextStim(g.win, text = str(g.states[6]['right']['value']) , units = 'norm', pos = (.4,.30), height = .08)

def doFreeTraining(duration):
    """
    Free Duration: Subject has limited time traversing across the map
    """
    #print 'on freeTraining'
    g.win.flip() # clear window

    start_state = random.randrange(1,7) # Random state from 1,6
    current_state = start_state
    last_state = ''
    transition_path = []

    timer = duration
    timerstim = visual.TextStim(g.win, text = str(timer), units = 'norm', pos = (0,0.7), height = .15)

    now = g.clock.getTime()
    
    # Freely Traverse within time limit
    while g.clock.getTime() <= now + duration:
  
        StimToolLib.check_for_esc()

        k = event.getKeys([ g.session_params[g.run_params['select_1']], g.session_params[g.run_params['select_2']], 's']) 
        
        # Draw Timer
        timer =  "%i" % int((now + duration) - g.clock.getTime())
        timerstim.setText(timer)
        timerstim.draw()

        resetStates()

        g.states[current_state]['stim'].size = [g.rectangleSize + 0.02, g.rectangleSize + 0.02]
        g.states[current_state]['stim'].fillColor = g.targetColor  # Set the curent white Color
        g.states[current_state]['stim'].lineColor = g.targetOutline 
        
        # Draw boxes
        drawBoxes()

        if g.show_transitions and len(transition_path) > 1:
            g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
            g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
            g.states[transition_path[0]][transition_path[1]]['arrow'].draw()
            if g.show_transitions_value:
                g.states[transition_path[0]][transition_path[1]]['valueText'].draw()
            #g.states[current_state]['left']['arrow'].draw()

        g.win.flip()
        # Press left
        if not len(k) == 0:
            g.states[current_state]['stim'].fillColor = g.defaultColor
            g.states[current_state]['stim'].lineColor = g.defaultColor
            last_state = current_state
            if k[0] == g.session_params[g.run_params['select_1']]:
                resp = -1
                transition_path = [current_state, 'left']
                current_state = g.states[current_state]['left']['state']
    
            # PRessed Right
            if k[0] == g.session_params[g.run_params['select_2']]:
                resp = 1
                transition_path = [current_state, 'right']
                current_state = g.states[current_state]['right']['state']

            if k[0] == 's': return
            StimToolLib.mark_event(g.output, timer, 'freeTraining', event_types['RESPONSE'], now, '', str(resp), last_state, g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
    


def drawBoxes():
    # Draw Boxes
    g.states[1]['stim'].draw()
    g.states[2]['stim'].draw()
    g.states[3]['stim'].draw()
    g.states[4]['stim'].draw()
    g.states[5]['stim'].draw()
    g.states[6]['stim'].draw()

def set_autodraw(setA):
    g.states[1]['stim'].setAutoDraw(setA)
    g.states[2]['stim'].setAutoDraw(setA)
    g.states[3]['stim'].setAutoDraw(setA)
    g.states[4]['stim'].setAutoDraw(setA)
    g.states[5]['stim'].setAutoDraw(setA)
    g.states[6]['stim'].setAutoDraw(setA)


def doGoalTraining(trials):
    """
    Run Goal Trails.
    """
    TOTAL_TRIALS = len(trials)
    #print 'on GoalTraining'
    g.win.flip()
    
    topText = 'Get to the Red Goal with your LAST move.'
    topTextstim = visual.TextStim(g.win, text = topText, units = 'norm', pos = (0,0.7), height = .07)
    

    midText = "You have %i moves" % 0
    midTextstim = visual.TextStim(g.win, text = midText, units = 'norm', pos = (0,0), height = .07)

    goalTextstim = visual.TextStim(g.win, text = 'Goal', units = 'norm', pos = (0,0), height = .07, color = g.goalTextColor)

    final_state = 0
    goal_state = 0

    transition_path = []

    midTextstim.pos = (0,.6)
    
    for idx,trial in enumerate(trials):
        # Repeat only until we reach the total depths
        repeat = True
        while repeat:
            depth = int(trial[0])
            start_state = int(trial[1])
            goal_state = int(trial[2])

            resetStates()
            g.win.flip()

            current_state = start_state
            last_state = 1
            transition_path = []
            while depth > 0:
                
                StimToolLib.check_for_esc()
                topTextstim.setText('Get to the Red Goal with your LAST move' )
                if depth > 1:
                    midTextstim.setText("You have %i moves left. " % depth)
                else:
                    midTextstim.setText("You have %i move left. " % depth)

                topTextstim.draw()
                midTextstim.draw()

                resetStates()

                # Current States
                g.states[current_state]['stim'].size = [g.rectangleSize + 0.02, g.rectangleSize + 0.02]
                g.states[current_state]['stim'].fillColor = g.targetColor
                g.states[current_state]['stim'].lineColor = g.targetOutline

                # Goal State
                g.states[goal_state]['stim'].fillColor = g.goalColor
                g.states[goal_state]['stim'].lineColor = g.goalColor
            

                if current_state == goal_state:
                    g.states[current_state]['stim'].setLineWidth(4)
                    g.states[current_state]['stim'].lineColor = g.targetOutline

                drawBoxes()

                goalTextstim.setPos(g.states[goal_state]['stim'].pos)
                goalTextstim.draw()

                # Show the Trial Tracker
                trialTracekrStim = visual.TextStim(g.win, text = '%s/%s' % (idx, TOTAL_TRIALS), units = 'norm', height = .05, pos = (0,-0.85))
                trialTracekrStim.draw()

                # Show Error:
                erroCount = visual.TextStim(g.win, text = 'Errors: %s' % g.goalErrors, units = 'norm', height = .05, pos = (0,-0.90), color = 'red')
                erroCount.draw()

                # Show Transitions if path exists
                if g.show_transitions and len(transition_path) > 1:
                    g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
                    g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
                    g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
                    if g.show_transitions_values:
                        g.states[transition_path[0]][transition_path[1]]['valueText'].draw()
                
                #g.states[current_state]['left']['arrow'].draw()
                g.win.flip()

                event.clearEvents() # Clear Events in the event buffer

                k = event.waitKeys(keyList = [ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape', 's'])
                last_state = current_state
                if k[0] == g.session_params[g.run_params['select_1']]:
                    resp = -1
                    transition_path = [current_state, 'left']
                    current_state = g.states[current_state]['left']['state']

                if k[0] == g.session_params[g.run_params['select_2']]:
                    resp = 1
                    transition_path = [current_state, 'right']
                    current_state = g.states[current_state]['right']['state']

                if k[0] == 's': 
                    # Skip Key pressed
                    g.skipped = True
                    g.goalErrors = 0
                    return
                if k[0] == "escape": raise StimToolLib.QuitException
                #print trial, start_state, goal_state, current_state, k
                depth = depth - 1
                
            resetStates()
            g.states[current_state]['stim'].size = [g.rectangleSize + 0.02, g.rectangleSize + 0.02]
            g.states[current_state]['stim'].fillColor = g.targetColor
            g.states[current_state]['stim'].lineColor = g.targetOutline

            
            g.states[goal_state]['stim'].fillColor = g.goalColor
            g.states[goal_state]['stim'].lineColor = g.goalColor

            if current_state == goal_state:
                g.states[current_state]['stim'].setLineWidth(4)
                g.states[current_state]['stim'].lineColor = g.targetOutline
            
            drawBoxes()

            goalTextstim.setPos(g.states[goal_state]['stim'].pos)
            goalTextstim.draw()

            # Show the Trial Tracker
            trialTracekrStim = visual.TextStim(g.win, text = '%s/%s' % (idx, TOTAL_TRIALS), units = 'norm', height = .05, pos = (0,-0.85))
            trialTracekrStim.draw()

            # Show Error:
            erroCount = visual.TextStim(g.win, text = 'Errors: %s' % g.goalErrors, units = 'norm', height = .05, pos = (0,-0.90), color = 'red')
            erroCount.draw()

            # Show Transitions if path exists
            if g.show_transitions and len(transition_path) > 1:
                g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
                g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
                g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
                if g.show_transitions_values:
                    g.states[transition_path[0]][transition_path[1]]['valueText'].draw()

            
            now = g.clock.getTime()

            midTextstim.pos = (0,.6)
            if current_state == goal_state: 
                midTextstim.color = '#00FF00'
                
                if g.goalErrors > 0:
                    midTextstim.setText("Nice! That was it!")
                else: 
                    midTextstim.setText("Good Job!")
                midTextstim.draw()
                repeat = False
                # Exit if error Max reached
                if g.goalErrors > g.errorMax: 
                    g.win.flip()
                    StimToolLib.just_wait(g.clock, now + 1) # wait 1 seconds
                    return
            else:
                midTextstim.color = '#FF0000'
                midTextstim.setText("That was incorrect. Please try again. ")
                midTextstim.draw()
                depth = int(trial[0])
                g.goalErrors = g.goalErrors + 1
                repeat = True

            g.win.flip()
            StimToolLib.just_wait(g.clock, now + 1) # wait 1 seconds

def doPathTest(trials):
    """
    Run Goal Trails.
    """
    TOTAL_TRIALS = len(trials)
    #print 'on GoalTraining'
    g.win.flip()
    
    final_state = 0
    goal_state = 0

    transition_path = []

    goalTextstim = visual.TextStim(g.win, text = 'Goal', units = 'norm', pos = (0,0), height = .07, color = g.goalTextColor)
    
    for idx,trial in enumerate(trials):
        # Repeat only until we reach the total depths
        
        depth = int(trial[0])
        start_state = int(trial[1])
        goal_state = int(trial[2])

        correct_key = getNextButton(start_state, goal_state)
        
        transition_path = [start_state, correct_key]

        resetStates()
        g.win.flip()

        current_state = start_state
        
        # # Current States
        g.states[current_state]['stim'].fillColor = g.targetColor
        g.states[current_state]['stim'].lineColor = g.targetOutline

        # Goal State
        g.states[goal_state]['stim'].fillColor = g.goalColor
        g.states[goal_state]['stim'].lineColor = g.goalColor
    

        
        topText = 'How many points is this path?'
        topTextstim = visual.TextStim(g.win, text = topText, units = 'norm', pos = (0,0.7), height = .07)
        

        midText = "A) -20   B) +20   C) +140   D) -70"
        midTextstim = visual.TextStim(g.win, text = midText, units = 'norm', pos = (0,0.6), height = .07)

        topTextstim.draw()
        midTextstim.draw()

        drawBoxes()

        # Draw Path
        g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
        g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
        g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 

        # Draw the "Goal TExt"
        goalTextstim.setPos(g.states[goal_state]['stim'].pos)
        goalTextstim.draw()

        # Show the Trial Tracker
        trialTracekrStim = visual.TextStim(g.win, text = '%s/%s' % (idx, TOTAL_TRIALS), units = 'norm', height = .05, pos = (0,-0.85))
        trialTracekrStim.draw()

        # Show Error:
        erroCount = visual.TextStim(g.win, text = 'Errors: %s' % g.goalErrors, units = 'norm', height = .05, pos = (0,-0.90), color = 'red')
        erroCount.draw()
            
        #g.states[current_state]['left']['arrow'].draw()
        g.win.flip()

        event.clearEvents() # Clear Events in the event buffer

        resp = 0
        question_onset = g.clock.getTime()
        k = event.waitKeys(keyList = [ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], g.session_params[g.run_params['select_3']], g.session_params[g.run_params['select_4']], 'escape', 's'])
        
        if k[0] == g.session_params[g.run_params['select_1']]: resp = -20
        if k[0] == g.session_params[g.run_params['select_2']]: resp = 20
        if k[0] == g.session_params[g.run_params['select_3']]: resp = 140
        if k[0] == g.session_params[g.run_params['select_4']]: resp = -70
        if k[0] == "escape": raise StimToolLib.QuitException
        if k[0] == 's':
            # Skipping
            g.goalErrors = 0
            return
        

        g.win.flip()

        resetStates()
        g.states[current_state]['stim'].fillColor = g.targetColor
        g.states[current_state]['stim'].lineColor = g.targetOutline

        # Goal State
        g.states[goal_state]['stim'].fillColor = g.goalColor
        g.states[goal_state]['stim'].lineColor = g.goalColor
    
        drawBoxes()

        goalTextstim.setPos(g.states[goal_state]['stim'].pos)
        goalTextstim.draw()

        # Draw Path
        g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
        g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
        g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
        # Draw the Value
        g.states[transition_path[0]][transition_path[1]]['valueText'].draw()

        # Show the Trial Tracker
        trialTracekrStim = visual.TextStim(g.win, text = '%s/%s' % (idx, TOTAL_TRIALS), units = 'norm', height = .05, pos = (0,-0.85))
        trialTracekrStim.draw()

        # Show Error:
        erroCount = visual.TextStim(g.win, text = 'Errors: %s' % g.goalErrors, units = 'norm', height = .05, pos = (0,-0.90), color = 'red')
        erroCount.draw()

        correct_points = g.states[transition_path[0]][transition_path[1]]['value']
       
        outcome = ''
        if resp == correct_points:
            outcome = 'correct'
            topTextstim.color = '#00FF00'
            topTextstim.setText("Good Job!")
            
        else:
            outcome = 'incorrect'
            topTextstim.color = '#FF0000'
            topTextstim.setText("Incorrect. The path will get you %s points " % correct_points )
            depth = int(trial[0])
            g.goalErrors = g.goalErrors + 1

        # Write to response to file
        now = g.clock.getTime()
        StimToolLib.mark_event(g.output, str(idx), '->'.join([str(elem) for elem in transition_path]), event_types['RESPONSE'], str(now - question_onset ), str(resp), str(correct_points), outcome, g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            

        topTextstim.draw()
        midTextstim.draw()
                

        g.win.flip()
        now = g.clock.getTime()
        StimToolLib.just_wait(g.clock, now + 2)

        # Incorrect and max Error reached
        if (resp != correct_points) and g.goalErrors > g.errorMax: 
            return


def doTaskTrial(start_state, depth, duration,  showFeedback):
    """
    Single Trial

    :param state_state inittial starting state
    :param depth number of moves to enter
    :param duration time limit the person is allowed to enter their moves
    :param showFeedback shows the points right after the each trial if it's True
    """
    DEPTH_ABS = depth
    event.clearEvents()
    #wait for 100ms at the beginning of a trial
    if duration is not None: StimToolLib.just_wait(g.clock, g.ideal_trial_start + 0.1)

    transition_path = []
    points = 0
    
    resetStates()
    g.win.flip()
    planingDuration = 9

    current_state = start_state

    now = g.clock.getTime()
    planing_onset = now
    trial_start = now
    time_to_end = g.ideal_trial_start + 15 # Trial must last only 15 seconds

    StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['TRIAL_ONSET'], now, 'NA', 'NA', 'NA', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
    response_start = ''
    key_pressed_num  = 0
    move_sequence = []
    transitions = []
    if duration is not None:

        StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['PLANNING_ONSET'], now, 'NA', 'NA', str(planingDuration), g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
        
        g.topTextstim.setText('You have %i moves' % depth)
        g.topTextstim.draw()
       

        g.bottomTextstim.setHeight(.05)
        g.bottomTextstim.setText('Please enter the full sequence of moves first to see the result.')
        g.bottomTextstim.draw()


        g.timerstim.color = '#FFFFFF'
        # timer =  "%s" % int((now + planingDuration + 1) - g.clock.getTime())
        # g.timerstim.setText('Planning Time (9s)')

        timer = "%s" % int((now + planingDuration + 1) - g.clock.getTime())
        g.timerstim.setText(timer)
        g.timerstim.draw()

        resetStates()
    
        # Current States
        g.states[current_state]['stim'].fillColor = g.targetColor
        g.states[current_state]['stim'].lineColor = g.targetOutline

        drawBoxes()
        
        g.win.flip()

        # Wait up to 9 seconds
        while g.clock.getTime() < now + planingDuration:

            timer = "%s" % int((now + planingDuration + 1) - g.clock.getTime())
        
            g.timerstim.setText(timer)
            g.timerstim.draw()
            g.topTextstim.draw()
            g.bottomTextstim.draw()
            resetStates()
    
            # Current States
            g.states[start_state]['stim'].fillColor = g.targetColor
            g.states[start_state]['stim'].lineColor = g.targetOutline

            drawBoxes()
 
            k = event.getKeys([ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], "escape", 's' ])
            g.win.flip()
            if len(k) == 0: continue
            response_start = g.clock.getTime()

            move_sequence.append(k[0]) # Add pressed transitions to path list
            
            if k[0] == "escape": raise StimToolLib.QuitException
            if k[0] == g.session_params[g.run_params['select_1']]: 
                resp = -1
                #transitions.append('left')
                points = points + g.states[current_state]['left']['value']
                current_state = g.states[current_state]['left']['state']
            if k[0] == g.session_params[g.run_params['select_2']]: 
                resp = 1
                transitions.append('right')
                points = points + g.states[current_state]['right']['value']
                current_state = g.states[current_state]['right']['state']
            if k[0] == 's':
                # skipping trial
                return
            
            StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['RESPONSE_ONSET'], response_start, 'NA', 'NA', str(duration), g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            StimToolLib.mark_event(g.output, g.trial, str(start_state) +'_' + str(g.trial_type) + '_' + str(key_pressed_num), event_types['RESPONSE'], response_start, str(response_start - planing_onset), str(resp), 'NA', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            depth = depth - 1
            key_pressed_num = key_pressed_num + 1
            break


    # Enter Moves
    if not response_start:
        response_start = g.clock.getTime()
        StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['RESPONSE_ONSET'], response_start, 'NA', 'NA', str(duration), g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
    
    

    #g.timerstim.color = '#FF0000'
    g.timerstim.bold = True

    g.topMidTextstim.pos = (0,.45)


    # Get Transition sequenc
    if duration is not None:
        g.timerstim.setText('Enter Moves now (2.5s)')
        g.timerstim.draw()


    transition_path = []
    while True:

        # Exit Loop with the time is up. If there is a duration
        if duration is not None: 
            if g.clock.getTime() >= response_start + 2.5: break
        
        event.clearEvents()
        g.topTextstim.setText('You have %i moves' % depth)
        g.topTextstim.draw()

        if duration is not None:
            g.timerstim.draw()

        # Show Transitions if no time limit
        if duration is None:
            resetStates()
            # Current States
            g.states[current_state]['stim'].fillColor = g.targetColor
            g.states[current_state]['stim'].lineColor = g.targetOutline
            
            if len(transition_path) > 1 :
                g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
                g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
                g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
                g.states[transition_path[0]][transition_path[1]]['valueText'].draw()

        drawBoxes()

        g.win.flip()

        # Once Enter all Moves than exists regardless if there is a duration
        if depth <= 0: break
    
        #event.clearEvents() # Clear Events in the event buffer
        if duration is None:
            k = event.waitKeys(keyList = [ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape','s' ])
        else:
            k = event.getKeys([ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape','s' ])
        

        if len(k) == 0: continue
        now = g.clock.getTime()
        if k[0] == g.session_params[g.run_params['select_1']]:
            resp = -1
            transitions.append('left')
            transition_path = [current_state, 'left']
            points = points + g.states[current_state]['left']['value']
            current_state = g.states[current_state]['left']['state']

        if k[0] == g.session_params[g.run_params['select_2']]:
            resp = 1
            transitions.append('right')
            transition_path = [current_state, 'right']
            points = points + g.states[current_state]['right']['value']
            current_state = g.states[current_state]['right']['state']
        if k[0] == "escape": raise StimToolLib.QuitException
        if k[0] == 's': return

        
        StimToolLib.mark_event(g.output, g.trial, str(start_state) +'_' + str(g.trial_type) + '_' + str(key_pressed_num), event_types['RESPONSE'], now, str(now - planing_onset), str(resp), str(points), g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
        move_sequence.append(k[0]) # Add pressed transitions to path list

        depth = depth - 1
        key_pressed_num += 1

    
    g.topTextstim.setAutoDraw(False)
    g.bottomTextstim.setAutoDraw(False)
    g.timerstim.setAutoDraw(False)

    if len(move_sequence) < DEPTH_ABS: 
        points = -200
        g.bottomTextstim.setText('You did not enter all your moves')
    else:
        # Show Transition Animation if there is a duration

        if duration is not None:
            now = g.clock.getTime()
            StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['ANIMATION_ONSET'], now, 'NA', 'NA', 'NA', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            transition_path = []
            
            current_state = start_state
            for move in move_sequence:
                # g.topTextstim.setText('You have %i moves' % DEPTH_TRIAL)
                # g.topTextstim.draw()

                if move == g.session_params[g.run_params['select_1']]:
                    resp = -1
                    transition_path = [current_state, 'left']
                    current_state = g.states[current_state]['left']['state']
                    
                
                if move == g.session_params[g.run_params['select_2']]:
                    resp = 1
                    transition_path = [current_state, 'right']
                    current_state = g.states[current_state]['right']['state']
                    

                resetStates()
                # Current States
                g.states[current_state]['stim'].fillColor = g.targetColor
                g.states[current_state]['stim'].lineColor = g.targetOutline
                
                drawBoxes()
                # draw Transision
                g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
                g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
                g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
                g.states[transition_path[0]][transition_path[1]]['valueText'].draw()

                now = g.clock.getTime()
                g.win.flip()
                StimToolLib.just_wait(g.clock, now + .75) # time the frame rate changes
            
        
        # StimToolLib.just_wait(g.clock, now + 1) 

    # ITI t o
    set_autodraw(False)

    outcome = getOutcome(start_state, DEPTH_ABS, transitions)
    g.feedbackstim.setHeight(.1)
    if showFeedback:
        if len(move_sequence) < DEPTH_ABS: 
            points = -200
            g.bottomTextstim.setHeight(.1)
            g.bottomTextstim.setText('You did not enter all your moves')
            g.bottomTextstim.draw()
        if points < 0:
            g.feedbackstim.setText('You have lost a total of %i points.' % points)
        else:
            g.feedbackstim.setText('You have won a total of %i points.' % points)
        g.feedbackstim.draw()
    
        g.win.flip()
        now = g.clock.getTime()
        StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['FEEDBACK'], now, 'NA', 'NA', str(points), g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
        StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['OUTCOME'], now, 'NA', 'NA', outcome, g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
        StimToolLib.just_wait(g.clock, now + 1) # show feedback for 1 seond seconds

    # if there is a duration, than display the Fixation ITI for the rest till end time
    if duration is not None:
        g.win.flip()
        g.fixation.draw()
        g.win.flip()

        now = g.clock.getTime()
        # print(now - trial_start)
        # if current trial duration is above 15 seconds, 
        # Add 1 second to show fixation for max 16 seconds
        if (now - trial_start) >= 15 and (now - trial_start) < 16:
            time_to_end = time_to_end + 1
            g.ideal_trial_start = g.ideal_trial_start + 1
        
            print('### %f ###' % g.trial)
            print('extending +1 time_to_end %f\t\tcurrent duration: %f' % (time_to_end, now - trial_start))
            print('total Duration: %f' % ( time_to_end - trial_start ))
            StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['EXTENDING_TIME'], now, str(now - trial_start), 'NA', 'adding 1 second', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            

        # If curren trial is 16 seconds, extend to max 17 seconds
        if (now - trial_start) >= 16:
            time_to_end = time_to_end + 2
            g.ideal_trial_start = g.ideal_trial_start + 2
        
            print('### %f ###' % g.trial)
            print('extending +2 time_to_end %f\t\tcurrent duration: %f' % (time_to_end, now - trial_start))
            print('total Duration: %f' % ( time_to_end - trial_start ))
            StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['EXTENDING_TIME'], now, str(now - trial_start), 'NA', 'adding 2 seconds', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            
            
            # StimToolLib.just_wait(g.clock, now + .5) # wait  seconds
        # Tackle on .5 second for duration longer than 14 second
        

        StimToolLib.mark_event(g.output, g.trial, g.trial_type, event_types['FIXATION_ONSET'], now, 'NA', 'NA', int(time_to_end - now), g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
        
        StimToolLib.just_wait(g.clock, time_to_end) # wait  seconds
    
        g.ideal_trial_start = g.ideal_trial_start + 15
    
    g.points = g.points + points



def doTaskTrialB(start_state, depth, duration, showFeedback):
    """
    Single Task Trial but modified solely for Part B of Task Training where sbuject enters moves.
    Then shows moves in sequence
    """
    StimToolLib.check_for_esc()

    current_state = start_state
    DEPTH_TRIAL = depth
    g.topTextstim.setText('You have %i moves' % depth)
    g.topTextstim.draw()

    resetStates()

    # Current States
    g.states[current_state]['stim'].fillColor = g.targetColor
    g.states[current_state]['stim'].lineColor = g.targetOutline

    drawBoxes()

    g.win.flip()

    # Get Transition sequenc
    move_sequence = []
    while True:
        
        if depth == 0: break

        StimToolLib.check_for_esc()
        
        g.topTextstim.setText('You have %i moves' % depth)
        g.topTextstim.draw()
        resetStates()
        g.states[current_state]['stim'].fillColor = g.targetColor
        g.states[current_state]['stim'].lineColor = g.targetOutline

        drawBoxes()
        g.win.flip()


        event.clearEvents() # Clear Events in the event buffer
        k = event.waitKeys(keyList=[ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 's'])
        if k[0] == 's': return
        move_sequence.append(k[0]) # Add pressed transitions to path list

        depth = depth - 1
        
    
    # Show Transition Animation
    transition_path = []
    points = 0
    if len(move_sequence)  == DEPTH_TRIAL:
        for move in move_sequence:
            # g.topTextstim.setText('You have %i moves' % DEPTH_TRIAL)
            # g.topTextstim.draw()

            if move == g.session_params[g.run_params['select_1']]:
                resp = -1
                transition_path = [current_state, 'left']
                points = points + g.states[current_state]['left']['value']
                current_state = g.states[current_state]['left']['state']
                
            
            if move == g.session_params[g.run_params['select_2']]:
                resp = 1
                transition_path = [current_state, 'right']
                points = points + g.states[current_state]['right']['value']
                current_state = g.states[current_state]['right']['state']
                

            resetStates()
            # Current States
            g.states[current_state]['stim'].fillColor = g.targetColor
            g.states[current_state]['stim'].lineColor = g.targetOutline
            drawBoxes()

            # draw Transision
            g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
            g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
            g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
            g.states[transition_path[0]][transition_path[1]]['valueText'].draw()

            g.win.flip()
            now = g.clock.getTime()
            StimToolLib.just_wait(g.clock, now + 1)

        
    #StimToolLib.just_wait(g.clock, now + 1) 

    g.win.flip()

    if len(move_sequence) < DEPTH_TRIAL:
        points = -200


    if showFeedback:
        if points > 0:
            midTextstim = visual.TextStim(g.win, text = 'You have won a total of %i points.' % points, units = 'norm', pos = (0,0), height = .1)
            midTextstim.draw()
        else:
            midTextstim = visual.TextStim(g.win, text = 'You have lost a total of %i points.' % points, units = 'norm', pos = (0,0), height = .1)
            midTextstim.draw()
        g.win.flip()
        now = g.clock.getTime()
        StimToolLib.just_wait(g.clock, now + 2) # wait  seconds



def doTaskTraining(trials):
    """
    Task Training: Broken into 3 parts
    
    Part A:
        3 Trials where subject enters moves based on certain depth without time contraints. Feedback is shown 
    Part B:
        3 Traisl where subject enters moves. Sequence shown later. Feedback not shown
    Part C:
        3 Trials where subject is allowed 9 seconds to make a move. If moves entered before the time is up, they
        Are given 2.5 seconds to finish the move sequence.
    """

    print("Part A")
    
    # Part A
    depth2 = [x for x in trials if x[0] == '2']
    depth3 = [x for x in trials if x[0] == '3']


    for trial in random.sample(depth2 + depth3, 6):
        g.win.flip() # clear window
        depth = int(trial[0])
        start_state = int(trial[1])
        goal_state = int(trial[2])
        #start_state = random.randrange(1,7) # Random state from 1,6
        #depth = random.randrange(2,4) # Random Depth, 2,3
        duration = None # no Time Constraing on entering moves
        doTaskTrial(start_state, depth,duration, True) # Do Single Trial  

    
    print('Part B')
    # Part B
    k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP5_3_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide27.m4a.aiff' )
            )
    
    for trial in random.sample(depth2 + depth3, 12):
        g.win.flip() # clear window
        
        #start_state = random.randrange(1,7) # Random state from 1,6
        #depth = random.randrange(2,4) # Random Depth, 2,3
        depth = int(trial[0])
        start_state = int(trial[1])
        goal_state = int(trial[2])
        duration = None
        doTaskTrialB(start_state, depth,duration, True) # Do Single Trial


    # Part C
    k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP5_4_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide28.m4a.aiff' )
            )
    k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP5_5_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide29.m4a.aiff' )
            )


    now = g.clock.getTime()
    g.ideal_trial_start = now
    # Part C
    for trial in random.sample(depth2 + depth3, 6):
        g.win.flip() # clear window
        
        depth = int(trial[0])
        start_state = int(trial[1])
        goal_state = int(trial[2])
        #start_state = random.randrange(1,7) # Random state from 1,6
        #depth = random.randrange(2,4) # Random Depth, 2,3
        duration = 3 # Must enter moves within 3 seconds
        doTaskTrial(start_state, depth,duration, True) # Do Single Trial
    
    k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP5_6_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide30.m4a.aiff' )
            )



def doTestTraining(trials):
    """
    Run Test Trails.
    """
    #print 'on TestTraining'
    g.win.flip()
    
    topText = 'Get to the Goal with your last move.'
    topTextstim = visual.TextStim(g.win, text = topText, units = 'norm', pos = (0,0.7), height = .07)
    

    midText = ""
    midTextstim = visual.TextStim(g.win, text = midText, units = 'norm', pos = (0,0), height = .07)

    goalTextstim = visual.TextStim(g.win, text = 'Goal', units = 'norm', pos = (0,0), height = .07, color = g.goalTextColor)

    final_state = 0
    goal_state = 0
    
    for trial in trials:
        # Repeat only until we reach the total depths
        repeat = True
        
        depth = int(trial[0])
        start_state = int(trial[1])
        goal_state = int(trial[2])

        resetStates()
        g.win.flip()

        current_state = start_state
        transition_path = []
        while depth > 0:
            
            StimToolLib.check_for_esc()
            topTextstim.setText('Get to the Red Goal with one move.' )

            topTextstim.draw()
        
            resetStates()

            # Current States
            g.states[current_state]['stim'].fillColor = g.targetColor
            g.states[current_state]['stim'].lineColor = g.targetOutline

            # Goal State
            g.states[goal_state]['stim'].fillColor = g.goalColor
            g.states[goal_state]['stim'].lineColor = g.goalColor
        

            if g.show_transitions and len(transition_path) > 1:
                g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
                g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
                g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
                if g.show_transitions_values:
                    g.states[transition_path[0]][transition_path[1]]['valueText'].draw()

            drawBoxes()

            goalTextstim.setPos(g.states[goal_state]['stim'].pos)
            goalTextstim.draw()
            g.win.flip()

            event.clearEvents() # Clear Events in the event buffer
            k = event.waitKeys(keyList = [ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape' ])

            if k[0] == "escape": raise StimToolLib.QuitException
            if k[0] == g.session_params[g.run_params['select_1']]:
                resp = -1
                transition_path = [current_state, 'left']
                current_state = g.states[current_state]['left']['state']

            if k[0] == g.session_params[g.run_params['select_2']]:
                resp = 1
                transition_path = [current_state, 'right']
                current_state = g.states[current_state]['right']['state']
            #print trial, start_state, goal_state, current_state, k
            depth = depth - 1
            
    
        resetStates()
        g.states[current_state]['stim'].fillColor = g.targetColor
        g.states[current_state]['stim'].lineColor = g.targetOutline

        g.states[goal_state]['stim'].fillColor = g.goalColor
        g.states[goal_state]['stim'].lineColor = g.goalColor
    
        drawBoxes()

        goalTextstim.setPos(g.states[goal_state]['stim'].pos)
        goalTextstim.draw()

        if g.show_transitions and len(transition_path) > 1:
                g.states[transition_path[0]][transition_path[1]]['arrow'].fillColor = g.pathColor[transition_path[1]]
                g.states[transition_path[0]][transition_path[1]]['arrow'].lineColor = 'white'
                g.states[transition_path[0]][transition_path[1]]['arrow'].draw() 
                if g.show_transitions_values:
                    g.states[transition_path[0]][transition_path[1]]['valueText'].draw()
        
        now = g.clock.getTime()
        midTextstim.pos = (0,.6)
        if current_state == goal_state: 
            midTextstim.color = '#00FF00'
            midTextstim.setText("Very Good!")
            midTextstim.draw()
            g.correctTrials = g.correctTrials + 1
            repeat = False
        else:
            midTextstim.color = '#FF0000'
            midTextstim.setText("That is not Correct ")
            midTextstim.draw()
            depth = int(trial[0])
            g.goalErrors = g.goalErrors + 1
            repeat = True

        g.win.flip()
        StimToolLib.just_wait(g.clock, now + 1) # wait 1 seconds


def show_one_slide(slide_path, audio_path = None):
    """
    """
    duration = None
    if audio_path:
        s = sound.Sound(value = audio_path)
        duration = s.getDuration()
        s.play()
    g.win.flip()
    slideStim = visual.ImageStim(g.win, image = slide_path)
    slideStim.draw()
    g.win.flip()
    now = g.clock.getTime()
    StimToolLib.just_wait(g.clock, now + 1) # wait 1 second
    k = event.waitKeys(keyList=[ 
        g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape'],
        clearEvents = True)
    # If it gets to here, than should stop
    if audio_path: s.stop()
    if k[0] == 'escape': raise StimToolLib.QuitException
    return k


def run_try():  

    schedules = [f for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.schedule')]
    if not g.session_params['auto_advance']:
        myDlg = gui.Dlg(title="PlanningTask")
        myDlg.addField('Run Number', choices=schedules, initial=str(g.run_params['run']))
        myDlg.show()  # show dialog and wait for OK or Cancel
        if myDlg.OK:  # then the user pressed OK
            thisInfo = myDlg.data
        else:
            #print 'QUIT!'
            return -1#the user hit cancel so exit 
        g.run_params['run'] = thisInfo[0]
    StimToolLib.general_setup(g)

    schedule_file = os.path.join(os.path.dirname(__file__), g.run_params['run'])
    #param_file = os.path.join(os.path.dirname(__file__),'T1000_DP_Schedule' + str(g.run_params['run']) + '.csv')
    
    #load instruction slides
    #slides = []
    #for i in range(1,6):
    #    slides.append(visual.ImageStim(g.win, image=os.path.join(os.path.dirname(__file__),  'media/Instructions/slide' + str(i) + '.bmp'), pos=[0,0], units='pix'))
    
    ## Set global session handedness if specifed
    try:
        if g.session_params['hand'] == 'left': 
            g.hand = 'left'
    except: pass
    
    
    #g.x = visual.TextStim(g.win, text="+", units='pix', height=25, color=[-1,-1,-1], pos=[0,0], bold=True)
    g.clock = core.Clock()
    start_time = data.getDateStr()
    param_file = g.run_params['run'][0:-9] + '.params' #every .schedule file can (probably should) have a .params file associated with it to specify running parameters (including part of the output filename)
    StimToolLib.get_var_dict_from_file(os.path.join(os.path.dirname(__file__), param_file), g.run_params)
    g.prefix = StimToolLib.generate_prefix(g)
    g.subj_param_file = os.path.join(os.path.dirname(g.prefix), g.session_params['SID'] + '_' + g.run_params['param_file'])
    fileName = os.path.join(g.prefix + '.csv')
    #g.prefix = 'DP-' + g.session_params['SID'] + '-Admin_' + g.session_params['raID'] + '-run_' + str(g.run_params['run']) + '-' + start_time
    #fileName = os.path.join(os.path.dirname(__file__), 'data/' + g.prefix +  '.csv')
    g.output = open(fileName, 'w')
    
    sorted_events = sorted(event_types.items(), key=lambda item: item[1])
    g.output.write('Administrator:,' + g.session_params['admin_id'] + ',Original File Name:,' + fileName + ',Time:,' + start_time + ',Parameter File:,' +  schedule_file + ',Event Codes:,' + str(sorted_events) + ',Trial Types are coded as follows: 8 bits representing [valence neut/neg/pos] [target_orientation H/V] [target_side left/right] [duration .5/1] [valenced_image left/right] [cue_orientation H/V] [cue_side left/right]\n')
    g.output.write('trial_number,trial_type,event_code,absolute_time,response_time,response,result\n')
    StimToolLib.task_start(StimToolLib.IAT_CODE, g)
    instruct_start_time = g.clock.getTime()
    StimToolLib.mark_event(g.output, 'NA', 'NA', event_types['INSTRUCT_ONSET'], instruct_start_time, 'NA', 'NA', 'NA', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
    #StimToolLib.show_title(g.win, g.title)
    #g.output.write('Trial_Type:-1:negative;0:neutral;1:positive,Image,ITI_Onset,ITI_startle,Stimulus_onset,Stimulus_startle,Valence_Rating,Valence_rating_time,Arousal_rating,Arousal_rating_time\n')
    

    # Ask about load
    try:
        if g.run_params['ask_load_question'] == True:
            textStim = visual.TextStim(g.win, text = "Is this Run with the breathing Load?\nYES = PRESS 'y' key\nNO = PRESS 'n' key", units = 'norm', pos = (0,0), height = .07)
            textStim.draw()
            g.win.flip()
            k = event.waitKeys(keyList=[ 'y','Y', 'n','N','escape'])
            if k[0] == 'escape': raise StimToolLib.QuitException
            if k[0] in ['y','Y']:
                StimToolLib.write_var_to_file(g.subj_param_file, 'breathing_load_run', 'YES')
                StimToolLib.mark_event(g.output, 'NA', 'NA', event_types['BREATHING_LOAD'], 'NA', 'NA', 'NA', 'BREATHING_LOAD_RUN=YES', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
            if k[0] in ['n','N']:
                StimToolLib.write_var_to_file(g.subj_param_file, 'breathing_load_run', 'NO')
                StimToolLib.mark_event(g.output, 'NA', 'NA', event_types['BREATHING_LOAD'], 'NA', 'NA', 'NA', 'BREATHING_LOAD_RUN=NO', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])

    except KeyError:
        pass
    StimToolLib.mark_event(g.output, 'NA', 'NA', event_types['INSTRUCT_ONSET'], instruct_start_time, 'NA', 'NA', 'NA', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])
    # Run 
    #StimToolLib.run_instructions(os.path.join(os.path.dirname(__file__), g.run_params['instruction_schedule']), g)
    StimToolLib.run_instructions_keyselect(os.path.join(os.path.dirname(__file__), g.run_params['instruction_schedule']), g)

    

    # Create Stim Objects
    g.topTextstim = visual.TextStim(g.win, text = 'You have 0 moves', units = 'norm', pos = (0,0.6), height = .12)
    g.bottomTextstim = visual.TextStim(g.win, text = 'Press the Right Button to enter your moves', units = 'norm', pos = (0,0.45), height = .08)
    g.topMidTextstim = visual.TextStim(g.win, text = 'Enter your moves now.', units = 'norm', pos = (0,0.45), height = .08)
    g.feedbackstim = visual.TextStim(g.win, text = 'You have won a total of 0 points.', units = 'norm', pos = (0,0), height = .07)

    g.timerstim = visual.TextStim(g.win, text = '', units = 'norm', pos = (0,0.8), height = .15)
    g.fixation = visual.TextStim(g.win, text = '+', units = 'norm', pos = (0,0), height = .3)

    setStates()
    setTransitions()

    ## READ the SCHEDULE FILE
    schedule = open(schedule_file, 'r')
    trials = []

    for idx,line in enumerate(schedule):
        if idx == 0:
            continue
        row = line.replace('\n','').split(',')
        trials.append(row)

    instruct_end_time = g.clock.getTime()
    
    
    

    if 'RP1' in g.run_params['run_id']:
        g.show_transitions = True
        g.show_transitions_value = False

        doFreeTraining(g.run_params['free_duration'])
        
        # Ask if they want to do again
        g.win.flip()

        if g.hand == 'right':
            k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP1_10_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide13.m4a.aiff' )
            )
        else:
            k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP1_10_L.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide13.m4a.aiff' )
            )

        if k[0] == g.session_params[g.run_params['select_1']]: 
            # repeat
            doFreeTraining(60) # reapeat another minute

        return
    
    if 'RP2' in g.run_params['run_id']:
        g.goalErrors = 2
        g.show_transitions = True
        g.show_transitions_values= False
        # Repeat these until participant makes only 1 erors or less

        # Can only make this much error
        g.errorMax = 1

        g.GoalTrainingTries = 1
        # Single Step
        while g.goalErrors > g.errorMax:
            g.goalErrors = 0
            # Shuffle Trials Types
            depth1 = [x for x in trials if x[0] == '1']
            random.shuffle(depth1)

            ## Show Goal Tries
            g.win.flip()
            textStim = visual.TextStim(g.win, text = 'Goal Training - Depth 1 \n\nAttempt #: %i' % g.GoalTrainingTries, units = 'norm', pos = (0,0), height = .07)
            textStim.draw()
            g.win.flip()
            now = g.clock.getTime()
            StimToolLib.just_wait(g.clock, now + 3) 
            
            doGoalTraining(depth1)

            if g.goalErrors > g.errorMax:
                show_one_slide( os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','REPEAT_RIGHT.JPG' ),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide18.m4a.aiff' )
                )
                g.GoalTrainingTries += 1
                
        StimToolLib.write_var_to_file(g.subj_param_file, 'goal_training_depth1_tries', g.GoalTrainingTries)
        # Double Step
        g.win.flip()
        now = g.clock.getTime()
        textStim = visual.TextStim(g.win, text = 'Great Job!\nNow we will try with 2 moves!', units = 'norm', pos = (0,0), height = .07)
        textStim.draw()
        g.win.flip()
        StimToolLib.just_wait(g.clock, now + 5) 
        g.GoalTrainingTries = 1
        
        g.goalErrors = 2
        g.show_transitions = True
        while g.goalErrors > g.errorMax:
            g.goalErrors = 0
            depth2 = [x for x in trials if x[0] == '2']
            random.shuffle(depth2)

            ## Show Goal Tries
            g.win.flip()
            textStim = visual.TextStim(g.win, text = 'Goal Training - Depth 2 \n\nAttempt #: %i' % g.GoalTrainingTries, units = 'norm', pos = (0,0), height = .07)
            textStim.draw()
            g.win.flip()
            now = g.clock.getTime()
            StimToolLib.just_wait(g.clock, now + 3) 

            doGoalTraining(depth2)

            if g.goalErrors > g.errorMax:
                show_one_slide( os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','REPEAT_RIGHT.JPG' ),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide18.m4a.aiff' )
                )
                g.GoalTrainingTries += 1

        StimToolLib.write_var_to_file(g.subj_param_file, 'goal_training_depth2_tries', g.GoalTrainingTries)

        # Triple Step
        g.win.flip()
        now = g.clock.getTime()
        textStim = visual.TextStim(g.win, text = 'Great Job!\nNow we will try with 3 moves!', units = 'norm', pos = (0,0), height = .07)
        textStim.draw()
        g.win.flip()
        StimToolLib.just_wait(g.clock, now + 5) 
        

        g.goalErrors = 2
        g.GoalTrainingTries = 1
        # Need to all the trials Right!
        while g.goalErrors > g.errorMax:
            g.goalErrors = 0
            depth3 = [x for x in trials if  x[0] == '3']
            random.shuffle(depth3)

            ## Show Goal Tries
            g.win.flip()
            textStim = visual.TextStim(g.win, text = 'Goal Training - Depth 3 \n\nAttempt #: %i' % g.GoalTrainingTries, units = 'norm', pos = (0,0), height = .07)
            textStim.draw()
            g.win.flip()
            now = g.clock.getTime()
            StimToolLib.just_wait(g.clock, now + 3) 


            doGoalTraining(depth3)

            if g.goalErrors > g.errorMax:
                # g.win.flip()
                # now = g.clock.getTime()
                # textStim = visual.TextStim(g.win, text = 'You have made more than 1 error in a row. :(\n We wil repeat again from the top.', units = 'norm', pos = (0,0), height = .07)
                # textStim.draw()
                # g.win.flip()
                # StimToolLib.just_wait(g.clock, now + 3) # wait 1 seconds
                show_one_slide( os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','REPEAT_RIGHT.JPG' ),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide18.m4a.aiff' )
                )
                g.GoalTrainingTries += 1
        
        StimToolLib.write_var_to_file(g.subj_param_file, 'goal_training_depth3_tries', g.GoalTrainingTries)

        # Show Encoruaging Slide
        show_one_slide( os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','PROGRESS_RIGHT.JPG' ),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide19.m4a.aiff' )
                )

        g.win.flip()
        slideStim = visual.ImageStim(g.win, image = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','PROGRESS_RIGHT.JPG' ) )
        slideStim.draw()
        g.win.flip()
        now = g.clock.getTime()
        StimToolLib.just_wait(g.clock, now + 1) # wait 1 second
        event.clearEvents() # Clear Events in the event buffer
        k = event.waitKeys(keyList=[ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape'])
        if k[0] == 'escape': raise StimToolLib.QuitException
        return
        
    if 'RP3' in g.run_params['run_id']:
        g.show_transitions = True
        g.show_transitions_value = True

        doFreeTraining(g.run_params['free_duration'])
        
        g.win.flip()
        if g.hand == 'right':
            k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP1_10_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide13.m4a.aiff' )
            )
        else:
            k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','RP1_10_L.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide13.m4a.aiff' )
            )

        if k[0] == g.session_params[g.run_params['select_1']]: 
            # repeat
            doFreeTraining(60) # reapeat another minute
        
        return

    if 'RP4' in g.run_params['run_id']:
        g.goalErrors = 2
        # Single Step
        g.PathTestTries = 1
        while g.goalErrors > 1:
            g.goalErrors = 0
            # Shuffle Trials Types
            depth1 = [x for x in trials if x[0] == '1']
            random.shuffle(depth1)

            g.win.flip()
            textStim = visual.TextStim(g.win, text = 'Path Test \n\nAttempt #: %i' % g.PathTestTries, units = 'norm', pos = (0,0), height = .07)
            textStim.draw()
            g.win.flip()
            now = g.clock.getTime()
            StimToolLib.just_wait(g.clock, now + 3) 
            
            doPathTest(depth1)

            if g.goalErrors > 1:
                show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','REPEAT_POINTS_RIGHT.JPG' ) )
                g.PathTestTries += 1
        StimToolLib.write_var_to_file(g.subj_param_file, 'path_test_tries', g.PathTestTries)
        return

    if 'RP5' in g.run_params['run_id']:
        g.ideal_trial_start = g.clock.getTime()
        doTaskTraining(trials)
        return

    # Example Trials

    if g.run_params['show_example'] == True:

        k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','R1_01_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide32.m4a.aiff' )
            )

        
        example_trials = [
            [4,2],
            [4,1],
            [5,6],
            [3,3],
            [5,5],
            [3,4]
        ]
        g.trial = 0
        
        g.ideal_trial_start = g.clock.getTime()
        g.trial = 0
        g.points = 0
        for trial in example_trials:
            g.win.flip() # clear window
            start_state = int(trial[1])
            depth = int(trial[0])
            g.trial_type = depth
            duration = 3 # Must enter moves within 3 seconds
            #print trial
            doTaskTrial(start_state, depth,duration, True) # Do Single Trial
            g.trial = g.trial + 1

        if not 'BK_Pilot' in schedule_file:
            k = show_one_slide(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'PlaningInstructions','R1_1_R.JPG' ),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'instructions', 'instruction_audio','slide33.m4a.aiff' )
            )
        else:
            textStim = visual.TextStim(g.win, text = "Let's Begin! \n Press the Right Button when you are ready.", units = 'norm', pos = (0,0), height = .07)
            textStim.draw()
            g.win.flip()
            k = event.waitKeys(keyList=[ g.session_params[g.run_params['select_1']],  g.session_params[g.run_params['select_2']], 'escape'])
            if k[0] == 'escape': raise StimToolLib.QuitException
            if k[0] == g.session_params[g.run_params['select_1']]: pass

    if g.session_params['scan'] and ('RP6' not in g.run_params['run_id']):
        StimToolLib.wait_scan_start(g.win)
    else:
        StimToolLib.wait_start(g.win)

    
    
    # Wait 8 seconds before start
    g.win.flip()
    g.fixation.draw()
    g.win.flip()

    now = g.clock.getTime()
    
    g.ideal_trial_start = g.clock.getTime()
    g.ideal_trial_start = g.ideal_trial_start + 8
    StimToolLib.just_wait(g.clock, g.ideal_trial_start)

    StimToolLib.mark_event(g.output, 'NA', 'NA', event_types['TASK_ONSET'], now, 'NA', 'NA', 'NA', g.session_params['signal_parallel'], g.session_params['parallel_port_address'])

    g.trial = 0
    g.points = 0
    for trial in trials:
        g.win.flip() # clear window
        start_state = int(trial[1])
        depth = int(trial[0])
        g.trial_type = depth
        duration = 2.5
        #print trial
        doTaskTrial(start_state, depth,duration, True) # Do Single Trial
        g.trial = g.trial + 1

    ## Show Points
    g.win.flip()
    textStim = visual.TextStim(g.win, text = 'You have won %i cents.' % g.points, units = 'norm', pos = (0,0), height = .07)
    textStim.draw()
    g.win.flip()
    now = g.clock.getTime()
    StimToolLib.just_wait(g.clock, now + 3) 

    # save points
    StimToolLib.write_var_to_file(g.subj_param_file, 'total_points', g.points)
