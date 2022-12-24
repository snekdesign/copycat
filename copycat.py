__author__ = 'snekdesign'
__version__ = '2022.12.24'
__doc__ = f"""CoPyCat {__version__}
Copyright (c) 2022 {__author__}

See https://github.com/{__author__}/copycat for more information."""
__all__ = ()

import atexit
import builtins
import collections
import ctypes.wintypes
import inspect
import itertools
import keyword
import msvcrt
import operator
import os
import pprint
import re
import reprlib
import shutil
import subprocess
import sys
import textwrap
import traceback
import types
import warnings
import __main__ as _main

import numpy as np

_QWERTY = 'qwertyuiopasdfghjklzxcvbnm'
_SENTINEL = object()


def displayhook(value):
    global _last_value
    _last_value = value


def excepthook(et, exc, tb):
    _cat_ready()
    traceback.print_exception(et, exc, tb, file=_cat_wrapper)
    ctypes.windll.kernel32.FlushConsoleInputBuffer(_stdin_handle)


def items(mapping):
    _cat_ready()
    for key, value in sorted(mapping.items()):
        if type(key) is not str:
            raise TypeError(f'key {reprlib.repr(key)} is not a string')
        _annotate(key, value)


def magics(obj=_SENTINEL):
    _inspect(obj, magic=True)


def privates(obj=_SENTINEL):
    _inspect(obj, private=True)


def publics(obj=_SENTINEL):
    _inspect(obj, public=True)


if _vscode := shutil.which('code') or shutil.which('code-insiders.cmd'):
    def source(obj=-1):
        if type(obj) is int:
            frame = inspect.getinnerframes(sys.last_traceback)[obj]
            filename = frame.filename
            lineno = frame.lineno
        else:
            obj = inspect.unwrap(obj)
            _, lineno = inspect.getsourcelines(obj)
            filename = inspect.getsourcefile(obj)
        subprocess.run([_vscode, '-g', f'{filename}:{lineno}'])
else:
    def source(obj):
        raise FileNotFoundError('code')


class _LazyModule(types.ModuleType):
    __repr__ = object.__repr__

    def __getattr__(self, name):
        module = _auto_import(self.__name__)
        try:
            _, attr = self.__name__.split('.', 1)
        except ValueError:
            pass
        else:
            module = operator.attrgetter(attr)(module)
        _maybe_set_back(_lazy_modules[self], module)
        return getattr(module, name)


class _ModuleImporter:
    def __getattr__(self, name):
        module = _auto_import(name)
        _maybe_set_back(name, module)
        return module


class _PrettyPrinter(pprint.PrettyPrinter):
    _dispatch = pprint.PrettyPrinter._dispatch.copy()

    def _pprint_ndarray(self, obj, stream, indent, allowance, context, level):
        linewidth = self._width - indent - allowance
        if newline := linewidth<75:
            linewidth = self._width
        with np.printoptions(linewidth=linewidth):
            text = repr(obj)
        if newline:
            stream.write('\n')
        elif indent:
            text = textwrap.indent(text, ' '*indent, text.find)
        stream.write(text)

    _dispatch[np.ndarray.__repr__] = _pprint_ndarray


class _PrimaryPS1:
    def __str__(self):
        if sys._getframe().f_back is None:
            try:
                _init()
                sys.ps1 = _SecondaryPS1()
            except:
                sys.ps1 = '>>> '
                sys.__excepthook__(*sys.exc_info())
        return '>>> '


class _SecondaryPS1:
    def __str__(self):
        global _last_value
        try:
            _ps1_impl()
        except:
            sys.last_type, sys.last_value, sys.last_traceback = sys.exc_info()
            # _ps1_impl() has cleared the screen, so just print the exception
            traceback.print_exc(file=_cat_wrapper)
            ctypes.windll.kernel32.FlushConsoleInputBuffer(_stdin_handle)
        _last_value = None
        _cat_wrapper.flush()
        return '>>> '


def _annotate(key, value):
    if not key.isidentifier() or keyword.iskeyword(key):
        raise ValueError(f'{reprlib.repr(key)} is not a valid identifier')
    _cat_wrapper.writelines([key, ': ', _repr(value), '\n'])


def _auto_import(name, globals_=None, level=0):
    try:
        module = __import__(name, globals_, None, (), level)
    except ImportError as e:
        if level:
            try:
                message = f"{globals_['__name__']}.{name}"
            except KeyError:
                message = name
        else:
            message = str(e)
            with warnings.catch_warnings():
                warnings.simplefilter('always')
                warnings.warn(message, ImportWarning, stacklevel=2)
        raise AttributeError(message) from None
    if not hasattr(module, '__getattr__'):
        def __getattr__(name):
            return _auto_import(name, _module_vars(module), 1)
        module.__getattr__ = __getattr__
    return module


def _cat_clear_screen():
    if _cat.poll() is not None:
        os._exit(_cat.returncode or 1)
    _cat_wrapper.write('\x1bc')


def _cat_ready():
    global _cat_called
    _cat_clear_screen()
    _cat_called = True


def _init():
    # Don't leak this to potential child processes
    del os.environ['PYTHONINSPECT']

    for cls in list, set, frozenset, collections.deque:
        _dispatch[cls] = _repr_collection
    for cls in bool, bytes, complex, float, int, range, str:
        _dispatch[cls] = _repr_literal
    for cls in (dict, collections.ChainMap, collections.Counter,
                collections.defaultdict, collections.OrderedDict,
                types.MappingProxyType):
        _dispatch[cls] = _repr_mapping
    for cls in (np.ndarray, np.chararray, np.matrix, np.memmap, np.recarray,
                np.ma.MaskedArray, np.ma.mvoid):
        _dispatch[cls] = _repr_ndarray

    for func in publics, privates, magics, items, source:
        _builtin_dict.setdefault(func.__name__, func)

    for name in itertools.filterfalse(_main_dict.__contains__,
                                      sys.stdlib_module_names):
        try:
            _main_dict[name] = sys.modules[name]
        except KeyError:
            _main_dict[name] = module = _LazyModule(name)
            _lazy_modules[module] = name

    for alias, fullname in [
        # Add your aliases here
        ('ds', 'pyarrow.dataset'),
        ('ET', 'xml.etree.ElementTree'),
        ('F', 'torch.nn.functional'),
        ('LA', 'numpy.linalg'),
        ('mp', 'multiprocessing'),
        ('mpl', 'matplotlib'),
        ('nn', 'torch.nn'),
        ('pa', 'pyarrow'),
        ('pc', 'pyarrow.compute'),
        ('pd', 'pandas'),
        ('plt', 'matplotlib.pyplot'),
        ('pq', 'pyarrow.parquet'),
        ('scipy', 'scipy'),
        ('sklearn', 'sklearn'),
        ('sm', 'statsmodels.api'),
        ('sns', 'seaborn'),
        ('torch', 'torch'),
        ('tsa', 'statsmodels.tsa.api'),
        ('xr', 'xarray'),
    ]:
        if alias not in _main_dict:
            _main_dict[alias] = module = _LazyModule(fullname)
            _lazy_modules[module] = alias

    globals_ = globals()
    for name in itertools.filterfalse(_main_dict.__contains__, _main_publics):
        _main_dict[name] = globals_[name]

    np.set_printoptions(precision=4, suppress=True, floatmode='maxprec')
    sys.displayhook = displayhook
    sys.excepthook = excepthook
    sys.modules['__main__'] = __main__


def _inspect(obj, public=False, private=False, magic=False):
    _cat_ready()
    _inspect_impl(obj, public, private, magic)
    _cat_wrapper.flush() # Required for pdb


def _inspect_impl(obj, public, private, magic):
    if magic:
        pattern = r'__[^_].*[^_]__$'
        extra = ()
    else:
        pattern = r'[^_]' if public else r'_(?!_.*__$)'
        extra = ('__getattribute__', '__getattr__')
    predicate = re.compile(pattern).match

    if obj is _SENTINEL:
        frame = sys._getframe(3)
        obj_dict = frame.f_locals
        if frame.f_globals is not obj_dict:
            for key in sorted(filter(predicate, obj_dict)):
                _annotate(key, obj_dict[key])
            return
        obj = sys.modules[obj_dict['__name__']]
        if _module_vars(obj) is not obj_dict:
            _cat_wrapper.write('Bad namespace')
            return

    mro = _getmro(type(obj))
    if inspect.isclass(obj):
        seen = set()
        for cls in _getmro(obj):
            _summary(cls, _type_vars(cls), predicate, extra)
            seen.add(cls)
        for cls in itertools.filterfalse(seen.__contains__, mro):
            _summary(cls, _type_vars(cls), predicate, extra)
        return

    if inspect.ismodule(obj):
        obj_dict = _module_vars(obj)
        pred = predicate
        if public or private:
            try:
                all_ = set(obj_dict['__all__'])
            except KeyError:
                pass
            else:
                if public:
                    all_.discard('__getattr__')
                    predicate = all_.__contains__
                else:
                    def predicate(name):
                        if name in all_:
                            return False
                        if name.startswith('__') and name.endswith('__'):
                            return False
                        return True
        _summary('self', obj_dict, predicate, extra[1:])
        for cls in mro:
            _summary(cls, _type_vars(cls), pred, extra)
        return

    for cls in mro:
        try:
            desc = _type_vars(cls)['__dict__']
        except KeyError:
            pass
        else:
            if (inspect.isgetsetdescriptor(desc)
                    and desc.__name__ == '__dict__'
                    and desc.__objclass__ is cls):
                _summary('self', desc.__get__(obj), predicate, ())
                break
    for cls in mro:
        _summary(cls, _type_vars(cls), predicate, extra)


def _maybe_set_back(name, module):
    try:
        value = _main_dict[name]
    except KeyError:
        _main_dict[name] = module
    else:
        if isinstance(value, _LazyModule):
            _main_dict[name] = module


def _ps1_impl():
    global _cat_called
    if _cat_called:
        _cat_called = False
        return
    _cat_clear_screen()
    if _last_value is None:
        return
    _printer._width = max(shutil.get_terminal_size().columns, 80)
    try:
        _printer.pprint(_last_value)
    except Exception as e:
        tb = e.__traceback__.tb_next
        while tb and inspect.getsourcefile(tb) == pprint.__file__:
            tb = tb.tb_next
        sys.last_type = type(e)
        sys.last_value = e.with_traceback(tb)
        sys.last_traceback = tb
        _cat_clear_screen()
        _cat_wrapper.write('Object not printable\n\n')
        traceback.print_exception(e, file=_cat_wrapper)
        ctypes.windll.kernel32.FlushConsoleInputBuffer(_stdin_handle)

    if sys._getframe(1).f_back:
        return
    for obj in _main_values:
        if _last_value is obj:
            return
    for obj in _builtin_values:
        if _last_value is obj:
            return
    name = next(_varnames)
    _main_dict[name] = _last_value
    _main_publics.append(name)
    sys.__stdout__.writelines(['\x1b[93m', name, ': ', _repr(_last_value),
                               '\x1b[0m\n'])


def _repr(obj):
    cls = type(obj)
    name = cls.__name__
    try:
        dispatch = _dispatch[cls]
    except KeyError:
        return name
    return dispatch(name, obj)


def _repr_collection(name, obj):
    return f'{name}[{_repr_union(obj)}]'


def _repr_literal(name, obj):
    return f'Literal[{reprlib.repr(obj)}]'


def _repr_mapping(name, obj):
    return f'{name}[{_repr_union(obj)}, {_repr_union(obj.values())}]'


def _repr_ndarray(name, obj):
    return f'{name}[Any, {type(obj.dtype).__name__}]'


def _repr_none(name, obj):
    return 'None'


def _repr_tuple(name, obj):
    if len(obj) > 5:
        return f'tuple[{_repr_union(obj)}, ...]'
    if obj:
        return f"tuple[{', '.join(map(_repr, obj))}]"
    return 'tuple[()]'


def _repr_type(name, obj):
    if obj is types.NoneType:
        return 'type[None]'
    return f'type[{obj.__name__}]'


def _repr_union(obj):
    if len(obj) == 1:
        return _repr(*obj) # obj[0] is not supported by set and frozenset
    classes = set(map(type, obj))
    if 0 < len(classes) < 6:
        none = True
        try:
            classes.remove(types.NoneType)
        except KeyError:
            none = False
        reprs = sorted(cls.__name__ for cls in classes)
        if none:
            reprs.append('None')
        return ' | '.join(reprs)
    return 'Any'


def _summary(obj, obj_dict, predicate, extra):
    if obj != 'self':
        obj = type.__repr__(obj)
    _cat_wrapper.writelines(['Members defined in ', obj, ': \n\n'])
    for key in sorted(filter(predicate, obj_dict)):
        _annotate(key, obj_dict[key])
    for key in extra:
        try:
            value = obj_dict[key]
        except KeyError:
            pass
        else:
            _annotate(key, value)
    _cat_wrapper.write('\n')


m = _ModuleImporter()

_console_mode = ctypes.wintypes.DWORD()
ctypes.windll.kernel32.GetConsoleMode(msvcrt.get_osfhandle(1),
                                      ctypes.byref(_console_mode))
if not _console_mode.value & 4: # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    raise OSError('VT sequences are disabled. You can enable them by setting '
                  r'HKCU\Console\VirtualTerminalLevel globally, or calling '
                  'SetConsoleMode() locally.'
                  if sys.getwindowsversion().build >= 10586 else
                  'Windows >= 10.0.10586.0 is required')

_getmro = type.__dict__['__mro__'].__get__
# _xxx_vars stands for callables, while _xxx_dict stands for dict instances
_type_vars = type.__dict__['__dict__'].__get__
_module_vars = types.ModuleType.__dict__['__dict__'].__get__
_builtin_dict = _module_vars(builtins)
_builtin_values = _builtin_dict.values()

__main__ = types.ModuleType('__main__', __doc__)
_main_dict = _module_vars(__main__)
_main_publics = ['m', 'np']
_main_values = _main_dict.values()
if __name__ == '__main__':
    __main__.__all__ = _main_publics
    __main__.__builtins__ = builtins
    # Avoid importing twice
    sys.modules['copycat'] = _main
    # Break reference cycle
    del _main
else:
    _main_dict |= _module_vars(_main)
    __main__.__all__ = _main_publics
    try:
        _main_publics += _main.__all__ # Duplicated entries are fine
    except AttributeError:
        pass

_varnames = itertools.repeat(('1234567890'+_QWERTY,))
_varnames = itertools.accumulate(_varnames, initial=(_QWERTY,))
_varnames = itertools.starmap(itertools.product, _varnames)
_varnames = itertools.chain.from_iterable(_varnames)
_varnames = map(''.join, _varnames)
_varnames = itertools.filterfalse(_builtin_dict.__contains__, _varnames)
_varnames = itertools.filterfalse(_main_dict.__contains__, _varnames)

_dispatch = {tuple: _repr_tuple, type: _repr_type, types.NoneType: _repr_none}
_last_value = None
_lazy_modules = {}
_stdin_handle = msvcrt.get_osfhandle(0)

_cat = subprocess.Popen('cat',
                        stdin=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        encoding='locale')
atexit.register(_cat.communicate)
_cat_called = False
_cat_wrapper = _cat.stdin
print(__doc__, file=_cat_wrapper, flush=True)
_printer = _PrettyPrinter(stream=_cat_wrapper)

os.environ['PYTHONINSPECT'] = '1'
sys.ps1 = _PrimaryPS1()
