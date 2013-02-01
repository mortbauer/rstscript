"""
A dictionary difference calculator
Shamelessly stolen from: https://github.com/hughdbrown/dictdiffer
Originally posted as:
http://stackoverflow.com/questions/1165352/fast-comparison-between-two-python-dictionary/1165552#1165552
"""

def equal(new,old):
    return new is old

class DictDiffer(object):
    """
Calculate the difference between two dictionaries as:
(1) items added
(2) items removed
(3) keys same in both but changed values
(4) keys same in both and unchanged values
"""
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.current_keys, self.past_keys = [
            set(d.keys()) for d in (current_dict, past_dict)
        ]
        self.intersect = self.current_keys.intersection(self.past_keys)

    def added(self):
        return self.current_keys - self.intersect

    def removed(self):
        return self.past_keys - self.intersect

    def changed(self):
        changes = []
        for o in self.intersect:
            try:
                if equal(self.past_dict[o],self.current_dict[o]):
                    changes.append(o)
            except Exception as e:
                raise e

        return set(changes)

    def unchanged(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] == self.current_dict[o])
