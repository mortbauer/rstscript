if has('python') || has('python3')
    function! s:update_buffers(outputfile)
        try
            exec "checktime" a:outputfile
        catch
        endtry
    endfun

    function! rstscript#RunUpdate(outputfile)
        call rstscript#RunLitrunner()
        call s:update_buffers(a:outputfile)
    endfun
endif

if has('python3')
    " use run locally if compiled with python3
    python3 << EOF
import vim
import sys

sys.path.append('/data/devel/python/rstscript/rstscript-git')
from rstscript import main

try:
    projects
except:
    projects = {}
EOF

    function! rstscript#SetupLitrunner(outputfile)
    python3 << EOF
if not vim.current.buffer.name in projects:
    if vim.current.buffer.name:
        litrunner = main.client_main(['--no-daemon','-i',vim.current.buffer.name,'-ow',vim.eval("a:outputfile")])
        projects[vim.current.buffer.name] = litrunner
    else:
        print('doesn\'t support unnamed buffers yet')
else:
    print('already set up')
EOF
    endfun

    function! rstscript#RunLitrunner()
    python3 << EOF
if vim.current.buffer.name in projects:
    if projects[vim.current.buffer.name].run():
        print('run ended successfully')
    else:
        print('errors occured')
else:
    print('you need to invoke SetupLitrunner first')
EOF
    endfun

    function! RstscriptWatchCurrentBuffer(outputfile)
        call rstscript#SetupLitrunner(a:outputfile)
        augroup runupdate
            exec "autocmd BufWritePost <buffer> call rstscript#RunUpdate(\""eval('a:outputfile')"\")"
        augroup END
    endfun
elseif has("python")
    " use run locally if compiled with python3
    python << EOF
import vim
import sys

sys.path.append('/data/devel/python/rstscript/rstscript-git')
from rstscript import main

try:
    projects
except:
    projects = {}
EOF

    function! rstscript#SetupLitrunner(outputfile)
    python << EOF
if not vim.current.buffer.name in projects:
    projects[vim.current.buffer.name] = {'woutput':vim.eval('a:outputfile')}
EOF
    endfun

    function! rstscript#RunLitrunner()
    python << EOF
import subprocess
if vim.current.buffer.name in projects:
    subprocess.call(['rstscript','-i',vim.current.buffer.name,'-ow',projects[vim.current.buffer.name]])
    print('run ended')
else:
    print('you need to invoke SetupLitrunner first')
EOF
    endfun

    function! rstscript#WatchCurrentBuffer(outputfile)
        call rstscript#SetupLitrunner(a:outputfile)
        autocmd BufWritePost <buffer> call rstscript#RunUpdate(a:outputfile)
    endfun

else
    echo "Error: Required vim compiled with +python"
    finish
endif
