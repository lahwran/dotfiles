
" Vim syntax file
" Language:	Cuda C++

if exists("b:current_syntax")
  finish
endif

let b:current_syntax = ''
unlet b:current_syntax
runtime! syntax/cuda_cpp.vim

let s:path = fnameescape(fnamemodify(resolve(expand('<sfile>:p')), ':h'))
execute 'source '.s:path.'/_nested_py.vim'

let b:current_syntax = 'nested_py_cuda_cpp'
