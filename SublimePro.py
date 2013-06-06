import sublime
import sublime_plugin
import sys
import os.path
import subprocess
import os
import shutil
import locale
from threading import Timer, Thread

SUBL_PATH = '../SharedSupport/bin/subl'
ENCODING = 'utf-8'


class OpenProCommand(sublime_plugin.WindowCommand):
    def run(self):
        t1 = Thread(target=self.open_project_panel)
        t1.start()

    def open_project_panel(self):
        projects = self.project_list()
        self.window.show_quick_panel(projects, self.on_done)

    def project_list(self):
        paths = self.project_paths()
        return [[os.path.basename(p), p] for p in paths]

    def project_paths(self):
        result = communicate(["pro","list"],timeout=2)
        self.projects = result.split("\n")
        return self.projects

    def on_done(self, picked):
        if picked == -1:
            return
        if self.projects:
            selpath = self.projects[picked]
            self.open_project(selpath)

    def open_project(self, path):
        sublime_command_line(['-n',path])


# hack to add folders to sidebar (stolen from wbond)
def get_sublime_path():
    if sublime.platform() == 'osx':
        base_dir = os.path.dirname(sublime.executable_path())
        return os.path.relpath(SUBL_PATH, base_dir)
    else:  # I hope this works on Windows and Linux
        return sublime.executable_path()


def sublime_command_line(args):
    args.insert(0, get_sublime_path())
    return subprocess.Popen(args)

# Command line utilities
def memoize(f):
    rets = {}

    def wrap(*args):
        if not args in rets:
            rets[args] = f(*args)

        return rets[args]

    wrap.__name__ = f.__name__
    return wrap

def extract_path(cmd, delim=':'):
    path = popen(cmd, os.environ).communicate()[0]
    path = path.decode('utf-8')
    path = path.split('__SUBL__', 1)[1].strip('\r\n')
    return ':'.join(path.split(delim))

def find_path(env):
  # find PATH using shell --login
  if 'SHELL' in env:
    shell_path = env['SHELL']
    shell = os.path.basename(shell_path)

    if shell in ('bash', 'zsh'):
      return extract_path(
        [shell_path, '--login', '-c', 'echo __SUBL__$PATH']
      )
    elif shell == 'fish':
      return extract_path(
        [shell_path, '--login', '-c', 'echo __SUBL__; for p in $PATH; echo $p; end'],
        '\n'
      )

  # guess PATH if we haven't returned yet
  split = env['PATH'].split(':')
  p = env['PATH']
  for path in (
    '/usr/bin', '/usr/local/bin',
    '/usr/local/php/bin', '/usr/local/php5/bin'
        ):
    if not path in split:
      p += (':' + path)

  return p

@memoize
def create_environment():
  if os.name == 'posix':
    os.environ['PATH'] = find_path(os.environ)

  return os.environ

def which(cmd, env=None):
  if env is None:
    env = create_environment()

  for path in env['PATH'].split(':'):
    full = os.path.join(path, cmd)
    if os.path.isfile(full) and os.access(full, os.X_OK):
      return full

# popen methods
def communicate(cmd, stdin=None, timeout=None, **popen_args):
  p = popen(cmd, **popen_args)
  if isinstance(p, subprocess.Popen):
    timer = None
    if timeout is not None:
      kill = lambda: p.kill()
      timer = Timer(timeout, kill)
      timer.start()

    out = p.communicate(stdin)
    if timer is not None:
      timer.cancel()

    return (out[0] or b'').decode(ENCODING) + (out[1] or b'').decode(ENCODING)
  elif isinstance(p, str):
    return p
  else:
    return ''

def popen(cmd, env=None, return_error=False):
  if isinstance(cmd, str):
    cmd = cmd,

  info = None
  if os.name == 'nt':
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE

  if env is None:
    env = create_environment()

  try:
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
      startupinfo=info, env=env)
  except OSError as err:
    print('Error launching', repr(cmd))
    print('Error was:', err.strerror)

    if return_error:
      return err.strerror
