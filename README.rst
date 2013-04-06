RstScript
#########

.. image:: https://travis-ci.org/mortbauer/rstscript.png?branch=master

Markup in `rest`_ and code in `python`_.

RstScript has its own syntax, don't worry it is really tiny, which allows you
to integrate your python scripts, and more important results in your ``rest``
document. It is intended to use for some calculation scripts, as it has
features like auto printing of variables, automatic saving and include of
produced `matplotlib`_ plots.

It is inspired by `sweave`_ and `pweave`_ but tries to be much faster, robust
and extensible.

Currently in early development, so don't blame me for any shit.

Snippet
*******
The following ``RstScript`` snippet::
  
  A very basic RstScript example
  ##############################

  %<{"a":True,"e":True}
  a = 'Hello World'
  b = 6
  c = b * 7
  print(a)
  %>

  This is some `rest`_ with embeded code chunks.

would render to::

  A very basic RstScript example
  ##############################

  .. code-block:: python

    a = 'Hello World'
    b = 6
    c = b * 7
    c = 42
    print(a)
    Hello World

  This is some `rest`_ with embeded code chunks.

.. _installation:

Installation
************
Just fetch the source, and run ``python setup.py install``.

Requirements
************
The `installation`_ will take care about the requirements, but to be complete
here the requirements:

* argparse
* meta

optionally, but highly recommended for usage:

* matplotlib

Similar Projects
****************
* `doconce`_
* `pweave`_
* `sweave`_ for R
* `knitr`_ for R

Python Compatibility Note
*************************
This package currently only support the `python3`_. But it my be easy to archive
backwards compatibility to `python2.7`_.

.. _rest: http://docutils.sourceforge.net/rst.html
.. _python: http://www.python.org/
.. _matplotlib: http://matplotlib.org/
.. _sweave: http://www.stat.uni-muenchen.de/~leisch/Sweave/
.. _pweave: http://mpastell.com/pweave/
.. _knitr: http://yihui.name/knitr
.. _doconce: http://code.google.com/p/doconce/
.. _python3: http://docs.python.org/3/
.. _python2.7: http://docs.python.org/2.7/
