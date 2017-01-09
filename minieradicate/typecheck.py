from minieradicate.analysis.nullability import NullabilityAnalysis


def check(function, globals):
    analysis = NullabilityAnalysis(function, globals)
    state, output = analysis.solve()
    print(output)
