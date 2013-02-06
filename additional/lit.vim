if exists("b:current_syntax")
    finish
endif

" main syntax is rst
runtime! syntax/rst.vim

" the syntax files depend on that the current_syntax parameter isn't set
unlet b:current_syntax

" define a region in which the python syntax is used
syntax include @python $VIMRUNTIME/syntax/python.vim
syntax region rgnPython matchgroup=Quote start="^%<<.*" end="^%>>.*" keepend contains=@python

" also highlight the start and end patterns
highlight link Quote keyword

" this syntax is called lit
let b:current_syntax = "lit"
