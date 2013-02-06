
if exists("b:current_syntax")
    finish
endif

" main syntax is rst
runtime! syntax/rst.vim

" the syntax files depend on that the current_syntax parameter isn't set
unlet b:current_syntax

" define a region in which the python syntax is used
syntax include @python $VIMRUNTIME/syntax/python.vim
syntax region rgnPython matchgroup=Quote start="^%<<.*>>=" end="^%>>" keepend contains=@python

" also highlight the start and end patterns
highlight link Quote keyword

" this syntax is called lit
let b:current_syntax = "lit"

" from here on only convinient stuff, which would better belong into a own
" plugin  but not a syntax file
"
" Processes the document until the final pdf
fun! PweaveRST2PDF()
  silent !(pweave -f rst % &> %:t:r.err;rst2pdf %:t:r.rst &>> %:t:r.err) &
 redraw!
endfun
map <Leader>p :w<CR>:call PweaveRST2PDF()<CR>

fun! PweavePDFLATEX()
 silent !(pweave -f rst % &> %:t:r.err;rst2latex --literal-block-env=minted[framesep=2mm,frame=lines,mathescape]{python} --latex-preamble='\usepackage{minted}' %:t:r.rst %:t:r.tex &>> %:t:r.err; pdflatex -shell-escape %:t:r.tex &>> %:t:r.err ) &
 redraw!
endfun
map <Leader>l :w<CR>:call PweavePDFLATEX()<CR>


map <Leader>k :w<CR>:!'/data/virtualenv/doc3/bin/rstwizard' %<CR>
map <Leader>d :w<CR>:!'/data/virtualenv/doc3/bin/litscript' -ow %:t:r.rst %<CR><CR>
map <Leader>t :w<CR>:!'/data/virtualenv/doc3/bin/litscript' -ot %:t:r.rst %<CR><CR>

"
" Looks for errors in the generated .err file, very shitty so far
fun! PweaveCopen()
  vimgrep /\(error\|exception\)/gj %:t:r.err
  copen
endfun
map <Leader>a :call PweaveCopen()<CR>

" from: http://blog.tuxcoder.com/2008/12/11/vim-restructuretext-macros/
" Restructured Text
" #########################
" Ctrl-u 1:    underline Parts w/ #'s
noremap  <C-u>1 yypVr#
inoremap <C-u>1 <esc>yypVr#A
" Ctrl-u 2:    underline Chapters w/ *'s
noremap  <C-u>2 yypVr*
inoremap <C-u>2 <esc>yypVr*A
" Ctrl-u 3:    underline Section Level 1 w/ ='s
noremap  <C-u>3 yypVr=
inoremap <C-u>3 <esc>yypVr=A
" Ctrl-u 4:    underline Section Level 2 w/ -'s
noremap  <C-u>4 yypVr-
inoremap <C-u>4 <esc>yypVr-A
" Ctrl-u 5:    underline Section Level 3 w/ ^'s
noremap  <C-u>5 yypVr^
inoremap <C-u>5 <esc>yypVr^A

"let g:tcommentGuessFileType=1
