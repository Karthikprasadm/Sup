Tiny App Tutorial: Todo CLI
===========================

In this tutorial we’ll build a tiny Todo CLI in SUP that supports adding, listing, and completing items.

Prerequisites
-------------
- Install SUP: `pip install sup-lang`

Project setup
-------------
Create `todo.sup`:
```
sup
  # Initialize an empty list (grammar requires at least one item)
  make list of 0
  set todos to the list
  pop from todos

  define function called add with text
    push text to todos
    print concat of "Added: " and text
  end function

  define function called list
    for each item in todos
      print item
    end for
  end function

  define function called done with index
    set n to subtract 1 from index  # convert 1-based to 0-based
    print concat of "Done: " and get n from todos
  end function

  # Simple router using args
  set cmd to args get of 0
  if cmd is equal to "add" then
    set text to args get of 1
    call add with text
  else if cmd is equal to "list" then
    call list
  else if cmd is equal to "done" then
    set idx to args get of 1
    call done with idx
  else
    print "Usage: sup todo.sup [add TEXT|list|done INDEX]"
  end if
bye
```

Run
---
```
sup todo.sup add "buy milk"
sup todo.sup add "write code"
sup todo.sup list
sup todo.sup done 1
```

Going further
-------------
- Persist to disk: use `write file of PATH and DATA` and `read file of PATH` with `json stringify/parse`.
- Packaging: transpile to Python and wrap with a launcher script.


