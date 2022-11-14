# CoPyCat - Another Enhanced Interactive Python Shell
[![][1]][2] [![][3]][4] ![][5] ![][6]
## Features
- Dual panes, one for input and the other for output
- Automatically assign the value of any top-level expression to an unused
  variable, print the type of the value to the input pane, and pretty-print the
  value to the output pane
- Automatically import stdlib and 3rd-party libraries on demand
- List public, private or magic members of any object
- Browse source code of modules, classes, functions and exceptions in VS Code
- Early-stopping on the first exception when multiple lines are pasted
- Ready for `pdb` and NumPy
## Dependencies
- Windows >= 10.0.10586.0
- Python >= 3.10.0
- `cat` from Cygwin, WSL or somewhere else  
  If you are using WSL, replace `'cat'` with `'wsl -e cat'` in the source  
  In fact, a full-featured `cat` is unnecessary.
  If you have a C compiler installed, simply compile [this][7]
- NumPy >= 1.21.3
- VS Code (Optional, for code navigation)  
  `code.cmd` or `code-insiders.cmd` should exist in `PATH`
## Usage
### Launch
There are various ways to launch `copycat`:
```powershell
PS D:\> # Run as `__main__`
PS D:\> python copycat.py
```
```powershell
PS D:\> # Register as `PYTHONSTARTUP`
PS D:\> $Env:PYTHONSTARTUP = Convert-Path copycat.py
PS D:\> python
```
```py
>>> # Import from Python REPL
>>> import copycat
>>> # All features are available in `__main__` now
```
```py
# Add these lines to the end of your script
if __name__ == '__main__':
    try:
        main()
    finally:
        import copycat # DO NOT import it too early!
```
You can choose any one that you prefer.
### Automatic Assignment and Type Annotation
```py
>>> # The value of the expression will be printed to `cat` using `pprint`,
>>> # while the annotation printed to Python REPL.
>>> tuple(range(2))
q: tuple[Literal[0], Literal[1]]
>>> # Occupied name will be skipped
>>> w = 3
>>> vars(object)
e: mappingproxy[str, Any]
>>> q * w
r: tuple[int, ...]
```
### Automatic Lazy Import
```py
>>> # Standard library
>>> # Submodules are fine (same for the examples below)
>>> http.client.HTTP_PORT
t: Literal[80]
>>> # Well-known alias of 3rd-party library
>>> plt.figure()
y: Figure
>>> # Use object `m` to import any module
>>> m.click
u: module
```
### Member Inspection
```py
>>> # Print public, private or magic members of `__main__`
>>> publics()
>>> privates()
>>> magics()
>>> # Print public, private or magic members of `y`
>>> publics(y)
>>> privates(y)
>>> magics(y)
>>> # Print keys and value types of `e`
>>> items(e)
```
### Source Code Navigation
```py
>>> # Open '__init__.py' of the package
>>> source(u)
>>> # Go to the implementation of `source` itself
>>> source(source)
>>> # classes and functions written in C are unsupported
>>> source(int)
# TypeError: <class 'int'> is a built-in class
>>> # Go where the exception was raised, equivalent to `source(-1)`
>>> source()
>>> # ... or one level outer
>>> source(-2)
```
## Tips and Tricks
### Debugging
- When you get an exception, type `pdb.pm()` to debug immediately
  (`pdb` will be automatically imported).
- `publics`, `privates`, `magics`, `items` and `source` are available in the
  debugger (as functions, not commands). If you call `publics`, `privates` or
  `magics` without arguments, the current local namespace will be inspected.
- If the traceback in `cat` has been wiped out and you want to print it again,
  the command `w(here)` is what you need.
- Use the command `q(uit)` or Ctrl+Z to quit from the debugger and
  continue your work.
### [Windows Terminal][8] Integration
- On Windows 11, if Windows Terminal (stable or preview) is set to default
  terminal, `cat` will be opened inside.
- You can use the action `movePane` to move Python and `cat` to the same tab.
- With Windows Terminal >= 1.13.10336.0, you can use the action `exportBuffer`
  to save current contents of `cat` as a file.
## Configuration
In consideration of performance, there is no plan for any means of
configuration. Please modify the code in place.
## Limitations
- Only outputs of `publics`, `privates`, `magics`, `items`, `sys.displayhook`
  and `sys.excepthook` will go to `cat`. `cat` is not a good place for other
  outputs, since `sys.ps1` wipes out it every time.
- There are many cases that can cause unexpected word wrap in `cat`, such as
  full-width characters, `numpy.ndarray` inside containers, and narrower pane
  of `cat` compared with that of Python.
- If `sys.displayhook` is invoked more than once after one time of input, all
  previous results will be lost. The behavior is by design. Otherwise, you
  would have to write like `_ = non_None_expression_with_side_effects`
  to suppress outputs from a loop.

[1]: https://img.shields.io/badge/license-GPL--2.0--only-blue.svg
[2]: https://github.com/snekdesign/copycat/blob/main/LICENSE#L1-L339
[3]: https://img.shields.io/badge/license-Anti--996-blue.svg
[4]: https://github.com/snekdesign/copycat/blob/main/LICENSE#L343-L388
[5]: https://img.shields.io/badge/platform-windows-lightgrey.svg
[6]: https://img.shields.io/badge/python-3.10_%7C_3.11-blue.svg
[7]: https://rosettacode.org/wiki/Copy_stdin_to_stdout#C
[8]: https://github.com/microsoft/terminal
