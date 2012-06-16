import re
from time import time


class Document(object):
    _RE_HEAD = '(^<<[^>]*>>=[\s]*$)'
    _RE_TAIL = '(^@[\s]*?$)'
    _splitter = re.compile(_RE_HEAD+'|'+_RE_TAIL,re.M)
    _head = re.compile(_RE_HEAD,re.M)
    _tail = re.compile(_RE_TAIL,re.M)

    def __init__(self,raw,processors_loaded):
        self.raw = raw
        self.nchunks = 0
        self.chunks = self.parse()
        self.processors_available = processors_loaded
        self.processors_desired = [ x.options['processor'] for x in self.chunks]
        self.processors_loaded = self._load_processors()

    def __str__(self):
        if len(self.chunks)>0:
            return str(self.chunks[0])
        else :
            return 'No Data!'

    def __getitem__(self,key):
        return self.chunks[key]

    def parse(self):
            #Split file to list at chunk separators
            chunklist = Document._splitter.split(self.raw)
            #Remove empty parts
            chunklist = filter(lambda x : x != None, chunklist)
            chunklist = filter(lambda x : not x.isspace() and x != "",
                    chunklist)
            #Parse
            doc = []
            head = None
            for chunk in chunklist:
                if Document._head.match(chunk) != None :
                    head = chunk
                elif Document._tail.match(chunk) != None :
                    head = None
                else :
                    doc.append(Chunk(chunk,head,self.nchunks))
                    self.nchunks +=1
            return doc


    def _load_processors(self):
        loaded = {}
        for proc in set(self.processors_desired):
            if self.processors_available.has_key(proc):
                loaded[proc] = self.processors_available[proc]()
        return loaded
    def _unload_processors(self):
        for proc in self.processors_loaded.values():
            proc.unload()

    def _execute(self):
        result_raw = []
        for chunk in self.chunks:
            t1 = time()
            chunk.execute(self.processors_loaded)
            t2 =time()
            #print('Executed in {} s'.format(round(t2-t1)))
        for proc in self.processors_loaded.values():
            t1 = time()
            result_raw.append(proc.executer.get_result())
            t2 =time()
            #print('Result in {} s'.format(round(t2-t1)))
        return result_raw

    def main(self):
        self.result_raw = self._execute()
        self._unload_processors()
        self.processed = True

def ChunkCrawler(raw):
    _RE_Code_Start = '(^<<[^>]*>>=[\s]*$)'
    _RE_Code_End = '(^@[\s]*?$)'
    _splitter = re.compile(_RE_Code_Start+'|'+_RE_Code_End,re.M)
    _head = re.compile(_RE_Code_Start,re.M)
    _tail = re.compile(_RE_Code_End,re.M)



class Chunk(object):
    def __init__(self,n,head,content):
        self.n       = n
        self.head    = head
        self.content = content
    

class ChunkOLD(object):
    _RE_SPLIT='^\s*([a-zA-Z0-9#]*)\s*(?!=)(.*)'
    _RE_KEYS ='([a-zA-Z_]*)\s*=\s*([a-zA-Z_0-9]*)'
    _split = re.compile(_RE_SPLIT)
    _keys  = re.compile(_RE_KEYS)

    def __init__(self,content,head,count):
        if type(head) == str:
            self.head = head[2:-3]
            self.type = 'Code'
        else:
            self.head = ''
            self.type = 'Text'
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
        options['processor'], residual = Chunk._split.match(head).groups()
        #Get keys, values
        #permitted keys: '_' and characters from a-z, A-Z
        #permitted values: '_' and characters from a-z, A-Z, 0-9
        keytupel = Chunk._keys.findall(residual)
        #Transform keytuples to options
        for key, value in keytupel:
            if len(key) > 0 and len(value) > 0 :
                options[key] = value

        return options
    def execute(self,processors_loaded):
        if processors_loaded.has_key(self.options['processor']):
            self.executed = \
                    processors_loaded[self.options['processor']].execute(self)
        else :
            self.executed = False
