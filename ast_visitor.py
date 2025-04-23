import ast

class MyVisitor(ast.NodeVisitor):
 
    def __init__(self):
        self.args = dict()
 
    def visit_Call(self, node: ast.Call):
        self.function_name = node.func.id
        self.generic_visit(node)

    def visit_keyword(self, node: ast.keyword):
        if type(node.value) is ast.List:
            self.args[node.arg] = []
            for const_ in node.value.elts:
                self.args[node.arg].append(const_.value)
        else:
            self.args[node.arg] = node.value.value