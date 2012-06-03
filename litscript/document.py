import re
from time import time


class Document(object):
    RE_HEAD = '(^<<[^>]*>>=[\s]*$)'
    RE_TAIL = '(^@[\s]*?$)'
    splitter = re.compile(RE_HEAD+'|'+RE_TAIL,re.M)
    head = re.compile(RE_HEAD,re.M)
    tail = re.compile(RE_TAIL,re.M)

    def __init__(self,raw,processors):
        self.raw = raw
        self.nchunks = 0
        self.chunks = self.parse()
        self.available_processors = processors
        self.desired_processors = [ x.options['processor'] for x in self.chunks]
        self.processors = self._load_processors()

    def __str__(self):
        if len(self.chunks)>0:
            return str(self.chunks[0])
        else :
            return 'No Data!'

    def __getitem__(self,key):
        return self.chunks[key]

    def parse(self):
            #Split file to list at chunk separators
            chunklist = Document.splitter.split(self.raw)
            #Remove empty parts
            chunklist = filter(lambda x : x != None, chunklist)
            chunklist = filter(lambda x : not x.isspace() and x != "",
                    chunklist)
            #Parse
            doc = []
            head = None
            for chunk in chunklist:
                if Document.head.match(chunk) != None :
                    head = chunk
                elif Document.tail.match(chunk) != None :
                    head = None
                else :
                    doc.append(Chunk(chunk,head,self.nchunks))
                    self.nchunks +=1
            return doc


    def _load_processors(self):
        loaded = {}
        for proc in set(self.desired_processors):
            if self.available_processors.has_key(proc):
                loaded[proc] = self.available_processors[proc]()
        return loaded
    def _unload_processors(self):
        for proc in self.processors.values():
            proc.unload()

    def _execute(self):
        result_raw = []
        for chunk in self.chunks:
            t1 = time()
            chunk.execute(self.processors)
            t2 =time()
            #print('Executed in {} s'.format(round(t2-t1)))
        for proc in self.processors.values():
            t1 = time()
            result_raw.append(proc.executer.get_result())
            t2 =time()
            #print('Result in {} s'.format(round(t2-t1)))
        return result_raw

    def main(self):
        self.result_raw = self._execute()
        self._unload_processors()
        self.processed = True

class Chunk(object):
    RE_SPLIT='^\s*([a-zA-Z0-9#]*)\s*(?!=)(.*)'
    RE_KEYS ='([a-zA-Z_]*)\s*=\s*([a-zA-Z_0-9]*)'
    split = re.compile(RE_SPLIT)
    keys  = re.compile(RE_KEYS)

    def __init__(self,content,head,count):
        if type(head) == str:
            self.head = head[2:-3]
            self.name = 'Code'
        else:
            self.head = ''
            self.name = 'Text'
        self.content = content
        self.id = count
        self.options = self._get_options()

    def __str__(self):
        if len(self.content) > 70:
            return self.content[:70]+' ...'
        else:
            return self.content

    def __repr__(self):
        return 'ChunkID: {0}'.format(self.id)

    def _get_options(self):
        """Parse option string into dictionary.

        The string must be of the following form:

        processor-name, key1=val1, key2=val2, ...

        """
        head = self.head

        options = {}
        #Get processor and the residual keys
        #permitted are: '#', '_' and all characters from a-z, A-Z
        options['processor'], residual = Chunk.split.match(head).groups()
        #Get keys, values
        #permitted keys: '_' and characters from a-z, A-Z
        #permitted values: '_' and characters from a-z, A-Z, 0-9
        keytupel = Chunk.keys.findall(residual)
        #Transform keytuples to options
        for key, value in keytupel:
            if len(key) > 0 and len(value) > 0 :
                options[key] = value

        return options
    def execute(self,processors):
        if processors.has_key(self.options['processor']):
            self.executed = \
                    processors[self.options['processor']].execute(self)
        else :
            self.executed = False
