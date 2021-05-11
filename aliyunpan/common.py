__all__ = ['DATA', 'GLOBAL_VAR']


class DATA(dict):
    def __init__(self, seq=None, **kwargs):
        if not seq:
            seq = {}
        super(DATA, self).__init__(seq, **kwargs)
        for key, value in seq.items():
            if isinstance(value, dict):
                self[key] = DATA(value)
            else:
                self[key] = value

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            self[key] = DATA(value)
        else:
            self[key] = value

    def __delattr__(self, item):
        del self[item]

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            super(DATA, self).__setitem__(key, DATA(value))
        else:
            super(DATA, self).__setitem__(key, value)


GLOBAL_VAR = DATA()
GLOBAL_VAR.tasks = {}
