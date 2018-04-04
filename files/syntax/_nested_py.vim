let b:current_syntax = ''
unlet b:current_syntax

syntax include @Python syntax/python.vim
syntax region pythonCode matchgroup=pyStringDelimiter start="\\begin{python}" end="\\end{python}" contains=@Python
syn region pyRawString	matchgroup=pyRawStringDelimiter start=+\%(u8\|[uLU]\)\=R"\z(py\|python\)(+ end=+)\z1"+  contains=@Python

hi! def link pyRawStringDelimiter Delimiter
hi! def link pyRawString Normal
