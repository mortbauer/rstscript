class FormatterRst(object):

    def figure(self,path,caption=None,width=None):
        fig =  (".. figure:: {0}\n"
                "   :width:  {1}\n\n"
                "   {2}".format(path,width,caption))
        return fig

def wrapper(string, width):
    """Wrap a string to specified width like Python terminal"""
    if len(string) < width:
        return string
    return string[0:width] + '\n' + wrapper(string[width:len(string)], width)
