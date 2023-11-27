import os
import io
import codecs
import sys
import html
import time
import sublime
import sublime_plugin
import subprocess
import shutil
import signal
import threading
from subprocess import Popen, PIPE, STDOUT
from os import path

# https://www.sublimetext.com/docs/1/api-reference

version = '1.3.3'  # build 0
os.environ["PACKAGE_VERSION"] = version

from .imports.utils import * # should be imported after environ["PACKAGE_VERSION"] is set
new_deployment = (not os.path.isdir(path.join(bin_dest+'cs-script_v'+version)))


# -----------------
bash_string = r'''#!/bin/bash
dotnet /home/user/.config/sublime-text/Packages/User/cs-script/cs-script_v1.2.3/cscs.dll -help > /home/user/.config/sublime-text/Packages/User/cs-script/help.txt 
'''
# output = subprocess.check_output(bash_string, shell=True, executable='/bin/bash')
# -----------------

if sys.version_info < (3, 3): raise RuntimeError('CS-Script.ST3 works with Sublime Text 3 only')

# ------------------------- 
def is_script_file(file):
    return file.endswith(".cs") or file.endswith(".csx")

def settings():
    return sublime.load_settings("cs-script.sublime-settings")

def save_settings():
    return sublime.save_settings("cs-script.sublime-settings")

def on_plugin_loaded():
    Runtime.init(version, new_deployment)
    print_config()
    sublime.set_timeout_async(lambda: check_environment(False))

# -------------------------
class CodeViewTextCommand(sublime_plugin.TextCommand):
    # -----------------
    def is_enabled(self):
         return is_csharp(self.view)
    # -----------------
    def is_visible(self):
        panel_name = self.view.window().active_panel()
        if panel_name and panel_name == 'output.CS-Script':
             panel = self.view.window().find_output_panel(panel_name[len('output.'):])
             return not(panel is not None and panel.id() == self.view.id())
        else:
            return True

# -------------------------
class csscript_check_deployment(sublime_plugin.TextCommand):
    def run(self, edit):
        check_environment(True)
# -------------------------
def clear_old_versions_but(version):

    if new_deployment:
        try:
            if os.name == 'nt':
                os.system('taskkill /f /im VBCSCompiler.exe') # stop roslyn server if it is runningif os.name == 'nt':
                os.system('taskkill /f /im syntaxer.exe')     # stop syntaxer
        except:
            pass

    def delete_file(file):
        if os.path.isfile(file):
            os.remove(file)

    # old cs-script engine, prior .NET 6 migration
    delete_file(path.join(bin_dest, 'cscs.exe'))   
    delete_file(path.join(bin_dest, 'css_config.xml'))  
    delete_file(path.join(bin_dest, 'CSSRoslynProvider.dll'))  
            
    sub_dirs = [name for name in os.listdir(bin_dest)
           if os.path.isdir(os.path.join(bin_dest, name))]

    for dir in sub_dirs:
        if dir.startswith('syntaxer') and not dir.endswith(version):
            try:
                shutil.rmtree(path.join(bin_dest, dir))
            except:
                pass

    for dir in sub_dirs:
        if dir.startswith('cs-script') and not dir.endswith(version):
            try:
                shutil.rmtree(path.join(bin_dest, dir))
            except:
                pass
# -------------------------
def ensure_default_config(csscriptApp):

    config_file = path.join(path.dirname(Runtime.cscs_path), 'css_config.xml')

    if not path.exists(config_file):
        subprocess.Popen(to_args([Runtime.cscs_path, '-config:create']),
                         stdout=subprocess.PIPE,
                         cwd=path.dirname(Runtime.cscs_path),
                         shell=True).wait()

        updated_config = ''

        with open(config_file, "r") as f:
            updated_config  = f.read()

        if os.name == 'nt':
            updated_config = updated_config.replace("<useAlternativeCompiler></useAlternativeCompiler>",
                                                    "<useAlternativeCompiler>CSSRoslynProvider.dll</useAlternativeCompiler>")

            need_explicit_tuple_ref = False
            if need_explicit_tuple_ref:
                updated_config = updated_config.replace("</defaultRefAssemblies>",
                                                        " %syntaxer_dir%"+os.sep+"System.ValueTuple.dll</defaultRefAssemblies>")
            else:
                updated_config = updated_config.replace(" %syntaxer_dir%"+os.sep+"System.ValueTuple.dll", "")


            updated_config = updated_config.replace("<roslynDir></roslynDir>",
                                                    "<roslynDir>%syntaxer_dir%</roslynDir>")

        with open(config_file, "w") as file:
            file.write(updated_config)

    else:

        # update existing config to be compatible with the current cscs.exe
        if os.getenv("new_deployment") == 'true':
            with open(config_file, "r") as f:
                updated_config  = f.read()
            updated_config = updated_config.replace("%syntaxer_dir%"+os.sep+"System.ValueTuple.dll", "")
            with open(config_file, "w") as file:
                file.write(updated_config)

# -------------------------
def ensure_default_roslyn_config(csscriptApp):
    if os.getenv("new_deployment") == 'true':
        if os.name == 'nt':
            subprocess.Popen(to_args([Runtime.cscs_path, '-config:set:RoslynDir="'+current_bin_dest+'"']),
                             stdout=subprocess.PIPE,
                             cwd=path.dirname(Runtime.cscs_path),
                             shell=True).wait()
            subprocess.Popen(to_args([Runtime.cscs_path, '-config:set:useAlternativeCompiler=CSSRoslynProvider.dll']),
                             stdout=subprocess.PIPE,
                             cwd=path.dirname(Runtime.cscs_path),
                             shell=True).wait()

# -------------------------

def deploy_shadow_dir(src_subdir, dest_subdir):

    def copy_and_overwrite(from_path, to_path):
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        shutil.copytree(from_path, to_path)

    if not path.exists(bin_dest):
        os.makedirs(bin_dest)

    dest_dir = bin_dest
    if dest_subdir:
        dest_dir = path.join(dest_dir, dest_subdir)

    
    if path.exists(dest_dir):
        return
    else:
        os.makedirs(dest_dir)
 
    src = path.join(bin_src, src_subdir)
    dest = path.join(bin_dest, dest_subdir)
    
    try:
        # print('deploying', dest)
        copy_and_overwrite(src, dest)
    except Exception as ex :
        print('deploy_shadow_bin', ex)
        pass
    return dest

    shutil.copytree(dir_name, dest)

deploy_shadow_dir('cs-script',"cs-script_v"+version)
deploy_shadow_dir('cs-syntaxer', "syntaxer_v"+version)
clear_old_versions_but(version)

showTooltipOverGutter = settings().get('show_tooltip_over_gutter', True)
# -------------------------
def print_config():

    print('----------------')
    print('cscs: ', Runtime.cscs_path)
    syntaxer_print_config()
    print('syntaxcheck_on_save: ', settings().get('syntaxcheck_on_save', True))
    print('server_autostart: ', settings().get('server_autostart', True))
    print('----------------')
    # start_syntax_server()

    sublime.status_message('Starting syntaxer server...')

    args = ['dotnet']
    args.append(Runtime.syntaxer_path)
    args.append('-listen')
    args.append('-port:'+str(Runtime.syntaxer_port))
    args.append('-timeout:3000')
    args.append('-client:{0}'.format(os.getpid()))
    args.append('-cscs_path:{0}'.format(Runtime.cscs_path))
    args = to_args(args)

    start = time.time()
    subprocess.Popen(args, shell=True)
    print('>', args)
    print('> Syntaxer server started:', time.time()-start, 'seconds')

# -------------------------
from .imports.syntaxer import *
from .imports.setup import *

csscript_setup.version = version

# =================================================================================
# TODO
# Detect upgrade and fresh install for showing readme/help
# csscript_execute_and_wait should only be available on windows
# =================================================================================
formatted_views = {}
def is_formatted(view):
    if view.id() in formatted_views.keys():
        last_format_time = formatted_views[view.id()]
        return time.time() - last_format_time < 2
    return False

def mark_as_formatted(view):
    formatted_views[view.id()] = time.time()

def is_sdk_available():
    try:

        def onOutput(line): 
            global result 
            result =  line.strip()

        execute(['dotnet', "--list-sdks"], onOutput)

        # 6.0.101 [C:\Program Files\dotnet\sdk]
        # 6.0.201 [/snap/dotnet-sdk/158/sdk]
        print(result)
        return len(result) > 0    

    except Exception as e:
        print(e)
        return False
# =================================================================================
# C#/CS-Script plugin "new script" service
# =================================================================================
class csscript_new(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
        backup_file = None
        if os.path.exists(new_file_path):
            backup_file = new_file_path+'.bak'
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(new_file_path, backup_file)

        content = ''
        if backup_file:
            content = '// The previous content of this file has been saved into: '+backup_file+' \n\n'

        sample_type = ''
        if is_sdk_available():
            content += "//css_engine csc\n"
            sample_type = 'toplevel'
        else:
            sample_type = 'console'

        subprocess\
            .Popen(to_args(['dotnet', Runtime.cscs_path, '-new:'+sample_type, new_file_path]), stdout=subprocess.PIPE, shell=True)\
            .wait()

        with open(new_file_path, "r") as f:
            content = content + f.read()

        with open(new_file_path, "w") as file:
            file.write(content)

        if os.path.exists(new_file_path):
            sublime.active_window().open_file(new_file_path)
# =================================================================================
# C#/CS-Script plugin help service
# =================================================================================
class csscript_help(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
        file = csscript_setup.prepare_readme()
        if os.path.exists(file):
            sublime.active_window().open_file(file)
        else:
            sublime.error_message('Cannot find '+file)

# =================================================================================
# C#/CS-Script CS-Script help service
# =================================================================================
class csscript_css_help(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):

        if is_linux() and settings().get('allow_large_stdout_on_linux', False) != True:
            execute_in_terminal(["dotnet", Runtime.cscs_path, "-help"])
            output_view_show(out_panel)
            output_view_clear(out_panel)
            output_view_write_line(out_panel, "It has been observed that Sublime Text Python interpreter (on some specs of Linux in virtual environments) exhibits difficulties "\
                                              "capturing subprocess output of a significant size. Thus the automatic generation of the documentation is ST is disabled.")
            output_view_write_line(out_panel, "You can access CS-Script help by executing the following manual command in the terminal:")
            output_view_write_line(out_panel, "")
            output_view_write_line(out_panel, "dotnet "+Runtime.cscs_path+" -help")
            output_view_write_line(out_panel, "")
            output_view_write_line(out_panel, "You can stil enable the automatic documentation generation by setting the plugin setting `allow_large_stdout_on_linux` to `true`.")


            # The next line works perfectly in terminal and in ST
            # retval = os.system('ls -l > /home/user/.config/sublime-text/Packages/User/cs-script/help.txt ') 

            # The next 3 lines work perfectly in terminal but none in ST
            # retval = os.system('dotnet /home/user/.config/sublime-text/Packages/User/cs-script/cs-script_v1.2.3/cscs.dll -help -out:/home/user/.config/sublime-text/Packages/User/cs-script/help.txt ')
            # retval = os.system('dotnet /home/user/.config/sublime-text/Packages/User/cs-script/cs-script_v1.2.3/cscs.dll -help > /home/user/.config/sublime-text/Packages/User/cs-script/help.txt ')
            # retval = os.system('dotnet /home/user/.config/sublime-text/Packages/User/cs-script/cs-script_v1.2.3/cscs.dll -help ')

            # The next line aslso works perfectly in terminal and in ST. The only difference between `--version` and `-help` is the larger amout of the output for `-help`
            # retval = os.system('dotnet /home/user/.config/sublime-text/Packages/User/cs-script/cs-script_v1.2.3/cscs.dll --version > /home/user/.config/sublime-text/Packages/User/cs-script/help.txt')
            # output_view_write_line(out_panel, str(retval))

            return

        file = os.path.join(plugin_dir, 'cs-script.help.txt')

        with open(file, "w") as out:
            def onOutput(line): out.write(line)

            execute(['dotnet', Runtime.cscs_path, '-help'], onOutput)

        if os.path.exists(file):
            sublime.active_window().open_file(file)
        else:
            sublime.error_message('Cannot find '+file)
# =================================================================================
# C#/CS-Script syntaxer restart service
# =================================================================================
class settings_listener(sublime_plugin.EventListener):
    hooked = False
    # -----------------
    def on_activated(self, view):
        if not settings_listener.hooked:
            settings_listener.hooked = True

            on_plugin_loaded()

            self.callback()
            os.environ['CSSCRIPT_SYNTAXER_PORT'] = str(Runtime.syntaxer_port)
            settings().add_on_change("cscs_path", self.callback)
            settings().add_on_change("server_port", self.on_port_changed)


    def on_port_changed(self):

        # may be fired when setting are not available yet
        try:
            port = settings().get('server_port', 18000)
            if Runtime.syntaxer_port != port:
                Runtime.syntaxer_port = port
                os.environ['CSSCRIPT_SYNTAXER_PORT'] = str(Runtime.syntaxer_port)
        except :
            pass

    def callback(self):
        sublime.set_timeout_async(self.process_settings_change, 100)

    def process_settings_change(self):

        # may be fired when setting are not available yet
        try:
            if Runtime.cscs_path != settings().get('cscs_path', '<none>'):
                read_engine_config()

                # sublime.error_message('About to send '+Runtime.cscs_path)
                set_engine_path(Runtime.cscs_path)

                if settings().get('suppress_embedded_nuget_execution', False):
                    # the default nuget app on Linux (e.g. Mint 18) is incompatible with std.out redirection.
                    # This is valid for both both Python and .NET apps hosted by ST3. So suppress execution of 'nuget'
                    # by cscs.exe internally for resolving packages.
                    if os.name != 'nt':
                        os.environ["NUGET_INCOMPATIBLE_HOST"] = 'true'
                else:
                    try:
                        os.unsetenv('NUGET_INCOMPATIBLE_HOST')
                    except Exception as e:
                        pass

                ensure_default_config(Runtime.cscs_path)
                ensure_default_roslyn_config(Runtime.cscs_path)

                if os.getenv("new_deployment") != 'true' and os.getenv("engine_preloaded") != 'true':
                    os.environ["engine_preloaded"] = 'true'
                    # Preloading only improves the initial overhead for compiling but not for the intellisense.
                    # Important: must to wait a bit to allow Roslyn binaries to be done copied (if they ar being moved)
                    sublime.set_timeout(preload_engine, 5000)

        except:
            pass

# =================================================================================
# C#/CS-Script completion service
# =================================================================================
class csscript_listener(sublime_plugin.EventListener):
    test_count = 0
    suppress_post_save_checking = False
    post_save_jobs = []
    # -----------------
    def __init__(self, *args, **kwargs):
        sublime_plugin.EventListener.__init__(self, *args, **kwargs)
    # -----------------
    def on_activated(self, view):
        pass
    # -----------------
    def on_window_command(self, vindow, command_name, args):
        pass
    # -----------------
    def on_hover(self, view, point, hover_zone):
        if is_output_panel(view) and view == sublime.active_window().find_output_panel(out_panel):
            csscript_show_tooltip(view, point).do_output_panel()
        elif is_csharp(view):
            if hover_zone == sublime.HOVER_TEXT:
                csscript_show_tooltip(view, point).do()
            if showTooltipOverGutter and hover_zone == sublime.HOVER_GUTTER:
                csscript_show_tooltip(view, point).do_gutter()
    # -----------------
    def on_post_text_command(self, view, command_name, args):
        if command_name == 'drag_select':
            if is_output_panel(view):
                if 'by' in args.keys() and args['by'] == 'words':
                    try:
                        point = view.sel()[0].begin()
                        line_region = view.line(point)
                        line_text = view.substr(line_region)

                        view.sel().clear()
                        view.sel().add(line_region)

                        sublime.status_message('Navigating to clicked item...')

                        navigate_to_file_ref(line_text)
                    except:
                        pass
    # -----------------
    def on_load_async(self, view):
        csscript_syntax_check.show_errors()

        # view.assign_syntax('Packages/C#/C#.tmLanguage')
        # view.assign_syntax('Packages/Text/Plain text.tmLanguage')
    # -----------------
    def on_modified(self, view):

        if is_csharp(view):
            # >>> view.scope_name(view.sel()[0].begin())

            # string scope
            # 'source.cs meta.class.source.cs meta.class.body.source.cs meta.method.source.cs meta.method.body.source.cs meta.method-call.source.cs string.quoted.double.source.cs '

            # comment scope
            # 'source.cs meta.class.source.cs meta.class.body.source.cs meta.method.source.cs meta.method.body.source.cs comment.line.double-slash.source.cs '

            # comment.line.double-slash.source.cs
            # string.quoted.double.source.cs
            point = view.sel()[0].begin()
            scope = view.scope_name(point)
            inside_of_string = "string.quoted" in scope
            inside_of_comment = "comment.line" in scope or "comment.block" in scope

            if not inside_of_string and not inside_of_comment:
                typed_char = view.substr(point-1)
                if '.' == typed_char:
                    if settings().get('auto_trigger_autocomplete', True):
                        view.window().run_command("auto_complete")
                elif ('(' == typed_char or ',' == typed_char) :
                    if settings().get('auto_trigger_tooltip', True):
                        view.window().run_command("csscript_pop_tooltip")
    # -----------------
    def on_post_save(self, view):
        # if not is_csharp(view):m
        #     print('---------------')
        # clear_console()
        # sublime.log_commands(True)

        if is_csharp(view):
            # print('> on_post_save')

            # view may be engaged in 'focus changing' activity (e.g. CodeMap)
            # for i in range(5):
            #     if not is_csharp(sublime.active_window().active_view()):
            #         time.sleep(1)

            active_view = sublime.active_window().active_view()
            if active_view == view:
                if not is_formatted(view) and settings().get('format_on_save', True):
                    # print('> formatting')
                    mark_as_formatted(view)
                    view.run_command("csscript_format_code")
                    view.run_command("save")
                elif settings().get('syntaxcheck_on_save', True):
                    # print('>>>> syntax check')
                    view.window().run_command("csscript_syntax_check", {'skip_saving':True})
    # -----------------
    def is_enabled(self):
        return is_csharp(sublime.active_window().active_view())
    # -----------------
    def on_query_completions(self, view, prefix, locations):
        curr_doc = view.file_name()

        if is_script_file(curr_doc):

            completions = []

            if not is_valid_selection(view):
                sublime.status_message('Incompatible selection')
                return completions

            (curr_doc, location, as_temp_file) = get_saved_doc(view)

            response = send_completion_request(curr_doc, location)
            if as_temp_file:
                os.remove(curr_doc)

            completions = self.parse_response(response)
            if completions:
                return (completions, sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)
    # -----------------
    def parse_response(self, response):

        if not response:
            return None

        completions = []
        error = None

        for line in response.split('\n'):
            if line.startswith('<error>'):
                error = "Error: cannot get C# completion from the syntax server\n"
            if not error:
                parts = line.strip().split('|')
                if len(parts) == 2:
                    completions.append((parts[0], parts[1]))
            else:
                error += line.replace('<error>', '')

        if error:
            print(error)

        return completions

# =================================================================================
# CS-Script plugin settings
# =================================================================================
class csscript_show_settings(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
        self.view.window().open_file(plugin_settings_file)

# =================================================================================
# CS-Script code show cs-script config
# =================================================================================
class csscript_show_config(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
        run_cscs(\
            ['-config'], \
            handle_line = lambda line: output_view_write_line(out_panel, line), \
            on_done=lambda: sublime.show(1, 1), \
            header= 'CS-Script configuration (see `https://github.com/oleg-shilo/cs-script/wiki/CS-Script---Command-Line-Interface#-configoption`)')

# =================================================================================
# CS-Script code formatter service
# =================================================================================
class csscript_format_code(CodeViewTextCommand):
    # -----------------
    def run(self, edit):
        mark_as_formatted(self.view)
        sublime.status_message('Formatting script "'+self.view.file_name()+'"')

        # position in text and in file mey not be the same depending on line endings type
        text_location = -1
        if len(self.view.sel()) > 0:
            text_location = self.view.sel()[0].begin()

        (curr_doc, file_location, as_temp_file) = get_saved_doc(self.view)

        response = send_formatting_request(curr_doc, file_location)

        if as_temp_file:
            os.remove(curr_doc)

        if response:
            if response.startswith('<error>'):
                print('Formatting error:', response.replace('<error>', ''))
            else:
                parts = response.split('\n', 1)

                new_file_location = int(parts[0])
                formatted_code = parts[1]

                new_text_location = to_text_pos(formatted_code, new_file_location)
                new_text = formatted_code.replace('\r', '')

                self.view.replace(edit, sublime.Region(0, self.view.size()), new_text)
                # with open(self.view.file_name(), "w") as file:
                #     file.write(formatted_code)

                # surprisingly mapping of selection is not required. ST3 does it by itself
                # self.view.sel().clear()
                # self.view.sel().add(sublime.Region(new_text_location, new_text_location))

                # print('formatting done')
                # sublime.active_window().run_command("save")


# =================================================================================
# CS-Script async replecement service
# =================================================================================
# DONE
class csscript_resolve_using_async(CodeViewTextCommand):
    # -----------------
    def run(self, edit, **args):
        parts = args['region'].split(',')
        region = sublime.Region(int(parts[0]), int(parts[1]))
        replacement = args['replacement']
        self.view.replace(edit, region, replacement)

# =================================================================================
# CS-Script resolve missing usings service
# =================================================================================
# DONE
class csscript_resolve_using(CodeViewTextCommand):
    inprogress= False
    # -----------------
    def run(self, edit, **args):
        view = self.view
        self.edit = edit
        self.point = None

        self.first_suffestion = False

        if 'point' in args.keys():
            self.point = int(args['point'])
            self.first_suffestion = True

        if self.point == None:
            if len(view.sel()) == 0:
                return
            else:
                self.point = view.sel()[0].begin()

        busy_indicator.show('Analyzing')
        sublime.set_timeout(self.do, 10)
    # -----------------
    def do(self):
        try:
            csscript_resolve_using.inprogress = True

            view = self.view

            word_region = view.word(self.point)
            word_to_resolve = view.substr(word_region)
            # print('view', view.file_name())

            (saved_doc, location, as_temp_file) = get_saved_doc(view)

            response = send_resolve_using_request(saved_doc, word_to_resolve)
            busy_indicator.hide()

            if as_temp_file:
                os.remove(saved_doc)

            if response == '<null>':
                pass
            elif response.startswith('<error>'):
                print(response.replace('<error>', 'CS-Script error: '))
            else:
                items = response.split('\n')
                def on_done(index):
                    if index != -1:
                        for region in self.view.lines(sublime.Region(0,self.view.size())):
                            line  = self.view.substr(region)
                            if not line.startswith("//"):
                                # cannot use 'self.view.replace(self.edit...' as edit is already invalid
                                # so need to start a new command that ctreats 'edit'; Remember, 'edit' cannot be created from code
                                # self.view.replace(self.edit, sublime.Region(start, start), 'using '+items[index]+';'+'\n')
                                region = str(region.begin())+','+str(region.begin())
                                replacement = 'using '+items[index]+';'+'\n'
                                sublime.active_window().run_command("csscript_resolve_using_async", {'replacement':replacement, 'region':region})
                                sublime.active_window().run_command('save')
                                break

                if self.first_suffestion:
                    on_done(0)
                else:
                    self.view.show_popup_menu(items, on_done, 1)

        except Exception as err:
            print(err)

        busy_indicator.hide()
        csscript_resolve_using.inprogress = False

# =================================================================================
# CS-Script tooltip service (for invoking via hotkeys)
# =================================================================================
class csscript_pop_tooltip(CodeViewTextCommand):
    # -----------------
    def run(self, edit):
        self.view.hide_popup()
        point = self.view.sel()[0].begin()

        left_char = self.view.substr(point-1)
        right_char = self.view.substr(point)
        line = self.view.line(point)
        line_str = self.view.substr(line)

        new_point = -1

        if line_str.startswith('//css'):
            csscript_show_tooltip(self.view,  line.begin()).do()
            return

        if left_char == ' ' or left_char == '(' or left_char == ',' or right_char == ')':
            new_point = point - 1
            while self.view.substr(new_point) != '(':
                new_point = new_point - 1
                if new_point < line.begin():
                    new_point = -1
                    break

        if new_point != -1:
            hint = self.view.substr(sublime.Region(point, new_point))
            csscript_show_tooltip(self.view,  new_point+1, hint).do()
        else:
            csscript_show_tooltip(self.view,  point).do()

# =================================================================================
# CS-Script references search service
# =================================================================================
class csscript_find_references(CodeViewTextCommand):
    # -----------------
    def run(self, edit):
        clear_and_print_result_header(self.view.file_name())
        sublime.set_timeout(self.do, 100)

    def do(self):
        (saved_doc, location, as_temp_file) = get_saved_doc(self.view)

        response = send_resolve_references(saved_doc, location)

        if as_temp_file:
            os.remove(saved_doc)
            response = response.replace(saved_doc, self.view.file_name())

        if response == '<null>':
            pass
        elif response.startswith('<error>'):
            print(response.replace('<error>', 'CS-Script error: '))
        else:
            output_view_write_line(out_panel, response)

# =================================================================================
# CS-Script project UI marshaling service (not in use yet)
# =================================================================================
class dispatcher(CodeViewTextCommand):
    queue = []
    # -----------------
    def invoke(edit, action):
        sublime.active_window().run_command('dispatcher', {'action': action})
        pass
    # -----------------
    def run(self, edit, **args):
        if 'action' in args.keys():
            action = args['action']
            try:
                action(self, edit)
            except Exception as ex:
                print("dispatcher:", ex)
        pass

# =================================================================================
# CS-Script project output panel service
# =================================================================================
class csscript_show_output(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
         output_view_show(out_panel)

# =================================================================================
# CS-Script project resolver service
# =================================================================================
class csscript_about(sublime_plugin.TextCommand):
    # -----------------
    def run(self, edit):
        run_cscs(\
            [], \
            handle_line = lambda line: output_view_write_line(out_panel, line), \
            on_done=lambda: sublime.show(1, 1), \
            header= 'CS-Script.ST3 - C# intellisense and execution plugin (v'+version+')')

# =================================================================================
# CS-Script project resolver service
# =================================================================================
# class csscript_load_proj(CodeViewTextCommand):
class csscript_list_proj_files(CodeViewTextCommand):
    # -----------------
    def handle_line(self, line):
        curr_prefix = line.split(':', 1)[0]
        if curr_prefix != self.prefix:
            self.prefix = curr_prefix
            # output_view_write_line(out_panel, '-------')
        output_view_write_line(out_panel, line.replace(curr_prefix+':', curr_prefix+": "))
    # -----------------
    def run(self, edit):
        view = self.view
        self.prefix = 'file'

        sublime.status_message('Checking script deficiencies for "'+self.view.file_name()+'"')

        if self.view.is_dirty():
            sublime.active_window().run_command("save")
            sublime.set_timeout(self.do, 100)
        else:
            self.do()
    # -----------------
    def do(self):

        def on_done():
            output_view_write_line(out_panel, "---------------------\n[Script dependencies]")

        run_doc_in_cscs(['-l', "-proj:dbg"], self.view, self.handle_line, on_done)
# =================================================================================
# CS-Script project (sources only) resolver service
# =================================================================================
class csscript_list_proj_sources(CodeViewTextCommand):
    # -----------------
    def handle_line(self, line):
        curr_prefix = line.split(':', 1)[0]
        if curr_prefix != self.prefix:
            self.prefix = curr_prefix
            # don't separate for now
            # output_view_write_line(out_panel, '-------')

        if not line.endswith('dbg.cs'):
            if curr_prefix.startswith('file'):
                text = line.replace("file:", '')
                if self.prev_line:
                    output_view_write_line(out_panel, item_boxed_prefix + self.prev_line)
                else:
                    output_view_write_line(out_panel, 'Sources')

                self.prev_line = text
    # -----------------
    def run(self, edit):
        view = self.view
        self.prefix = 'file'
        self.prev_line = None
        sublime.status_message('Checking script dependencies for "'+self.view.file_name()+'"')

        if self.view.is_dirty():
            sublime.active_window().run_command("save")
            sublime.set_timeout(self.do, 100)
        else:
            self.do()
    # -----------------
    def do(self):

        def on_done():
            if self.prev_line:
                output_view_write_line(out_panel, last_item_boxed_prefix + self.prev_line)
            self.prev_line = None

            output_view_write_line(out_panel, "---------------------\n[Script sources]")

        run_doc_in_cscs(['-l', "-proj:dbg"], self.view, self.handle_line, on_done)

# =================================================================================
# CS-Script syntax check service
# =================================================================================
# DONE
class csscript_syntax_check(CodeViewTextCommand):
    errors = {}
    instance = None
    # -----------------
    def run(self, edit, **args):

        view = self.view

        sublime.status_message('Checking syntax of "'+view.file_name()+'"')

        if view.is_dirty() and not 'skip_saving' in args.keys():
            sublime.active_window().run_command("save")

        curr_doc = view.file_name()

        clear_and_print_result_header(curr_doc)

        if not path.exists(Runtime.cscs_path):
            print('Error: cannot find CS-Script launcher - ', Runtime.cscs_path)
        elif not curr_doc:
            print('Error: cannot find out the document path')
        else:

            clear_and_print_result_header(curr_doc)
            
            if '//css_nuget' in view.substr(sublime.Region(0, view.size())):
                output_view_write_line(out_panel, "Resolving NuGet packages may take time...")
            csscript_syntax_check.clear_errors()

            
            proc = popen_redirect(['dotnet', Runtime.cscs_path, '-l', "-check", curr_doc])


            first_result = True
            for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
                line = line.strip()
                if first_result:
                    first_result = False
                    clear_and_print_result_header(curr_doc)

                output_view_write_line(out_panel, line)
                error_info = extract_location(line.strip())
                if error_info:

                    file, line, column, context = error_info
                    file = os.path.abspath(file)
                    if file not in csscript_syntax_check.errors.keys():
                        csscript_syntax_check.errors[file] = []

                    csscript_syntax_check.errors[file].append((line, column, context))
            output_view_write_line(out_panel, "[Syntax check]")

            csscript_syntax_check.show_errors()

    # -----------------
    def has_errors(file):
        for key in csscript_syntax_check.errors.keys():
            if key.lower() == file.lower():
                return True
        return False
    # -----------------
    def get_errors(file, line): # line is 1-based
        errors = []
        for key in csscript_syntax_check.errors.keys():
            if key.lower() == file.lower():
                for error_info in csscript_syntax_check.errors[key]:
                    ln, col, cxt = error_info
                    if ln == line:
                        errors.append(error_info)

                if len(errors) > 0:
                    break

        return errors
    # -----------------
    def clear_errors():

        for view in sublime.active_window().views():
            if view.file_name():
                view.erase_regions("cs-script.errors")

        csscript_syntax_check.errors.clear()
    # -----------------
    def show_errors():
        error_strong_appearence = settings().get('error_strong_appearence', False)
        error_strong_appearence = True
        for file in csscript_syntax_check.errors.keys():
            view = find_file_view(file)
            if view:
                view.erase_regions("cs-script.errors")

                regions = []

                for line, column, context in csscript_syntax_check.errors[file]:
                    pt = view.text_point(line-1, column-1)
                    regions.append(view.word(pt))

                # scope = settings().get('cs-script.syntaxerror_scope')
                # https://www.sublimetext.com/docs/3/scope_naming.html
                # http://docs.sublimetext.info/en/latest/reference/color_schemes.html
                scope = 'invalid'
                icon = 'Packages/'+plugin_name+'/images/error.png'
                # icon = 'Packages/cs-script-sublime/images/error.png'
                if error_strong_appearence:
                    flags = 0
                else:
                    flags = sublime.DRAW_SQUIGGLY_UNDERLINE|sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE
                view.add_regions("cs-script.errors", regions, scope, icon, flags)

# =================================================================================
# C#/CS-Script kill running script service
# =================================================================================
class csscript_kills_script(sublime_plugin.TextCommand):
    # -----------------
    def is_enabled(self):
         return csscript_execute_and_redirect.running_process != None
    # -----------------
    def is_visible(self):
        panel_name = self.view.window().active_panel()
        if panel_name and panel_name == 'output.CS-Script':
             panel = self.view.window().find_output_panel(panel_name[len('output.'):])
             return panel is not None and panel.id() == self.view.id()
        else:
            return False
    # -----------------
    def run(self, edit):
        if csscript_execute_and_redirect.running_process:
            try:
                pid = csscript_execute_and_redirect.running_process.pid

                sublime.status_message('Terminating...')

                # extremely important to kill all process children
                if os.name == 'posix':
                    subprocess.Popen(['pkill', '-TERM', '-P', str(pid)])
                else:
                    send_pkill_request(pid, 'cscs')
            except:
                pass

# =================================================================================
# CS-Script tooltip service
# =================================================================================
class csscript_show_tooltip():
    def __init__(self, view, point, hint=''):
        self.view = view
        self.point = point
        self.location = point
        self.hint = hint
    # -----------------
    def do_output_panel(self):
        only_over_process_line = True

        if only_over_process_line:
            mouse_line, mouse_column = self.view.rowcol(self.point)
            mouse_region = self.view.line(self.point)
            line = self.view.substr(mouse_region)
        else:
            line_reg = self.view.line(self.view.text_point(2, 0))
            line = self.view.substr(line_reg)

        # print('>>>>>>', line)
        if line.startswith('[Started pid: ') and csscript_execute_and_redirect.running_process:
            try:
                pid = int(line.replace('[Started pid: ','').replace(']',''))

                link =  '<a href="'+str(self.point)+'">Terminate process '+str(pid)+'</a>'
                def terminate(arg):
                    sublime.status_message('Terminating...')
                    self.view.hide_popup()

                    # extremely important to kill all process children
                    if os.name == 'posix':
                        subprocess.Popen(['pkill', '-TERM', '-P', str(pid)])
                    else:
                        send_pkill_request(pid, 'cscs')

                html = """
                    <body id=show-scope>
                        <style>
                        body { margin: 0; padding: 5; }
                         p { margin-top: 0;}
                         </style>
                        %s
                    </body>
                """ % (link)

                self.view.show_popup(html, location=self.point, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=600, on_navigate=terminate)
            except :
                pass
    # -----------------
    def do_gutter(self):
        if csscript_resolve_using.inprogress: return

        file = self.view.file_name()
        line, column = self.view.rowcol(self.point)

        errors = ''
        for line, column, error in csscript_syntax_check.get_errors(file, line+1):
            errors = errors + error.strip() + '<br>'
        html = """
            <body id=show-scope>
                <style>
                body { margin: 0; padding: 5; }
                 p { margin-top: 0;}
                 </style>
                <p>%s</p>
            </body>
        """ % (errors)

        self.view.show_popup(html, location=self.point, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=600)

    # -----------------
    def do(self):

        if csscript_resolve_using.inprogress: return

        # check if we are over the error region
        # NOTE: view.text_point and view.rowcol operate in 0-based units and C# compiler errors are reported in 1-based ones
        mouse_line, mouse_column = self.view.rowcol(self.point)
        mouse_region = self.view.word(self.point)

        for line, column, error in csscript_syntax_check.get_errors(self.view.file_name(), mouse_line+1):
            error_region = self.view.word(self.view.text_point(line-1,column-1))
            if error_region == mouse_region:

                link = ''
                # doesn't work yet
                if 'CS0103' in error:
                    link =  '<a href="'+str(self.point)+'">Try to fix it</a>'

                html = """
                        <body id=show-scope>
                            <style>
                            body { margin: 0; padding: 5; }
                             p { margin-top: 0;}
                             </style>
                            <p>%s</p>
                            %s
                        </body>
                    """ % (error, link)
                # html = '<body id=show-scope>'+error+'</body>'
                self.view.show_popup(html, location=self.point, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=600, on_navigate=lambda x: self._try_to_fix(x))
                return


        (curr_doc, location, as_temp_file) = get_saved_doc(self.view, self.location)
        text = send_tooltip_request(curr_doc, location, self.hint, settings().get('auto_tooltip_light_content', False))

        if as_temp_file:
            os.remove(curr_doc)

        if text:
            if text == '<null>':
                # print('tooltip null')
                return
            elif text.startswith('<error>'):
                print(text.replace('<error>', 'CS-Script generate tooltip error: '))
            else:
                self._show(text, self.point)
    # -----------------
    def _try_to_fix(self, point):
        self.view.hide_popup()
        sublime.set_timeout(lambda : sublime.active_window().run_command("csscript_resolve_using", {'point': point}), 100)
        pass
    # -----------------
    def _go_to_definition(self):

        self.view.hide_popup()

        #unfortunately setting selection doesn't work when invoked from OnPopupHide callback
        # self.view.sel().clear()
        # self.view.sel().add(sublime.Region(self.location, self.location))
        # sublime.active_window().run_command("csscript_goto_definition")

        (curr_doc, location, as_temp_file) = get_saved_doc(self.view, self.location)
        csscript_goto_definition.do(curr_doc, location, as_temp_file)
    # -----------------
    def decorate(self, text):
        text = text.replace('\r', '')


        def deco_section(text, style):
            parts = text.split(':', 1)

            if len(parts) > 1:
                title = parts[0]
                rest = parts[1]
                return '<span class="title">'+title+':</span><span class="'+style+'">'+rest+'</span>\n'
            else:
                return '<span class="'+style+'">'+text+'</span>\n'


        parts = text.split('\n', 1)

        if len(parts) > 1:
            sugnature = deco_section(parts[0],'sig')
            doc = parts[1].strip()
            exc = ''
            pos = doc.find('Exceptions:')
            if pos != -1:
                exc = '<br>'+deco_section(doc[pos:], 'exc')+'<br>\n'
                doc = doc[:pos].strip()

            doc = '<br><span class="doc">'+doc+'</span><br>'
            text = sugnature + doc + exc
        else:
            text = deco_section(text,'sig')

        return text
    # -----------------
    def _show(self, text, text_point):
        import html
        if self.view.is_popup_visible():
            return

        text_value = html.escape(text, quote=False)
        text_value = self.decorate(text_value)
        text_value = text_value.replace('\n', '<br>')

        html = """
            <body id=show-scope>
                <style>
                    body { margin: 0; padding: 5;  }
                    p { margin-top: 0; }
                    a {
                        font-family: sans-serif;
                        font-size: 1.05rem;
                    }
                    span.title {
                        font-style: italic;
                        font-weight: bold;
                        font-size: 1.1rem;
                        padding: 0px;
                    }
                    span.doc {
                        font-style: italic;
                    }
                    span.exc {
                        padding: 15px;
                    }
                    span.sig {
                    }
                </style>
                <p>%s</p>
                $go_def_link
            </body>
        """ % (text_value)


        if self.hint:
            html = html.replace('$go_def_link', '')
        else:
            html = html.replace('$go_def_link','<a href="dummy">Go to Definition</a>')

        # print('---------------------')
        # print(html)
        # print('---------------------')
        flg = sublime.HIDE_ON_MOUSE_MOVE|sublime.HIDE_ON_MOUSE_MOVE_AWAY # testing
        flg = sublime.HIDE_ON_MOUSE_MOVE_AWAY

        self.view.show_popup(html, flags=flg, location=text_point, max_width=600, on_navigate=lambda x: self._go_to_definition())

# =================================================================================
# CS-Script execute service with STD out redirection
# =================================================================================
class csscript_execute_and_redirect(CodeViewTextCommand):
    running_process = None
    # -----------------
    def run(self, edit):
        
        if csscript_execute_and_redirect.running_process:
            if os.name == 'nt':
                try:
                    os.kill(p.pid, signal.SIGKILL)
                except:
                    pass
            else:
                print("Previous C# script is still running...")
                return

        sublime.status_message('Executing script "'+self.view.file_name()+'"')

        if self.view.is_dirty():
            csscript_listener.suppress_post_save_checking = True
            sublime.active_window().run_command("save")

        curr_doc = self.view.file_name()

        def run():
            script = curr_doc
            clear_and_print_result_header(self.view.file_name())
            
            def on_process_start(p):
                output_view_write_line(out_panel, '[Started pid: '+str(p.pid)+']', True)
                csscript_execute_and_redirect.running_process = p

            def on_process_output_line(line):
                if line != '':
                    output_view_append(out_panel, line)

            try:
                execute(['dotnet', Runtime.cscs_path, script], on_process_output_line, on_process_start)
            except:
                print("Error Encountered while running script")

            output_view_write_line(out_panel, "[Execution completed]")
            
            csscript_execute_and_redirect.running_process = None
            return


            # process = subprocess.Popen(to_args(['dotnet', Runtime.cscs_path, script]),  stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            
            # output_view_write_line(out_panel, '[Started pid: '+str(process.pid)+']', True)
            
            # csscript_execute_and_redirect.running_process = process

            # def process_line(output, ignore_empty = False):
            #     try:
            #         output = output.decode('utf-8').rstrip()
            #         if not ignore_empty or output != '':
            #     except UnicodeDecodeError:
            #         append_output('<Decoding error. You may want to adjust script output encoding in settings.>')
            #         # process.terminate()

            # while process.poll() is None: # may not read the last few lines of output
            #     output = process.stdout.readline()
            #     process_line(output)

            # while (True): # drain any remaining data
            #     try:
            #         output = process.stdout.readline()
            #         if output == b'':
            #             output = process.stderr.readline()
            #             break;
            #         process_line(output, ignore_empty=True)
            #     except :
            #         pass

            # csscript_execute_and_redirect.running_process = None
            # output_view_write_line(out_panel, "[Execution completed]")

        #must be done in a separate thread otherwise line rendering is suspended until process exits
        sublime.set_timeout_async(run, 10)

# =================================================================================
# CS-Script build executable from the script
# =================================================================================
# +done
class csscript_build_exe(CodeViewTextCommand):
    # -----------------
    def run(self, edit):
        view = self.view
        self.prefix = 'file'

        sublime.status_message('Building executable from the script "'+self.view.file_name()+'"')

        if self.view.is_dirty():
            sublime.active_window().run_command("save")
            sublime.set_timeout(self.do, 100)
        else:
            self.do()
    # -----------------
    def do(self):
        script_file = self.view.file_name()
        pre, ext = os.path.splitext(script_file)
        exe_file = pre + '.exe'

        def handle_line(line):
            output_view_write_line(out_panel, line)

        def on_done():
            if path.exists(exe_file):
                output_view_write_line(out_panel,'Script is converted into executable ' + exe_file)
            output_view_write_line(out_panel, "---------------------\n[Build exe]")
            sublime.show(1, 1)

        run_doc_in_cscs(['-l', '-e'], self.view, handle_line, on_done)

# =================================================================================
# CS-Script execute service. Shell remains visible after the process termination
# =================================================================================
# +done
class csscript_execute_and_wait(CodeViewTextCommand):
    # -----------------
    def run(self, edit):
        
        sublime.active_window().run_command("save")
        curr_doc = self.view.file_name()

        if not path.exists(Runtime.cscs_path):
            print('Error: cannot find CS-Script launcher - ', Runtime.cscs_path)
        else:
            execute_in_terminal(['dotnet', Runtime.cscs_path, '-l', '-wait', curr_doc])

            return

            # older algorithm that may need to be reactivated in the future if the current one stops working on Linux
            if os.name == 'nt':
                os.system('dotnet "' + Runtime.cscs_path + '" -l -wait "'+ curr_doc + '"')
            else:
                # Linux and Mac
                env = os.environ.copy()
                env['SCRIPT_FILE'] = curr_doc

                cwd = os.path.dirname(curr_doc)

                css_command = ' dotnet "' + Runtime.cscs_path + '" -l -wait "'+ curr_doc + '"'

                command = "bash -c \"{0} ; exec bash\"".format(css_command)
                args =[TerminalSelector.get(), '-e', command]

                if 'NUGET_INCOMPATIBLE_HOST' in env:
                    del env['NUGET_INCOMPATIBLE_HOST']

                print(args)
                subprocess.Popen(args, cwd=cwd, env=env)

# =================================================================================
# CS-Script go-to-next-result service
# =================================================================================
class csscript_next_result(sublime_plugin.WindowCommand):
    # -----------------
    def run(self):
        view_name = sublime.active_window().active_panel()
        if not view_name:
            return

        if view_name == 'output.exec':
            self.window.run_command('next_result')
        else:
            if view_name.startswith('output.'):
                view_name = view_name.replace('output.', '')

            view = sublime.active_window().find_output_panel(view_name)

            if not view or not view.window():
                return

            caret_point = view.sel()[0].begin()
            caret_line_region = view.line(caret_point)
            line_regions = view.lines(sublime.Region(0, view.size()))

            next_location_index = -1
            locations = []

            for rg in line_regions:
                line = view.substr(rg).strip()
                info = extract_location(line)
                if info:
                    if next_location_index == -1 and rg == caret_line_region:
                        next_location_index = len(locations)
                    locations.append((rg, line))

            if len(locations) > 0:
                next_location_index = next_location_index + 1

                if next_location_index >= len(locations):
                    next_location_index = 0

                line_region, line_text = locations[next_location_index]

                view.sel().clear()
                view.sel().add(line_region)
                view.run_command('append', {'characters': ''}) # to force repainting the selection

                navigate_to_file_ref(line_text)

# =================================================================================
# CS-Script go-to-definition service
# =================================================================================
class csscript_goto_definition(CodeViewTextCommand):
    # -----------------
    def run(self, edit):
        view = self.view
        curr_doc = self.view.file_name()
        if is_script_file(curr_doc):

            if not is_valid_selection(self.view):
                sublime.status_message('Incompatible selection')
                return

            (curr_doc, location, as_temp_file) = get_saved_doc(view)

            csscript_goto_definition.do(curr_doc, location, as_temp_file)
    # -----------------
    def do(curr_doc, location, as_temp_file):
            response = send_resolve_request(curr_doc, location)

            if as_temp_file:
                os.remove(curr_doc)

            path = csscript_goto_definition.parse_response(response)
            if path:
                fiel_name = os.path.basename(path).split(':')[0].lower()

                if fiel_name.endswith('.dll') or fiel_name.endswith('.exe'):
                    dir_path = os.path.dirname(path)
                    sublime.active_window().run_command('open_dir', { 'dir': dir_path })
                else:
                    sublime.active_window().open_file(path, sublime.ENCODED_POSITION)
    # -----------------
    def parse_response(response):
        if not response:
            return None

        error = None
        fileName = None
        lineNum = None

        for line in response.split('\n'):
            if line.startswith('<error>'):
                error = "Error: cannot resolve C# symbol\n"
            if not error:
                if line.startswith('file:'):
                    fileName = line[5:].strip()
                if line.startswith('line:'):
                    lineNum = line[5:].strip()
            else:
                error += line.replace('<error>', '')

        if error:
            print(error)
        elif fileName:
            if fileName.endswith('.tmp'):
                possible_oriuginal_file = fileName[:-4]
                if os.path.exists(possible_oriuginal_file):
                    fileName = possible_oriuginal_file

            # print("{0}:{1}:0".format(fileName, lineNum))
            return "{0}:{1}:0".format(fileName, lineNum)

# =================================================================================
# CS-Script go-to-definition service
# =================================================================================
# +done
class csscript_show_output_panel(sublime_plugin.WindowCommand):
    # -----------------
    def run(self):
        view = sublime.active_window().active_view()
        if sublime.active_window().active_panel() == 'output.'+out_panel:
            output_view_hide(out_panel)
        else:
            output_view_show(out_panel)
