import os
import shutil
import subprocess

from threading import Timer

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
  path = path.split('__SUBL__', 1)[1].strip('\r\n')
  return ':'.join(path.split(delim))

def find_path(env):
  # find PATH using shell --login
  if 'SHELL' in env:
    shell_path = env['SHELL']
    shell = os.path.basename(shell_path)

    if shell in ('bash', 'zsh'):
      return extract_path(
        (shell_path, '--login', '-c', 'echo __SUBL__$PATH')
      )
    elif shell == 'fish':
      return extract_path(
        (shell_path, '--login', '-c', 'echo __SUBL__; for p in $PATH; echo $p; end'),
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

    return (out[0] or '') + (out[1] or '')
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