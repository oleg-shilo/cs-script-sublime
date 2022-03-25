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
 * .NET:       v{req_clr}
 * CS-Script:  v4.4.2

**Detected system configuration:**
  * {det_clr}
  * {det_css}
{clr_install}"""

        required_clr = ''
        detected_clr = ''
        detected_css = ''
        clr_install = ''

        required_clr = '6.˟'
        incompatible_clr = True

        current_dotnet_version = get_dotnet_version()
        
        if current_dotnet_version == None:
            detected_clr = '.NET:       <not found>'
            detected_css = 'CS-Script:  <unknown>'

        elif LooseVersion(current_dotnet_version) <  LooseVersion(Runtime.min_compatible_dotnet_version) or LooseVersion(current_dotnet_version) >=  LooseVersion(Runtime.max_compatible_dotnet_version):
            detected_clr = '.NET:       v'+str(current_dotnet_version) + ' <incompatible> - required v'+required_clr
            detected_css = 'CS-Script:  <unknown>'

        elif LooseVersion(current_dotnet_version) >=  LooseVersion('6.0.0') :
            # only run cscs if compatible clr is found
            incompatible_clr = False
            css_ver  = get_css_version()
            detected_clr = '.NET:       v' + str(current_dotnet_version)
            detected_css = 'CS-Script:  v' + css_ver

        if incompatible_clr:
            clr_install = """
The required version of .NET runtime cannot be detected on the system.
Please visit .NET website (https://dotnet.microsoft.com) and follow the instructions on how to install the required version (v"""+required_clr+""").
"""
        
        return template.replace('{req_clr}', required_clr) \
                       .replace('{det_clr}', detected_clr) \
                       .replace('{det_css}', detected_css) \
                       .replace('{clr_install}', clr_install)

    # -----------------
    def on_activated(self, view):
        file = view.file_name()
        if file and file.lower().endswith('.cs'):
            last_run_version = settings().get('last_run_version', 'unknown')
            just_installed = last_run_version == 'unknown';

            if just_installed:
                sublime.set_timeout_async(self.show_readme, 500)
            elif last_run_version != csscript_setup.version:
                sublime.set_timeout_async(self.show_release_notes, 500)

            settings().set('last_run_version', csscript_setup.version)
            settings().set('cscs_path', Runtime.cscs_path)
            settings().set('syntaxer_path', Runtime.syntaxer_path)
            save_settings()
    # -----------------
    def show_readme(self):
        # print('csscript_help')
        # sublime.error_message('Readme.md')
        sublime.active_window().run_command("csscript_help")
    # -----------------
    def show_release_notes(self):
        # print('show_release_notes')
        release_notes = os.path.join(plugin_dir, 'docs', 'release_notes.md')

        if os.path.exists(release_notes):
            sublime.active_window().open_file(release_notes)
    # -----------------
    def prepare_readme():
        readme = os.path.join(plugin_dir, 'readme.md')

        readme_template = os.path.join(plugin_dir, 'docs', 'readme.tmpl.md')
        template = ''

        with open(readme_template, "r") as f:
            templete = f.read()

        content = templete.replace('{SYS_REQ}', csscript_setup.get_sysconfig_description())

        with open(readme, "w", encoding="utf-8") as f:
            f.write(content)

        return readme
    # -----------------
    def prepare_css_help():

        readme = os.path.join(plugin_dir, 'cs-script.help.txt')

        with open(readme, "w") as f:
            popen_redirect_tofile([Runtime.cscs_path, "-help"], f).wait()

        return readme
