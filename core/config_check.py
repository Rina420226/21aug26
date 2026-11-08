"""Startup validation: one clear message instead of a cryptic ValueError traceback."""


def find_problems(env, required, int_vars=()):
    problems = []
    for name in required:
        if not str(env.get(name, "")).strip():
            problems.append(f"{name} is missing")
    for name in int_vars:
        v = str(env.get(name, "")).strip()
        if v:
            try:
                int(v)
            except ValueError:
                problems.append(f"{name} must be a number (got {v!r})")
    return problems
