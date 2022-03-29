import os
import io
import codecs
import sys
import sublime
import platform
import time
import sublime_plugin
import subprocess
from subprocess import Popen, PIPE, STDOUT
from os import path

import socket
import subprocess
import errno
from socket import error as socket_error
from .utils import *

out_panel = 'CS-Script'


# plugin_dir = path.dirname(path.dirname(__file__))
# Runtime.cscs_path = path.join(plugin_dir, 'bin', 'cscs.exe')

def syntaxer_print_config():
    print('syntaxer_cscs: ', Runtime.cscs_path)
    print('syntaxer_path: ', Runtime.syntaxer_path)
    print('syntaxer_port: ', Runtime.syntaxer_port)


def is_linux():
    return os.name == 'posix' and platform.system() == 'Linux'

# =================================================================================
# C# Syntax Server - service that any process can connect via socket and request
# intellisense queries
# =================================================================================

# -----------------
def to_args(args):
    # excellent discussion about why popen+shell doesn't work on Linux
    # http://stackoverflow.com/questions/1253122/why-does-subprocess-popen-with-shell-true-work-differently-on-linux-vs-windows
        
    if is_linux() and not is_mac():
        result = ''
        last_arg = args[0]
        # if last_arg.endswith('cscs.exe') or last_arg.endswith('syntaxer.exe') or last_arg.endswith('cscs.dll') or last_arg.endswith('syntaxer.dll'):
        #     result = 'mono '

        for arg in args:
            result = result + '"'+arg+'" '
        return [result.rstrip()]
    return args
# -----------------
def start_syntax_server():
    try:
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
        print('> Syntaxer server started:', time.time()-start, 'seconds')

        sublime.status_message('> Syntaxer server started...')
    except Exception as ex:
        print('Cannot start syntaxer server', ex)
        pass

# Start the server as soon as possible. If the server is already running the next call will do nothing.
# The server will terminate itself after the last client exits
# start_syntax_server()

# -----------------
def send_exit_request():
    try:
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(('localhost', Runtime.syntaxer_port))
        clientsocket.send('-exit'.encode('utf-8'))
    except socket_error as serr:
        pass
# -----------------
reconnect_count = 0
last_cscs_sent = None
def set_engine_path(cscs_path):
    if cscs_path:
        Runtime.cscs_path = cscs_path
        reconnect_count = 0
        # print('setting engine path')
        send_cscs_path(Runtime.cscs_path)

# -----------------
def preload_engine():
    try:
        args = []
        args.append(Runtime.cscs_path)
        args.append('-preload')
        args = to_args(args)
        start = time.time()
        subprocess.Popen(args, shell=True)
        print('> Roslyn preloading done:', time.time()-start, 'seconds')
    except:
        pass

# -----------------
def send_cscs_path(cscs_path):
    sublime.set_timeout_async(lambda: try_send_cscs_path(cscs_path), 3000)

def try_send_cscs_path(cscs_path):

    global reconnect_count
    global last_cscs_sent
    reconnect_count = reconnect_count + 1

    if last_cscs_sent == cscs_path:
        return

    try:
        start_time = time.time()
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(('localhost', Runtime.syntaxer_port))
        request = '-cscs_path:{0}'.format(cscs_path)
        clientsocket.send(request.encode('utf-8'))

        last_cscs_sent = cscs_path
        reconnect_count = 0
        print('> Connected to syntaxer server:', time.time()-start_time, 'seconds')

    except socket_error as serr:
        # send_cscs_path may be issued before server is ready for the connection
        # so we may need to retry

        last_cscs_sent = None

        if reconnect_count  < 5:
            print(serr)
            print('Cannot configure syntaxer server with cscs location. Schedule another attempt in 3 seconds.')
            sublime.set_timeout_async(try_send_cscs_path, 3000)

        else:
            # just give up. 5 sec should be enough to connect. Meaning there is something
            # more serious than server is not being ready.
            print(serr)
            print('Cannot configure syntaxer server with cscs location.')
            reconnect_count = 0

# -----------------
def send_pkill_request(pid, pname=None):
    try:
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(('localhost', Runtime.syntaxer_port))
        request = '-pkill\n-pid:{0}'.format(pid)
        if pname:
            request = request + '\n-pname:' + pname
        clientsocket.send(request.encode('utf-8'))
    except socket_error as serr:
        if serr.errno == errno.ECONNREFUSED:
            start_syntax_server()
# -----------------
def send_popen_request(command):
    try:
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(('localhost', Runtime.syntaxer_port))
        request = '-popen:{0}'.format(command)
        clientsocket.send(request.encode('utf-8'))
    except socket_error as serr:
        if serr.errno == errno.ECONNREFUSED:
            start_syntax_server()
# -----------------
def send_syntax_request(file, location, operation):
    try:
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect(('localhost', Runtime.syntaxer_port))
        request = '-client:{0}\n-op:{1}\n-script:{2}\n-pos:{3}'.format(os.getpid(), operation, file, location)
        clientsocket.send(request.encode('utf-8'))
        response = clientsocket.recv(1024*1024)
        return response.decode('utf-8')
    except socket_error as serr:
        if serr.errno == errno.ECONNREFUSED:
            start_syntax_server()
            # print(serr)
# -----------------
def send_formatting_request(file, location):
    return send_syntax_request(file, location, 'format')
# -----------------
def send_completion_request(file, location):
    print('send_completion_request')
    return send_syntax_request(file, location, 'completion')
# -----------------
def send_tooltip_request(file, location, hint, short_hinted_tooltips=True):
    args = 'tooltip:'+hint

    if short_hinted_tooltips:
        args = args + '\n-short_hinted_tooltips:1'
    else:
        args = args + '\n-short_hinted_tooltips:0'

    return send_syntax_request(file, location, args)
    # if short_hinted_tooltips:
    #     return send_syntax_request(file, location, 'short_hinted_tooltips:1\n-tooltip:'+hint)
    # else:
    #     return send_syntax_request(file, location, 'short_hinted_tooltips:0\n-tooltip:'+hint)

    # return send_syntax_request(file, location, 'tooltip:'+hint)
# -----------------
def send_resolve_request(file, location):
    return send_syntax_request(file, location, 'resolve')
# -----------------
def send_resolve_references(file, location):
    return send_syntax_request(file, location, 'references')
# -----------------
def send_resolve_using_request(file, word):
    return send_syntax_request(file, -1, 'suggest_usings:'+word)
# -----------------
def popen_redirect(args):
    all_args = to_args(args)
    cmd = ''
    for arg in all_args:
        cmd = cmd + '"'+arg+'" '
    # print('popen_redirect: ' + cmd)
    return subprocess.Popen(all_args, stdout=subprocess.PIPE, shell=True)
# -----------------
def popen_redirect_tofile(args, file):
    return subprocess.Popen(to_args(args), stdout=file, shell=True)

def popen_tofile(args, file):
 return subprocess.Popen(args, stdout=file, shell=True)

# -----------------
def run_doc_in_cscs(args, view, handle_line, on_done=None, nuget_warning = True):

    curr_doc = view.file_name()

    clear_and_print_result_header(curr_doc)

    if not path.exists(Runtime.cscs_path):
        print('Error: cannot find CS-Script launcher - ', Runtime.cscs_path)
    elif not curr_doc:
        print('Error: cannot find out the document path')
    else:

        clear_and_print_result_header(curr_doc)

        if nuget_warning and '//css_nuget' in view.substr(sublime.Region(0, view.size())):
            output_view_write_line(out_panel, "Resolving NuGet packages may take time...")

        def do():
            all_args = ['dotnet', Runtime.cscs_path]

            for a in args:
                all_args.append(a)

            all_args.append(curr_doc)

            proc = popen_redirect(all_args)

            first_result = True
            for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
                line = line.strip()
                if first_result:
                    first_result = False
                    clear_and_print_result_header(curr_doc)

                handle_line(line)

            if on_done:
                on_done()

        sublime.set_timeout(do, 100)
# -----------------
def run_cscs(args, handle_line, on_done=None, header=None):

    output_view_show(out_panel)
    output_view_clear(out_panel)
    if header:
        output_view_write_line(out_panel, header)
        output_view_write_line(out_panel, "------------------------------------------------------------------------")

    if not path.exists(Runtime.cscs_path):
        print('Error: cannot find CS-Script launcher - ', Runtime.cscs_path)
    else:
        def do():
            all_args = ['dotnet', Runtime.cscs_path]

            for a in args:
                all_args.append(a)

            proc = subprocess.Popen(all_args, stdout=subprocess.PIPE, shell=True)

            for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
                handle_line(line.strip())

            if on_done:
                on_done()

        sublime.set_timeout(do, 100)
# -------------
def clear_and_print_result_header(curr_doc):
    output_view_show(out_panel)
    output_view_clear(out_panel)

    simple_output_header = sublime.load_settings("cs-script.sublime-settings").get('simple_output_header', False)

    if not simple_output_header:
        output_view_write_line(out_panel, 'Script: '+ curr_doc)
        output_view_write_line(out_panel, "------------------------------------------------------------------------")

