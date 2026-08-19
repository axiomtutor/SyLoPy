


class TypecheckError(Exception):
    pass


class Term:
    def __eq__(self, other):
        if not isinstance(other, Term):
            return False
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        raise NotImplementedError("Subclasses of Term must implement __repr__")

    def is_constant(self):
        return False

    def is_variable(self):
        return False

    def is_function(self):
        return False

class ConstantTerm(Term):
    def __init__(self, name, value):
        if not isinstance(name, str):
            raise TypecheckError("Constant term name must be a string")
        if name == "":
            raise TypecheckError("Constant term name cannot be empty")
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return self.name

    def is_constant(self):
        return True

class VariableTerm(Term):
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypecheckError("Variable term name must be a string")
        if name == "":
            raise TypecheckError("Variable term name cannot be empty")
        self.name = name

    def __repr__(self) -> str:
        return self.name

    def is_variable(self):
        return True

class FunctionTerm(Term):
    def __init__(self, symbol, args):
        if not isinstance(symbol, str):
            raise TypecheckError("Function symbol must be a string")
        if symbol == "":
            raise TypecheckError("Function symbol cannot be empty")
        if not isinstance(args, (list, tuple)):
            raise TypecheckError("Function arguments must be a list or tuple")
        for arg in args:
            if not isinstance(arg, Term):
                raise TypecheckError("Function arguments must be Term instances")

        self.symbol = symbol
        self.args = list(args)

    def __repr__(self) -> str:
        args_repr = ", ".join(repr(arg) for arg in self.args)
        return f"{self.symbol}({args_repr})"

    def is_function(self):
        return True

    def arity(self):
        return len(self.args)

def evaluate_term(term, substitution_schema=None):
    if not isinstance(term, Term):
        raise TypecheckError("evaluate_term requires a Term instance")

    if substitution_schema is None:
        substitution_schema = {}

    if term.is_constant():
        return term.value

    if term.is_variable():
        if term.name not in substitution_schema:
            raise TypecheckError(f"Variable '{term.name}' not found in substitution schema")
        replacement = substitution_schema[term.name]
        return replacement

    if term.is_function():
        evaluated_args = [evaluate_term(arg, substitution_schema) for arg in term.args]
        if term.symbol not in substitution_schema:
            raise TypecheckError(f"Function symbol '{term.symbol}' not found in substitution schema")
        func = substitution_schema[term.symbol]
        if not callable(func):
            raise TypecheckError("Function symbol mapping must be callable")
        return func(*evaluated_args)

    raise TypecheckError("Unknown Term subtype")

if __name__ == "__main__":
    # Constants and variables
    a = ConstantTerm("a", 3)
    b = ConstantTerm("b", 5)
    x = VariableTerm("x")
    y = VariableTerm("y")

    print("Constant a:", a, "value=", a.value)
    print("Variable x:", x)

    # A simple function term f(x, a)
    f_term = FunctionTerm("f", [x, a])
    print("Function term:", f_term)

    # Substitute x -> b, and associate f with a callable
    subs = {
        "x": 1,
        "f": lambda x_val, a_val: x_val + a_val
    }
    print("Substitution schema:", subs)
    evaluated_f = evaluate_term(f_term, substitution_schema=subs)
    print("Evaluated f(x,a) with x=b:", evaluated_f)

    print(evaluate_term(x, subs)) 
    print(evaluate_term(a, subs))




