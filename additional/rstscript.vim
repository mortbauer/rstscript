if !has('python3')
    echo "Error: Required vim compiled with +python"
    finish
endif

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
    exec ":au BufWritePost" bufname("%") ":call rstscript#RunLitrunner()"
endfun

