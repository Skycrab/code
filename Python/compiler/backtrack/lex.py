# coding= utf8


class Token(object):
    __slot__ = ("type", "text")

    def __init__(self, type, text=None):
        self.type = type
        self.text = text

    def __str__(self):
        return "<{},{}>".format(Lexer.token_name(self.type), self.text)


class Lexer(object):
    EOF = 1
    LBRACKET = 2
    RBRACKET = 3
    NAME = 4
    COMMA = 5
    EQUAL = 6

    Tokens = ["none", "EOF", "[", "]", "NAME", ",", "="]

    def __init__(self, text):
        self.text = text
        self.p = 0
        self.c = self.text[0] if len(self.text) > 1 else None

    @classmethod
    def token_name(cls, type):
        return cls.Tokens[type]

    def consume(self):
        self.p += 1
        self.c = self.text[self.p] if len(self.text) > self.p else None

    def match(self, c):
        if self.c == c:
            self.consume()
        else:
            raise TypeError("match err")

    def parse(self):
        while 1:
            token = self.next_token()
            print(token)
            if token.type == self.EOF:
                break

    def next_token(self):
        while self.c is not None:
            if self.c.isspace():
                self.consume()
            elif self.c == '[':
                self.consume()
                return Token(self.LBRACKET)
            elif self.c == ']':
                self.consume()
                return Token(self.RBRACKET)
            elif self.c == ',':
                self.consume()
                return Token(self.COMMA)
            elif self.c == '=':
                self.consume()
                return Token(self.EQUAL)
            elif self.c.isalpha():
                return self.names()

        return Token(self.EOF, "eof")

    def names(self):
        names = []
        while self.c.isalpha():
            names.append(self.c)
            self.consume()
        return Token(self.NAME, "".join(names))


def test():
    lex = Lexer("[a,b]=[c,d]")
    lex.parse()


if __name__ == "__main__":
    test()
