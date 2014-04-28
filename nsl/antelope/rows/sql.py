import collections
import curds2
from obspy.core import UTCDateTime

curds2.TimestampFromTicks = UTCDateTime

class _SQLValues(object):
    @staticmethod
    def _sql_str(value, desc):
        """
        Convert a value to a string suitable for an sql statement
        """
        # Format everything not a string or to be stringified
        if value is None:
            return 'NULL'
        
        if desc.type_code == curds2.DATETIME and isinstance(value, float):
            value =  str(curds2.TimestampFromTicks(value))
        
        if isinstance(value, str):
            return "'{0}'".format(value.replace("'","''"))
        return str(value)

    @classmethod
    def _values(cls, row, description):
        """
        row : seq of values from a database
        
        Return
        ------
        list of strings formatted for SQL

        """
        return [cls._sql_str(r, description[n]) for n, r in enumerate(row)]
    
    @staticmethod
    def values_str(values):
        return '(' + ', '.join(values) + ')'
        
    def __str__(self):
        """
        String of the tuple used as input for VALUES

        Input : sequence of SQL value strings

        """
        return self.values_str(self)


class SQLValuesRow(_SQLValues):
    """
    A row_factory function to provide SQL values
    
    Instance is a namedtuple with: field names as attributes.
                                   SQL strings as values
    
    Methods
    -------
    __str__ : The 'str' function will return a string suitable for passing after
              'VALUES' in an SQL statement

    Class Methods
    -------------
    values_str : class version of the __str__ function, if one would like to
                 make a subset of the returned values (for an UPDATE, e.g.)
                 from a custom sequence.
    
    """
    def __new__(cls, cursor, row):
        description = cursor.description
        Tuple = collections.namedtuple(cls.__name__, [d.name.replace('.','_') for d in description])
        class_ = type(cls.__name__, (_SQLValues, Tuple,), {})
        return class_(*super(SQLValuesRow, cls)._values(row, description))

#
#---------------------------------------------------------------------#


