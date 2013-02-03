import ast
import meta
import collections

class LitVisitor(object):
    """ special ast visitor, parses code chunks from string into single code
    objects do not set maxdepth bigger than 1, except you know what you do, but
    probaly the compilation will fail"""

    def __init__(self,maxdepth=1):
        self.maxdepth = maxdepth
        self.CodeChunk = collections.namedtuple('CodeChunk',['codeobject','source'])

    def _compile(self,node):
        codeobject = compile(ast.Module([node]),"<string>",'exec')
        source = meta.asttools.dump_python_source(node)
        return self.CodeChunk(codeobject,source)

    def visit(self, node, depth=0):
        """Visit a node."""

        if depth >= self.maxdepth:
            yield self._compile(node)
        else:
            depth += 1
            for child in ast.iter_child_nodes(node):
                yield from self.visit(child,depth=depth)

