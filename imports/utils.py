import os
import io
import codecs
import sys
import sublime
import sublime_plugin
import subprocess
from subprocess import Popen, PIPE, STDOUT
from os import path

plugin_dir = path.dirname(path.dirname(__file__))

# =================================================================================
# Sublime utils
# =================================================================================
def get_output_view(name): 
    view = sublime.active_window().find_output_panel(name)
    if not view:
        view = sublime.active_window().create_output_panel(name)
        view.assign_syntax('Packages/C#/Build.tmLanguage')
        # view.assign_syntax('Packages/Batch File/Batch File.tmLanguage')
        # view.assign_syntax('Packages/Text/Plain text.tmLanguage')
    return view
# -----------------
def output_view_show(name): 
    view = get_output_view(name) # to ensure it's created
    sublime.active_window().run_command("show_panel", {"panel": "output."+name})
# -----------------
def output_view_hide(name): 
    view = get_output_view(name) # to ensure it's created
    sublime.active_window().run_command("hide_panel", {"panel": "output."+name})
# -----------------
def output_view_toggle(name): 
    view = get_output_view(name) # to ensure it's created
    sublime.active_window().run_command("show_panel", {"panel": "output."+name, "toggle": True})
# -----------------
def output_view_write_line(name, text, move_caret_to_end=False):
    view = get_output_view(name) # to ensure it's created
    view.run_command('append', {'characters': text + '\n'})
    if move_caret_to_end:
        view.sel().clear()
        view.sel().add(sublime.Region(view.size(), view.size()))
# -----------------
def output_view_append(name, output):
    output_view_write_line(name, output.rstrip())
    
    # no need to scroll as "view.run_command('append'..." of output_view_write_line
    # already does it. What is actually quite annoing as no scrolling contron from plugin is possible.
    # view = get_output_view(name) 
    # view.show(view.size()-1)
# -----------------
def output_view_clear(name):
    view = get_output_view(name) # to ensure it's created
    view.run_command('select_all')
    view.run_command('right_delete') 
# -----------------
def is_output_view_visible(name):
    view = sublime.active_window().get_output_panel("output."+name)
    if view.window():
        return True
    else:
        return False
# -----------------
def extract_location(reference):
    # e:\script.cs(20,7): error CS1002: ; expected
    # file: e:\script.cs
    try:    
        if reference.startswith('file:'):
            reference = reference.replace('file:', '').strip()

        if reference.startswith('csscript.CompilerException: '):
            reference = reference.replace('csscript.CompilerException: ', '').strip()

        end = reference.find('):')
        if end != -1:
            context = reference[end+2:]
            reference = reference[:end]
            pos = reference.rfind('(') 
            if pos != -1:
                location = reference[pos+1:].split(',')

                file = reference[:pos]
                line = int(location[0])
                column = int(location[1])
                file, line, column = normalize(file, line, column)
                return (file, line, column, context)

        elif os.path.exists(reference):
            return (reference, -1, -1, None)
    except:
        return None
# -----------------
def find_file_view(file_name):
    is_win = (sublime.platform() == 'windows')

    pattern = os.path.normpath(file_name)

    if is_win:
        pattern = pattern.lower()

    for view in sublime.active_window().views():
        viewPath = os.path.normpath(view.file_name())

        if is_win:
            viewPath = viewPath.lower()
            
        if pattern == viewPath:
            return view
    return None
# -----------------
def active_primary_view():
    for view in sublime.active_window().views():
        if view.is_primary():
            return view
    return None
# -----------------
def is_output_panel(view):
    
    # return view == sublime.active_window().active_panel() # not reliable
    if view == sublime.active_window().find_output_panel('exec'):
        return True
        
    return view.file_name() == None and view.name() == ''

# -----------------
def get_saved_doc(view, location = -1):
    if location == -1:
        if len(view.sel()) > 0:
            location = view.sel()[0].begin()
            
    location = to_file_pos(view, location)
    as_temp_file = view.is_dirty()
    if as_temp_file:
        current_file = save_as_temp(view)
        return (current_file, location, as_temp_file)
    else:
        return (view.file_name(), location, as_temp_file)
# -----------------
def show_console(): 
    sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": False})
# -----------------
def is_csharp(view):
    file_name = view.file_name()
    if  file_name:
        return file_name.lower().endswith(".cs")
    return False  
# -----------------
def clear_console(): 
    print('\n\n\n\n\n\n\n') 
# -----------------
def to_text_pos(text, location):
    # For text position ST always ignores '\r' while file can have it 
    # May need to be reworked to support Mac
    pos = 0
    count = 0
    while pos != -1:
        pos = text.find('\r', pos)
        if pos != -1 and pos < location:
            pos=pos+1
            count = count + 1
        else:
            break

    return location-count
# -----------------
def to_file_pos(view, location): 
    pos = location 
    if view.line_endings() == 'Windows':
        (row,col) = view.rowcol(location) #on win every line break has extra character which sublime doesn't count 
        pos += row
    return pos
# -----------------
def get_text(view): 
    text = view.substr(sublime.Region(0, view.size()))
    if view.line_endings() == 'Windows':
        text = text.replace('\n', '\r\n') #Roslyn on Win expects /r/n but Sublime on Win still operates with /n only 
    return text
# -----------------
def save_as_temp(view):
    tmpfile_name = view.file_name()+'.tmp'
    tmpfile = codecs.open(tmpfile_name, "w", "utf-8")
    text = get_text(view)
    tmpfile.write(text)
    tmpfile.flush()
    tmpfile.close()
    return tmpfile_name
# -----------------
def is_valid_selection(view):
    region  = view.sel()[0]

    if len(view.sel()) > 1:
        return False
    elif not region.empty():
        return False
    else:    
        return True        
# -----------------
def normalize(file, line, column): 
    if file.endswith(".g.csx") or file.endswith(".g.cs") and "CSSCRIPT\\Cache" in file:
        dir = os.path.dirname(file)
        info_file = os.path.join(dir, "css_info.txt")
        if os.path.exists(info_file):
            with codecs.open(info_file, "r") as f:
                lines = f.read().split('\n')
            if len(lines) > 1 and os.path.exists(lines[1]):
                logical_file = os.path.join(lines[1], os.path.basename(file).replace(".g.csx", ".csx").replace(".g.cs", ".cs"))
                if os.path.exists(logical_file):

                    code = ''
                    with codecs.open(file, "r") as f:
                        code = f.read()

                    pos = code.find("///CS-Script auto-class generation");
                    if pos != -1:
                        injectedLineNumber = len(code[:pos].split('\n')) - 1;
                        if injectedLineNumber <= line:
                            line = line - 1; # a single line is always injected

                    file = logical_file

    return (file, line, column)            
# -----------------
# For TerminalSelector the all credit goes to "Terminal" plugin: https://packagecontrol.io/packages/Terminal
# Copyright (c) 2011 Will Bond
class TerminalSelector():
    default = None

    def get():
        if TerminalSelector.default:
            return TerminalSelector.default

        default = None

        if sys.platform == 'darwin':
            package_dir = os.path.join(sublime.packages_path(), "cs-script")
            default = os.path.join(package_dir, 'Terminal.sh')
            if not os.access(default, os.X_OK):
                os.chmod(default, 0o755)

        else:
            ps = 'ps -eo comm | grep -E "gnome-session|ksmserver|' + \
                'xfce4-session|lxsession|mate-panel|cinnamon-sessio" | grep -v grep'
            wm = [x.replace("\n", '') for x in os.popen(ps)]
            if wm:
                if 'gnome-session' in wm[0] or wm[0] == 'cinnamon-sessio':
                    default = 'gnome-terminal'
                elif wm[0] == 'xfce4-session':
                    default = 'xfce4-terminal'
                elif wm[0] == 'ksmserver':
                    default = 'konsole'
                elif wm[0] == 'lxsession':
                    default = 'lxterminal'
                elif wm[0] == 'mate-panel':
                    default = 'mate-terminal'
            if not default:
                default = 'xterm'

        TerminalSelector.default = default
        return default
# -----------------
def navigate_to_file_ref(reference):
    # e:\script.cs(20,7): error CS1002: ; expected
    # file: e:\script.cs
    print('navigating........')
    if reference.startswith('file:'):
        reference = reference.replace('file:', '').strip()

    if reference.startswith('csscript.CompilerException: '):
        reference = reference.replace('csscript.CompilerException: ', '').strip()

    end = reference.find('):')
    if end != -1:
        reference = reference[:end]
        pos = reference.rfind('(') 
        if pos != -1:
            location = reference[pos+1:].split(',')

            file = reference[:pos]
            line = int(location[0])
            column = int(location[1])
            
            file, line, column = normalize(file, line, column)

            sublime.active_window().open_file('{0}:{1}:{2}'.format(file, line, column), sublime.ENCODED_POSITION)
            if os.path.exists(file):
                view = sublime.active_window().find_open_file(file)
                if view:
                    point = view.text_point(line-1, column-1)
                    new_selection = view.word(point)
                    view.sel().clear()
                    view.sel().add(new_selection)
    else:
        file = reference
        if os.path.exists(file):
            sublime.active_window().open_file(file)
        else:
            print('File ', file, 'doesn''t exist')


# ===============================================
class busy_indicator():
    count = 0
    active = False
    prompt = 'Busy'
    delay = 70
    up = True
    # -----------
    def show(prompt="Busy"):
        busy_indicator.prompt = prompt
        busy_indicator.active = True
        sublime.active_window().active_view().show_popup(busy_indicator.prompt+'...')
        sublime.set_timeout_async(busy_indicator.do, 1)
    # -----------
    def do():
        if busy_indicator.active:
            incrment = 1 if busy_indicator.up else -1;
            busy_indicator.count = busy_indicator.count + incrment
            if busy_indicator.up:
                if busy_indicator.count > 5:
                    busy_indicator.count = 4
                    busy_indicator.up = False
            else:
                if busy_indicator.count < 0:
                    busy_indicator.count = 1
                    busy_indicator.up = True

            msg = busy_indicator.prompt
            for i in range(busy_indicator.count):
                msg = msg+'.'
            sublime.status_message(msg)
            # sublime.active_window().active_view().update_popup(msg)
            sublime.set_timeout_async(busy_indicator.do, busy_indicator.delay)
        else:
            sublime.status_message('')
    # -----------
    def hide():
        busy_indicator.active = False
        sublime.status_message('')
        sublime.active_window().active_view().hide_popup()

