
class CompactFormatter(object):
    name = 'compact'
    aliases = {}

    def process(self,cchunk):
        i = 0
        for hunk in cchunk.hunks:
            if i == 0:
                yield hunk.source.formatted
            else:
                yield hunk.source.simple
            yield hunk.stdout.simple
            yield hunk.stderr.simple
            yield hunk.traceback.simple
            i += 1
