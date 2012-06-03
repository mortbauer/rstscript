############
`litscript` 
############

*******
Summary
*******
Write a document with inlined code chunks, which will get processed and
incorporated into the document.

********************
How it should behave
********************
* commandline script which accepts options 
* configuration via `/etc/litscript` respectively `$XDG_CONFIG_HOME/litscript` 
* plugins for individual processors * python library, for easy extensibility to
  even higher and better programmes, not among present imagination 
* separation of actual code and syntax, therefore easy extensibility to
  different markup languages, default restructuredText. This already refers to
  very convinient methodes like incorporating by codechunks produced images
  into the document, or also latex output, .... (extensible)

*****
Steps
*****
* find well programmed python commandline/library tool to serve as an example *
  use pweave from Matti Pastell and also it's several forks and mix them to one
  nice implementation
* focus on generality but only implement the default, like `rst` as markup, and
  python as processor, don't forget about problems like matlab, think about a
  general approach!
* use something similar to `noweb` syntax, but no inheritance, but use codechunk name/number to place it anywhere in a document (not multiple times, there should be just made a reference, in the syntax of the markup language)

*****
Notes
*****
* good script example is `alot`
