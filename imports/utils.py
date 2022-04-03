import os
import io
import codecs
import sys
import sublime
import sublime_plugin
import subprocess
import time
import platform
from subprocess import Popen, PIPE, STDOUT
from distutils.version import LooseVersion, StrictVersion
from os import path

plugin_dir = path.dirname(path.dirname(__file__))
plugin_name = path.basename(plugin_dir)
new_file_path = path.join(path.dirname(plugin_dir), 'User', 'cs-script', 'new_script.cs')
bin_dest = path.join(path.dirname(plugin_dir), 'User', 'cs-script'+ os.sep)
bin_src = path.join(plugin_dir, 'bin')

def settings():
    return sublime.load_settings("cs-script.sublime-settings")

def save_settings():
    sublime.save_settings("cs-script.sublime-settings")

# -----------------
def is_win():
    return sublime.platform() == 'windows'
    
def is_linux():
    return os.name == 'posix' and platform.system() == 'Linux'

def is_mac():
    return os.name == 'posix' and platform.system() == 'Darwin'
    
def to_args(args):
    # excellent discussion about why popen+shell doesn't work on Linux
    # http://stackoverflow.com/questions/1253122/why-does-subprocess-popen-with-shell-true-work-differently-on-linux-vs-windows
        
    if os.name == 'posix' and platform.system() == 'Linux': 
        result = ''
        for arg in args:
            result = result + '"'+arg+'" '
        return [result.rstrip()]
    return args

def execute(args, onLineOut, onStart=None):
    try:
        # excellent discussion about why popen+shell doesn't work on Linux
        # http://stackoverflow.com/questions/1253122/why-does-subprocess-popen-with-shell-true-work-differently-on-linux-vs-windows
        if os.name == 'posix' and platform.system() == 'Linux': 
            result = ''
            for arg in args:
                result = result + '"'+arg+'" '
            all_args = [result.rstrip()]
        else:
            all_args = args

        p = subprocess.Popen(all_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        # out, error_msg = p.communicate() # to get bytes
        
        if onStart: 
            onStart(p)

        if onLineOut:
            for line in io.TextIOWrapper(p.stdout, encoding="utf-8"):
                onLineOut(line.strip())

            for line in io.TextIOWrapper(p.stderr, encoding="utf-8"):
                onLineOut(line.strip())

        p.wait()
        time.sleep(0.3)
                
    except Exception as e:
        print(e)
        return None

def execute_in_terminal(args):
    try:
        
        all_args = ''
        for arg in args:
            all_args = all_args + '"'+arg+'" '
        all_args = all_args.rstrip()

        if os.name == 'nt':
            os.system(all_args)
        else:
            # Linux and Mac
            env = os.environ.copy()


            command = "bash -c \" {0} ; exec bash\"".format(all_args)
            args =[TerminalSelector.get(), '-e', command]

            subprocess.Popen(args)



    except Exception as e:
        print(e)
        return None
# =================================================================================
# Plugin runtime configuration
# =================================================================================
class Runtime():
    cscs_path = None
    syntaxer_path = None
    min_compatible_css_version = '4.4.2.0'
    min_compatible_dotnet_version = '6.0.0'
    max_compatible_dotnet_version = '7.0.0'
    syntaxer_port = None
    pluginVersion = None
    new_deployment = False
    is_dotnet_core = True

    def integrate_with_choco():
        print(path.join(os.environ["ChocolateyInstall"],'lib','cs-script', 'tools', 'cscs.dll'))
        print(path.join(os.environ["ChocolateyInstall"],'lib','cs-syntaxer', 'tools', 'syntaxer.dll'))


    def init(version, new_deployment):

        Runtime.pluginVersion = version
        Runtime.new_deployment = new_deployment

        Runtime.syntaxer_port = settings().get('syntaxer_port')
        Runtime.syntaxer_path = settings().get('syntaxer_path')
        Runtime.cscs_path = settings().get('cscs_path')

        version_envar_pattern = '$PACKAGE_VERSION'
        if is_win():
            version_envar_pattern = '%PACKAGE_VERSION%'

        # cannot use default value with get(...) as it is not triggered if the config value is null but only absent
        if not Runtime.syntaxer_path: Runtime.syntaxer_path = path.join(bin_dest, 'syntaxer_v'+version, 'syntaxer.dll')
        if not Runtime.cscs_path: Runtime.cscs_path = path.join(bin_dest, 'cs-script_v'+version, 'cscs.dll')
        if not Runtime.syntaxer_port: Runtime.syntaxer_port = 18000
        
        Runtime.syntaxer_path = os.path.expandvars(Runtime.syntaxer_path)
        Runtime.cscs_path = os.path.expandvars(Runtime.cscs_path)
    
        # if cscs_path is not set we can try to discover local deployment. if none found then set it to the default        
        # css_root = os.environ["CSSCRIPT_ROOT"]
        # if  cscs_path == None and path.exists(css_root):
        #     cscs_path = path.join(css_root, "cscs.dll");
            
        # if cscs_path == None:
        #     Runtime.cscs_path = path.join(bin_dest, 'cs-script_v'+version, 'cscs.dll')
        # elif cscs_path:
        #     Runtime.cscs_path = os.path.abspath(os.path.expandvars(cscs_path))

        if Runtime.cscs_path:
            settings().set('cscs_path', Runtime.cscs_path.replace('cs-script_v'+version, 'cs-script_v'+version_envar_pattern))
            settings().set('syntaxer_path', Runtime.syntaxer_path.replace('syntaxer_v'+version, 'syntaxer_v'+version_envar_pattern))
            settings().set('syntaxer_port', Runtime.syntaxer_port)
            save_settings()
                
# =================================================================================
# Plugin utils
# =================================================================================
def get_dotnet_version():
    try:
        
        def onOutput(line): 
            global result 
            result =  line.strip()

        execute(['dotnet', "--version"], onOutput)

        return result

    except Exception as e:
        print(e)
        return None
# -----------------
def get_css_version():
    try:

        def onOutput(line): 
            global result 
            result =  line.strip()

        execute(['dotnet', Runtime.cscs_path, "--version"], onOutput)

        return result    

    except Exception as e:
        print(e)
        return None
# -----------------
def get_syntaxer_version():
    try:
        def onOutput(line): 
            global result 
            # 'CS-Syntaxer v3.1.0.0'    #first line only
            if result == None:
                result =  line.split(' ', 1)[-1][1:]

        execute(['dotnet', Runtime.syntaxer_path], onOutput)

        return result    

    except Exception as e:
        print(e)
        return None
# =================================================================================
# Sublime utils
# =================================================================================


def which(file):
    try:
        out_file = os.path.join(plugin_dir, "..", "User", 'which.txt')

        with open(out_file, "w") as f:
            popen_redirect_tofile(['which', file], f).wait()

        output = None
        with open(out_file, "r") as f:
            output =  f.read().strip()

        if os.path.exists(out_file):
            os.remove(out_file)

        return output

    except Exception as e:
        print('Cannot execute "which" for '+file+'.', e)
# -----------------
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
    # already does it. What is actually quite annoying as no scrolling control from plugin is possible.
    # view = get_output_view(name)
    # view.show(view.size()-1)
# -----------------
def output_view_scrollup(name):
    view = get_output_view(name)
    view.show(view.size()-1)
# -----------------
def output_view_clear(name):
    view = get_output_view(name) # to ensure it's created
    view.run_command('select_all')
    view.run_command('right_delete')
    view.show(view.size()-1) # ensure reset of the scrollbar position (it is important)
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
is_deployment_problem_reported= False

def check_environment(force_show_doc):

    current_dotnet_version = get_dotnet_version()
    current_css_version = get_css_version() 
    current_syntaxer_version = get_syntaxer_version() 

    # print('current_dotnet_version: '+current_dotnet_version)
    # print('current_css_version: '+current_css_version)
    # print('current_syntaxer_version: '+current_syntaxer_version)
    # print('Runtime.min_compatible_dotnet_version: '+Runtime.min_compatible_dotnet_version)
    # print('Runtime.max_compatible_dotnet_version: '+Runtime.max_compatible_dotnet_version)
        
    error = None
    if current_dotnet_version == None:
        error = ".NET is not found\n"

    elif LooseVersion(current_dotnet_version) <  LooseVersion(Runtime.min_compatible_dotnet_version) \
         or LooseVersion(current_dotnet_version) >=  LooseVersion(Runtime.max_compatible_dotnet_version):
        error = "Installed .NET version is incompatible.\n"

    if current_css_version == None:
        error = (error if error else '') + "CS-Script is not found.\n"
    
    if current_syntaxer_version == None:
        error = (error if error else '') + "Syntaxer is not found.\n"

    report = ''    

    if error:
        report = '*************** CS-Script ******************\n' +\
                'ERROR: \n' + error +\
                '\nEnvironment requirements and setup instructions:\n' +\
                '  https://github.com/oleg-shilo/cs-script/wiki/CLI-Environment-Specification\n' +\
                '**********************************************'        
        print(report)
    else:
        report = '*************** CS-Script ******************\n'\
                 '.NET:      v' + str(current_dotnet_version) + '\n'\
                 'CS-Script: v' + str(current_css_version) + '\n'\
                 'Syntaxer:  v' + str(current_syntaxer_version) + '\n'\
                 '---\n'\
                 'CS-Script (script engine): ' + Runtime.cscs_path + '\n'\
                 'Syntaxer (C# syntax server): ' + Runtime.syntaxer_path + '\n'\
                 '---\n'\
                 '\n'\
                 '\n'\
                 'Environment requirements and setup instructions:\n'\
                 '  https://github.com/oleg-shilo/cs-script/wiki/CLI-Environment-Specification\n'\
                 '\n'\
                 'Use "right-click > CS-Script > Settings > Plugin Config" if you need to change'\
                 ' the location of the integrated CS-Script engine and syntaxer\n'\
                 '**********************************************'


    if force_show_doc or Runtime.new_deployment:
        deployment_info = os.path.join(plugin_dir, 'deployment.md')
        with open(deployment_info, "w", encoding="utf-8") as f: f.write(report)
        sublime.active_window().open_file(deployment_info)

# -----------------
def show_console():
    sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": False})
# -----------------
def is_csharp(view):
    file_name = view.file_name()
    if  file_name:
        return file_name.lower().endswith(".cs") or file_name.lower().endswith(".csx")
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
item_boxed_prefix = '  ├─ '
last_item_boxed_prefix = '  └─ '
def navigate_to_file_ref(reference):
    # e:\script.cs(20,7): error CS1002: ; expected
    # file: e:\script.cs
    print('navigating........')
    if reference.startswith('file:'):
        reference = reference.replace('file:', '').strip()

    if reference.startswith(item_boxed_prefix):
        reference = reference.replace(item_boxed_prefix, '').strip()
    if reference.startswith(last_item_boxed_prefix):
        reference = reference.replace(last_item_boxed_prefix, '').strip()

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

