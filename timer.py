"""
A Timer module to help diagnose performance problems in the web interface.
"""

import time

class Timer(object):
    """
    A basic class to track how long certain methods take to execute.
    """
    
    def __init__(self):
        """
        Initialize this Timer.
        """
        self.segments = []
    
    def segment(self, name):
        """
        A decorator to benchmark the given closure.
        """
        
        def outer(function):
            """
            Called at "compile time" when the module is imported.
            """
            
            def inner(*vargs, **dargs):
                """
                Wrapper of the function being profiled.
                """
                
                return self.invoke(name, function, *vargs, **dargs)
            return inner
        return outer
    
    def invoke(self, name, function, *vargs, **dargs):
        """
        Invoke the given function, placing the results in the segments list.
        """
        
        start = time.time()
        try:
            return function(*vargs, **dargs)
        finally:
            finish = time.time()
            self.segments[name] = finish - start
    
    def format(self):
        """
        Formats the given list as text.
        """
        
        result = []
        
        for name, time in self.segments:
            result.append("{:<20s} {>5.3f}s".format(name, time))
        
        return "\n".join(result)