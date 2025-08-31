Quickstart
==========

Install
-------
```
pip install sup-lang
```

From source (editable):
```
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Hello world
-----------
Scaffold a project:
```
sup init hello-sup
```

Or create a single file `hello.sup`:
Create `hello.sup`:
```
sup
  print "Hello, SUP!"
bye
```

Run:
```
sup hello.sup
```

Variables and arithmetic
------------------------
```
sup
  set x to add 2 and 3
  print the result
  print subtract 3 from x
bye
```

Control flow
------------
```
sup
  set n to 5
  if n is greater than 3 then
    print "big"
  else
    print "small"
  end if
bye
```

Functions
---------
```
sup
  define function called square with x
    return multiply x and x
  end function

  print call square with 7
bye
```

Errors and imports
------------------
```
sup
  try
    throw "oops"
  catch e
    print e
  finally
    print "done"
  end try
bye
```

Transpile to Python
-------------------
```
sup --emit python hello.sup
```

Project transpile (entry + imports)
-----------------------------------
```
sup transpile sup-lang/examples/06_mixed.sup --out dist_py
python dist_py/run.py
```

Formatter and linter
--------------------
```
supfmt path/to/program.sup
suplint path/to/program.sup
```

VS Code extension
-----------------
Install the SUP language support extension for syntax highlighting and snippets.


