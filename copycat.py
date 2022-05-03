__author__ = 'snekdesign'
__version__ = '2022.5.3'
__doc__ = f"""CoPyCat {__version__}
Copyright (c) 2022 {__author__}

See https://github.com/{__author__}/copycat for more information."""
__all__ = ['m', 'np']

import atexit
import builtins
import collections
import ctypes.wintypes
import inspect
import itertools
import msvcrt
import operator
import os
import pprint
import re
import shutil
import subprocess
import sys
import traceback
import types

import numpy as np

if __name__ == '__main__':
    __main__ = types.ModuleType('__main__', __doc__)
    __main__.__builtins__ = builtins
else:
    import __main__

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
            raise TypeError('all keys must be string')
        _annotate(key, value)


def magics(obj=_SENTINEL):
    _inspect(obj, magic=True)


def privates(obj=_SENTINEL):
    _inspect(obj, private=True)


def publics(obj=_SENTINEL):
    _inspect(obj, public=True)


if _vscode := shutil.which('code.cmd') or shutil.which('code-insiders.cmd'):
    def source(obj):
        obj = inspect.unwrap(obj)
        file = inspect.getsourcefile(obj)
        if not file:
            raise OSError('source code not available')
        _, line = inspect.getsourcelines(obj)
        subprocess.run([_vscode, '-g', f'{file}:{line}'])
else:
    def source(obj):
        raise FileNotFoundError('code.cmd')


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


class _PrimaryPS1:
    def __str__(self):
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
            excepthook(*sys.exc_info())
        _last_value = None
        _cat_wrapper.flush()
        return '>>> '


def _annotate(key, value):
    _cat_wrapper.writelines([key, ': ', _repr(value), '\n'])


def _auto_import(name, globals_=None, level=0):
    try:
        module = __import__(name, globals_, None, (), level)
    except ImportError:
        raise AttributeError from None
    if not hasattr(module, '__getattr__'):
        def __getattr__(name):
            return _auto_import(name, _module_dict(module), 1)
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
        ('nn', 'torch.nn'),
        ('pa', 'pyarrow'),
        ('pc', 'pyarrow.compute'),
        ('plt', 'matplotlib.pyplot'),
        ('pq', 'pyarrow.parquet'),
        ('scipy', 'scipy'),
        ('sklearn', 'sklearn'),
        ('sm', 'statsmodels.api'),
        ('torch', 'torch'),
        ('tsa', 'statsmodels.tsa.api'),
        ('xr', 'xarray'),
    ]:
        if alias not in _main_dict:
            _main_dict[alias] = module = _LazyModule(fullname)
            _lazy_modules[module] = alias

    globals_ = globals()
    for name in itertools.filterfalse(_main_dict.__contains__, __all__):
        _main_dict[name] = globals_[name]
        _main_all.append(name)

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
        if _module_dict(obj) is not obj_dict:
            _cat_wrapper.write('Bad namespace')
            return

    mro = _mro(type(obj))
    if inspect.isclass(obj):
        seen = set()
        for cls in _mro(obj):
            _summary(cls, _type_dict(cls), predicate, extra)
            seen.add(cls)
        for cls in itertools.filterfalse(seen.__contains__, mro):
            _summary(cls, _type_dict(cls), predicate, extra)
        return

    if inspect.ismodule(obj):
        obj_dict = _module_dict(obj)
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
            _summary(cls, _type_dict(cls), pred, extra)
        return

    for cls in mro:
        try:
            desc = _type_dict(cls)['__dict__']
        except KeyError:
            pass
        else:
            if (inspect.isgetsetdescriptor(desc)
                    and desc.__name__ == '__dict__'
                    and desc.__objclass__ is cls):
                _summary('self', desc.__get__(obj), predicate, ())
                break
    for cls in mro:
        _summary(cls, _type_dict(cls), predicate, extra)


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
    width = shutil.get_terminal_size().columns
    if width < 42:
        width = 80
    _printer._width = width
    np.set_printoptions(linewidth=width-5)
    _printer.pprint(_last_value)

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
    _main_all.append(name)
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
    repr_ = f'Literal[{obj!r}]'
    if len(repr_) > 42:
        return name
    return repr_


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

_mro = type.__dict__['__mro__'].__get__
_type_dict = type.__dict__['__dict__'].__get__
_module_dict = types.ModuleType.__dict__['__dict__'].__get__
_builtin_dict = _module_dict(builtins)
_builtin_values = _builtin_dict.values()
_main_dict = _module_dict(__main__)
_main_values = _main_dict.values()
_main_all = _main_dict.setdefault('__all__', [])
if not isinstance(_main_all, list):
    raise TypeError('__main__.__all__ must be a list')

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
_printer = pprint.PrettyPrinter(stream=_cat_wrapper)

os.environ['PYTHONINSPECT'] = '1'
sys.ps1 = _PrimaryPS1()