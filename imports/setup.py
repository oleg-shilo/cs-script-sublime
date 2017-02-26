import os
import io
import codecs
import sys
import html
import time
import sublime
import sublime_plugin
import subprocess
import threading
from os import path
from subprocess import Popen, PIPE, STDOUT
from distutils.version import LooseVersion, StrictVersion
# -------------------------  
from .utils import *  
from .syntaxer import *
# -------------------------
plugin_dir = path.dirname(path.dirname(__file__))
# csscriptApp = path.join(path.dirname(plugin_dir), 'User', 'cs-script.bin','cscs.exe')
# syntaxerApp = path.join(path.dirname(plugin_dir), 'User', 'cs-script.bin','syntaxer.exe')

def settings():
    return sublime.load_settings("cs-script.sublime-settings")

def save_settings():
    return sublime.save_settings("cs-script.sublime-settings")
              

# =================================================================================
# C#/CS-Script setup service
# =================================================================================
class csscript_setup(sublime_plugin.EventListener):
    # ----------------- 
    version = None
    # ----------------- 
    def get_sysconfig_description():
        template = """
**Required minimum system configuration:**
 * {req_clr}
 * CS-Script:  v3.19

**Detected system configuration:**
  * {det_clr}
  * {det_css}
{clr_install}"""

        required_clr = ''
        detected_clr = ''
        detected_css = '' 
        clr_install = ''     

        if os.name == 'posix':
            required_clr = 'Mono:       v4.6.2'
            incompatible_clr = True

            current_mono_version = csscript_setup.get_mono_version()

            if current_mono_version == None:
                detected_clr = 'Mono:       <not found>'
                detected_css = 'CS-Script:  <unknown>'

            elif LooseVersion(current_mono_version) <  LooseVersion('4.6.2') :
                detected_clr = 'Mono:       v'+str(current_mono_version) + ' <incompatible>'
                detected_css = 'CS-Script:  <unknown>'

            elif LooseVersion(current_mono_version) >=  LooseVersion('4.6.2') :
                # only reun cscs if compatible clr is found
                incompatible_clr = False
                css_ver, clr_ver = csscript_setup.get_css_version()
                detected_clr = 'Mono:       v' + str(current_mono_version)
                detected_css = 'CS-Script:  v' + css_ver

            if incompatible_clr:   
                clr_install = """
The required version of Mono runtime cannot be deteced on the system.
Please visit Mono website (http://www.mono-project.com/docs/getting-started/install/linux/) and follow the instructions on how to install the latest version.
Note: you need to install "mono-complete" package.

The following are the instructions on how to install Mono on Debian, Ubuntu, and derivatives (as at 24 Dec 2016 for Mint18):
 sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
 echo "deb http://download.mono-project.com/repo/debian wheezy main" | sudo tee /etc/apt/sources.list.d/mono-xamarin.list
 sudo apt-get update
 sudo apt-get install mono-complete
"""
        else:
            css_ver, clr_ver = csscript_setup.get_css_version()
            print('clr_ver', clr_ver)
            if css_ver == None:
                detected_clr = '.NET:       <unknown>'
                detected_css = 'CS-Script:  <unknown>'
            elif LooseVersion(clr_ver) <  LooseVersion('4.0') :
                detected_clr = '.NET:       v'+ clr_ver + ' <incompatible>'
                detected_css = 'CS-Script:  v'+css_ver

            elif LooseVersion(clr_ver) >=  LooseVersion('4.0') :
                # only run cscs if compatible clr is found
                incompatible_clr = False

            required_clr = '.NET:       v4.0/4.5'
            detected_clr = '.NET:       v' + clr_ver   
            detected_css = 'CS-Script:  v' + css_ver
            
            if incompatible_clr:   
                clr_install = """
!!!!!!!!!!!!!!!!!
The required version of .NET runtime cannot be deteced on the system.
!!!!!!!!!!!!!!!!!
Please visit .NET website (https://www.microsoft.com/net/download) and follow the instructions on how to install the latest version.
"""
        return template.replace('{req_clr}', required_clr) \
                       .replace('{det_clr}', detected_clr) \
                       .replace('{det_css}', detected_css) \
                       .replace('{clr_install}', clr_install) 
    # ----------------- 
    def get_mono_version():
        try:
            version = ''
            file = os.path.join(plugin_dir, 'detect_css.log')

            command = ['mono', '--version']
            with open(file, 'w') as logfile:
                subprocess.call(command, stdout=logfile, shell=False)
                
            with open(file, 'r') as logfile:
                prefix = 'Mono JIT compiler version'
                for line in logfile.readlines():
                    if prefix in line:
                        version = line[len(prefix):].strip().split(' ')[0]
                        break

            if os.path.exists(file):
                os.remove(file)
            
            return version

        except Exception as e:
            print(e)
            return None
    # ----------------- 
    def get_css_version():
        try:
            version = ''
            clr_version = ''
            # print('read ver..')

            global csscriptApp
            proc = popen_redirect([csscriptApp, "-ver"])

            # print('csscriptApp', os.path.exists(csscriptApp), csscriptApp)

            prefix = 'C# Script execution engine. Version'
            clr_prefix = 'CLR:' 

            for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):  
                # print(line)
                line = line.strip()
                if prefix in line:
                    # C# Script execution engine. Version 3.19.1.0.
                    version = line[len(prefix):].strip().strip('.')
                if clr_prefix in line:
                    # CLR:            4.0.30319.42000 (.NET Framework v4.6.2 or later)
                    ver_str = line.split(':')[1]
                    clr_version = ver_str.split('(')[0].strip()
                    # print('ver:', clr_version)

            return (version, clr_version)

        except Exception as e:
            print(e)
            return (None, None)
    # -----------------
    # def is_enabled(self):
    #     return is_csharp(sublime.active_window().active_view())
    # -----------------
    def on_activated(self, view):
        file = view.file_name()
        if file and file.lower().endswith('.cs'):
            if settings().get('last_run_version', 'unknown') != csscript_setup.version:
                sublime.set_timeout_async(self.show_readme, 500)

            settings().set('last_run_version', csscript_setup.version)
            save_settings()
    # -----------------
    def show_readme(self):
        # print('csscript_help')
        # sublime.error_message('Readme.md')
        sublime.active_window().run_command("csscript_help")
    # -----------------
    def prepare_readme():
        readme = os.path.join(plugin_dir, 'readme.md')

        readme_template = os.path.join(plugin_dir, 'docs', 'readme.tmpl.md')
        template = ''

        with open(readme_template, "r") as f: 
            templete = f.read()

        content = templete.replace('{SYS_REQ}', csscript_setup.get_sysconfig_description())    

        with open(readme, "w") as f: 
            f.write(content)

        return readme
    # -----------------
    def prepare_css_help():
        global csscriptApp
        
        readme = os.path.join(plugin_dir, 'cs-script.help.txt')

        with open(readme, "w") as f: 
            popen_redirect_tofile([csscriptApp, "-help"], f).wait()

        return readme
