class DecoratorCompositor:
    def __init__(self):
        self.decorators = []

    @staticmethod   
    def from_list(decorator_list):
        stack = DecoratorCompositor()
        for dec in decorator_list:
            stack.add(dec)
        return stack
    
    def add(self, decorator):
        self.decorators.append(decorator)

    def apply(self, f):
        for dec in reversed(self.decorators):
            f = dec(f)
        return f
    
    def decorate(self):
        def decorator(f):
            return self.apply(f)
        return decorator
    