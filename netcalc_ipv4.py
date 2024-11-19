class Prefix:
    def __init__(self, prefix:str):
        '''
        Create an object to represent IPv4 prefix
        :param prefix: IPv4 prefix 'X.X.X.X/X' (str)
        '''
        tmp = prefix.split('/')
        self.mask = int(tmp[1])
        tmp = tmp[0].split('.')
        self.octs = [int(tmp[0]), int(tmp[1]), int(tmp[2]),int(tmp[3])]
        self.check_prefix()


    def __str__(self):
        '''
        Print the prefix inf str format
        :return: 'X.X.X.X/X'
        '''
        return self.get_prefix()


    def __repr__(self):
        '''
        Print the prefix inf str format
        :return: 'X.X.X.X/X'
        '''
        return self.get_prefix()


    def __eq__(self, other):
        '''
        Check if this and the other prefix are equals.
        :param other: Prefix object to compare
        :return: True or False
        '''
        if not isinstance(other, Prefix):
            return NotImplemented
        return self.__key() == other.__key()


    def __lt__(self, other):
        '''
        Check if this Prefix is less than the other prefix.
        :param other: Prefix object to compare
        :return: True or False
        '''
        if self.octs[0] < other.octs[0]:
            return True
        elif self.octs[0] == other.octs[0] and  self.octs[1] < other.octs[1]:
            return True
        elif self.octs[0] == other.octs[0] and self.octs[1] == other.octs[1] and self.octs[2] < other.octs[2]:
            return True
        elif (self.octs[0] == other.octs[0] and self.octs[1] == other.octs[1] and
            self.octs[2] == other.octs[2] and self.octs[3] < other.octs[3]):
            return True
        elif (self.octs[0] == other.octs[0] and self.octs[1] == other.octs[1] and
            self.octs[2] == other.octs[2] and self.octs[3] == other.octs[3] and self.mask < other.mask):
            return True
        else:
            return False


    def __key(self):
        '''
        Information to compare two Prefix
        :return: X,X,X,X,X - octets values and subnet mask
        '''
        return (self.octs[0], self.octs[1], self.octs[2], self.octs[3], self.mask)


    def __hash__(self):
        '''
        Object hash to create a set with this object
        :return: hash of the key
        '''
        return hash(self.__key())


    def check_prefix(self):
        '''
        Check and adjust the Prefix to the network address
        :return: None
        '''
        p_oct = self.mask // 8
        base = 2**(8 - self.mask % 8)
        if base!=0:
            self.octs[p_oct] = (self.octs[p_oct] // base) * base


    def get_prefix(self):
        '''
        Get prefix information as string
        :return: IPv4 prefix as string
        '''
        return '{}.{}.{}.{}/{}'.format(self.octs[0], self.octs[1], self.octs[2], self.octs[3], self.mask)


    def get_octets(self):
        '''
        Octets values
        :return: octets values as a list
        '''
        return self.octs


    def get_mask(self):
        '''
        Get subnet mask length
        :return: Subnet mask length
        '''
        return self.mask


    def may_be_subnet(self, prefix):
        '''
        Previous check if one prefix may be a subnet
        :param prefix: Prefix object
        :return: 0 (None of them are a subnet),
                 1 or 2 (one of them may be a subnet),
                 3 (all octets are equals).
        '''
        s_mask = min(self.mask, prefix.mask)
        oct_p = s_mask // 8
        equals = 0
        for i in range(4):
            if self.octs[i] == prefix.octs[i]:
                equals += 1
            else:
                break
        if equals == 4:
            return 3
        elif (s_mask % 8 == 0) and (equals >= oct_p):
            return 2
        elif equals >= oct_p:
            return 1
        else:
            return 0


    def check(self, prefix):
        """
        Check prefix about this Prefix Object
        :param prefix: Prefix to compare
        :return: 0 = different networks,
                -1 = this object is a less specific network,
                 1 = this object is a more specific network,
                 2 = is the same network
        """
        mb = self.may_be_subnet(prefix)
        if mb==0:
            return 0
        elif mb==3 and self.mask == prefix.mask:
            return 2
        else:
            s_mask = min(self.mask, prefix.mask)
            oct_p = s_mask // 8
            if s_mask%8 > 0:
                oct_p -= 1
            if self.mask < prefix.mask:
                if self.octs[oct_p] > prefix.octs[oct_p]:
                    return 0
                result = -1
            else:
                if prefix.octs[oct_p] > self.octs[oct_p]:
                    return 0
                result = 1
            base = 2 ** (s_mask % 8)
            s_oct = min(prefix.octs[oct_p], self.octs[oct_p])
            l_oct = max(prefix.octs[oct_p], self.octs[oct_p])
            if l_oct > (s_oct+base):
                return result
            else:
                return 0



def is_subnet(prefix1:str, prefix2:str):
    """
    Check if prefix2 is a prefix1 subnet
    :param prefix1: Less specific network
    :param prefix2: More specific network
    :return: True or False
    """
    p1 = Prefix(prefix1)
    p2 = Prefix(prefix2)
    result = p1.check(p2)
    if result == (-1):
        return True
    else:
        return False



