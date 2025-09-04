class SwiftSupport:
    @staticmethod
    def isSeparatedStatement(*args, **kwargs): return True
    @staticmethod
    def isStartOfLine(*args, **kwargs):       return True
    @staticmethod
    def isNotLineTerminator(*args, **kwargs): return True
    @staticmethod
    def isLineTerminatorAhead(*args, **kwargs): return False
    @staticmethod
    def isPostfixOp(*args, **kwargs):         return False
    @staticmethod
    def isPrefixOp(*args, **kwargs):          return False
    @staticmethod
    def isBinaryOp(*args, **kwargs):          return True
    @staticmethod
    def isOperator(*args, **kwargs):          return True
    @staticmethod
    def isOpChar(*args, **kwargs):            return True
    @staticmethod
    def isOpHead(*args, **kwargs):            return True
    @staticmethod
    def isImplicitParameterName(*args, **kwargs): return False
    @staticmethod
    def isIdentifier(*args, **kwargs):        return True
