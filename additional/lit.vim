" Remove any old syntax stuff hanging around
if version < 600
  syntax clear
endif
if exists("b:current_syntax")
    finish
endif

" main syntax is rst
runtime! syntax/rst.vim

" the syntax files depend on that the current_syntax parameter isn't set
if exists("b:current_syntax")
    unlet b:current_syntax
endif
" define a region in which the python syntax is used
syntax include @python syntax/python.vim
syntax region rgnPython matchgroup=Quote start="^%<.*$" end="^%>.*$" keepend containedin=ALL contains=@python

" also fold the chunks
set foldmethod=syntax
syntax region rgnPython start="^%<.*$" end="^%>.*$" transparent fold containedin=ALL keepend

" also highlight the start and end patterns
highlight link Quote SpecialComment

"
" this syntax is called lit
let b:current_syntax="lit"
