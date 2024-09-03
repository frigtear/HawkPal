import requests
import json 
from tkinter import * 
import tkinter as tk
from tkinter import ttk
import webbrowser
from datetime import datetime
import atexit

with open("config.json", "r") as f:
    config = json.load(f)

url = config["url"]
icon_url = config["icon_url"]
canvas_url = config["canvas_url"]
token = config["token"]
limit = config["limit"]


auth = {'Authorization':'Bearer ' + token}

title = 'Hawk-Launch'
root = tk.Tk()
tab_window = None
style = ttk.Style()
style.configure("TButton", foreground="yellow")
style.configure('TLabel', foreground='yellow')


ttk.Label(root,text="Classes:").grid(row=0,column=0)
ttk.Label(root,text="Tabs1").grid(row=0,column=1)
ttk.Label(root,text="Tabs2").grid(row=0,column=2)
ttk.Label(root,text="Tabs3").grid(row=0,column=3)


pin_button_list = []
unpin_button_list = []

with open('pins.json','r') as f:
    course_pins = json.load(f)

# Automatically sets settings for tk.Toplevel
def configure_tl(toplevel,title='',geometry='1000x500',resizable=False):
    toplevel.resizable(resizable,resizable)
    toplevel.geometry(geometry)
    toplevel.title(title)


def save_data():
    with open('pins.json','w') as f:
        json.dump(course_pins,f)

atexit.register(save_data)


def pin(course,tab,row):
    id = str(course['id'])
    course_pins[id].append(tab)


def unpin(course,tab,row):
    id = str(course['id'])
    course_pins[id].remove(tab)


def display_error_window(message):
    err_window = tk.Toplevel(root)
    configure_tl(err_window,title="Error!",geometry='200x200')
    ttk.Label(err_window,text=message).pack()
    ttk.Button(err_window, text="Click here to quit. Email rsonnenschein@uiowa if this error persists",command=quit)


# Checks if requests.response object returned valid json
def get_json(response):
    if response.status_code == 200:
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            display_error_window("There was a problem retrieving class information")
    else:
        display_error_window("There was an issue with getting data")


configure_tl(root,title="Hawk-Launch",geometry="1500x500")

# We include the course tabs to avoid unnecessary requests
course_params = {'enrollment_type':'student',
                 'enrollment_state':'active',
                 'exclude_blueprint_course':True, 
                 'include':['tabs'],
                   }

courses_response = requests.get(url=url + '/courses',headers=auth,params=course_params)
course_data = get_json(courses_response)
# Conditional in following comprehension filters out unwanted courses 
course_data = [course for course in course_data if not ' - ' in course['name']] 

def display_submodules(module,items):
    submod_window = tk.Toplevel()
    configure_tl(submod_window, title=module['name'])
    for item in items:
        try:
            url = item['html_url']
            url = url.replace(canvas_url,icon_url)
            ttk.Button(submod_window, text=item['title'],command=lambda url=url : webbrowser.open(url)).pack()
        except KeyError:
            pass
def display_modules(course,tab):
    #  /api/v1/courses/:course_id/students/submissions
    modules_window = tk.Toplevel()
    configure_tl(modules_window,title=tab['label'])

    modules_params = {'include':['items']}
    modules_url = url + '/courses/' +str(course['id']) + '/modules'
    module_response = requests.get(url=modules_url, headers=auth,params=modules_params)
    module_data = get_json(module_response)
    for module in module_data:
        items = module['items']
        ttk.Button(modules_window,text=module['name'],command=lambda module=module,items=items : display_submodules(module,items)).pack()

def display_assignments(course,tab):
    # If ctrl is held down while button clicked, immediatly open assignment tab
    event_data = root.event_info
    as_window = tk.Toplevel()
    configure_tl(as_window,title=tab['label'])
    # GET /api/v1/courses/:course_id/assignments
    # Order assignment list by most recently due
    assignments_params = {'order_by':'due_at'}
    assignments_url = url + '/courses/' + str(course['id']) + '/assignments'
    assignments_response = requests.get(url=assignments_url,headers=auth,params=assignments_params)
    assignments = get_json(assignments_response)
    #Limit the displayed assignments to the 20 most recently due
    if len(assignments) > 20:
        assignments = assignments[:limit]
    for i,assignment in enumerate(assignments[::-1]):
        as_url = assignment['html_url']
        as_url = as_url.replace(canvas_url,icon_url)
        date = datetime.strptime(assignment['due_at'],'%Y-%m-%dT%H:%M:%S%z')
        latin = 'PM' if date.hour > 12 else 'AM'
        hour = date.hour - 12 if date.hour > 12 else date.hour
        due_date = 'due ' + str(date.month) + '/' +  str(date.day) + ' at ' + str(hour) + (':') + str(date.minute) + latin
        ttk.Label(as_window,text=due_date).grid(row=i,column=0,sticky='e')
        ttk.Button(as_window,text=assignment['name'],command= lambda as_url=as_url : webbrowser.open(as_url)).grid(row=i,column=1,columnspan=2,sticky='w')


# Maps tab button clicked to corresponding display function    
def navigate(course,tab):
    label = tab['label']
    if label == 'Modules':
        display_modules(course,tab)
    elif label == 'Assignments':
        display_assignments(course,tab)
    else:
        webbrowser.open(icon_url + tab['html_url'])

#Executes when course widget clicked, displays course tab window
def display_course_tabs(course):
    global tab_window
    id = str(course['id'])
    if tab_window is None or not(tab_window.winfo_exists()):
        tab_window = tk.Toplevel(root)
        configure_tl(tab_window,course['name'])
        for row,tab in enumerate(course['tabs']):
            ttk.Button(tab_window,text=tab['label'],command= lambda course=course,tab=tab : navigate(course,tab)).grid(row=row+1,column=0)
            if not tab in course_pins[id]:
                pin_button = ttk.Button(tab_window,text='Pin',command=lambda course=course,tab=tab : pin(course,tab,row+1))
                pin_button_list.append(pin_button)
                pin_button.grid(row=row+1,column=1)
            else:
                unpin_button = ttk.Button(tab_window,text='Unpin',command=lambda course=course,tab=tab : unpin(course,tab,row+1))
                unpin_button_list.append(unpin_button)
                unpin_button.grid(row=row + 1, column=1)


for row,course in enumerate(course_data):
    id = str(course['id'])
    home_url = icon_url + '/courses/' + str(course['id'])
    try:
        name_f = course['name']
        i = name_f.index(':')
    except ValueError:
        pass
   
    name_s = name_f[:i]
    as_tab = [tab for tab in course['tabs'] if tab['label'] == 'Assignments']
    mod_tab = [tab for tab in course['tabs'] if tab['label'] == 'Modules']
    pinned_tabs = []
    #print(course_pins)
    try:
        pinned_tabs = course_pins[id]
    except:
        if as_tab and mod_tab:
            pinned_tabs.append(as_tab[0])
            pinned_tabs.append(mod_tab[0])
            course_pins[id] = pinned_tabs
        elif as_tab and not mod_tab:
            pinned_tabs.append(as_tab[0])
            course_pins[id] = pinned_tabs
        elif mod_tab and not as_tab:
            pinned_tabs.append(mod_tab[0])
            course_pins[id] = pinned_tabs
        else:
            course_pins[id] = []

    ttk.Button(root,text=name_f,command=lambda course=course : display_course_tabs(course)).grid(row=row+1,column=0)
    ttk.Button(root,text=name_s + ' Home',command=lambda home_url=home_url : webbrowser.open(home_url)).grid(row=row+1,column=1)
    pinned_tabs = course_pins[id]
    if id in course_pins.keys():
        for column,tab in enumerate(pinned_tabs):
            ttk.Button(root,text=name_s + " " + tab['label'],command=lambda course=course,tab = tab : navigate(course,tab)).grid(row=row+1,column=column+2)

root.mainloop()
