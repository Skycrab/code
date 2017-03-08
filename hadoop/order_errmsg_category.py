#!/usr/bin/env python
# encoding: utf-8

import re
import sys

Category="""\
编号  一级分类
1   验车
2   高风险
3   核保出错
4   重复投保
5   填写信息错误
6   系统问题
7   其他
"""

KeyWords = """\
一级分类    关键词
填写信息错误  联系人
填写信息错误  VIN录入不规范
填写信息错误  VIN
高风险 初登
高风险 初次
高风险 商业险拒保
高风险 二手车 {无} 验车
高风险 异地车 {无} 验车
系统问题    报价信息不存在
验车  验车
验车  请上传影像
验车  二手车 {and} 验车
验车  非续保的外地牌照车辆
验车  异地车 {and} 验车
验车  外地车
验车  外省车
其他 ^\s*$
"""

class Rule(object):
    """正则规则解析
    支持: and/not
    """
    KEYS = {
        "{and}": "and",
        "{无}": "and not"
    }
    KEY_COMPILE = re.compile(r"{(.+?)}")
    def __init__(self, word):
        self.word = word
        self.code = None
        self.init()

    def init(self):
        """解析{and} {无}"""
        rules = []
        keys = []

        matchs = self.KEY_COMPILE.finditer(self.word)

        start=0
        for match in matchs:
            key, begin, end = match.group(), match.start(), match.end()
            if key not in self.KEYS: #不支持的{}规则，跳过
                break
            rules.append(self.word[start:begin].strip())
            keys.append(key)
            start= end + 1

        rules.append(self.word[start:])

        result = []
        for index, rule in enumerate(rules):
            result.append("re.search('{rule}', ''' {{message}} ''')".format(rule=rule))
            if index < len(keys): #补充and和not关键字
                expression  = self.KEYS[keys[index]]
                result.append(" {expression} ".format(expression=expression))
        self.code = "".join(result)

    def __str__(self):
        return self.code

    def execute(self, message):
        """返回True/False"""
        code = self.code.format(message=message)
        #print(code)
        return not not eval(code)


class CategoryRule(object):
    """分类规则"""
    def __init__(self, category_id, category_name):
        self.category_id= category_id
        self.category_name= category_name
        self.rules = []

    def __str__(self):
        return "{category_id}-{category_name}-{rules}".format(**self.__dict__)

    def add_rule(self, key):
        """增加规则关键字"""
        self.rules.append(Rule(key))

    def execute_once(self, message):
        """返回首次命中rule,否则None"""
        for rule in self.rules:
            if rule.execute(message):
                return rule
        return None

    def execute_all(self, message):
        """返回全部命中rule"""
        rules = []
        for rule in self.rules:
            if rule.execute(message):
                rules.append(rule)
        return rules

class Engine(object):
    def __init__(self):
        self.category_rules = {}
        self.category_names = {}

    def __str__(self):
        return str(self.category_rules)

    def init(self):
        self.rule_init()

    def rule_init(self):
        """规则文本解析初始化"""
        #解析分类
        for category in Category.splitlines()[1:]:
            category_id, category_name = category.split(' ', 1)
            self.category_rules[int(category_id)] = CategoryRule(int(category_id), category_name.strip())
            self.category_names[category_name.strip()] = int(category_id)

        #解析分类下关键字
        for key_words in KeyWords.splitlines()[1:]:
            category_name, key_word = key_words.split(' ', 1)
            category_id = self.category_names[category_name.strip()]
            self.category_rules[int(category_id)].add_rule(key_word.strip())

    def categorys_sort(self):
        """返回规则集优先顺序, 默认id越小越优先"""
        return sorted(self.category_rules.iteritems(),key=lambda x: x[0])

    def execute_once(self, message):
        """返回首次命中message所属分类,命中规则
           未命中: None
        """
        for category_id, category_rule in self.categorys_sort():
            rule = category_rule.execute_once(message)
            if rule is not None:
                return category_rule, rule
        return None, None

    def execute_all(self, message):
        """返回全部命中message所属分类,命中规则集
        """
        rules = []
        for category_id, category_rule in self.categorys_sort():
            rule = category_rule.execute_all(message)
            if rule:
                rules.append((category_rule, rule))
        return rules

def hive_transform():
    """分析hive errmessage"""
    engine = Engine()
    engine.init()
    #python *.py (once|all)
    run_type = sys.argv[1] if len(sys.argv)>1 else "once"
    for line in sys.stdin:
        id, error_message = line.split('\t', 1)
        #id, error_message = '1111', '验证码出错初登录黑名单'
        error_message = error_message.strip()
        if run_type == "once":
            category, rule = engine.execute_once(error_message)
            if category is not None:
                category_id, category_name,rule = category.category_id, category.category_name, rule.word
            else:
                category_id, category_name,rule = 0, "", ""
        else:
            rules_bingo = engine.execute_all(error_message)
            category_ids = []
            category_names = []
            rules_key = []
            for category, rules in rules_bingo:
                category_ids.append(str(category.category_id))
                category_names.append(category.category_name)
                tmp = []
                for rule in rules:
                    tmp.append(rule.word)
                rules_key.append('#'.join(tmp))
            category_id, category_name,rule = '-'.join(category_ids), '-'.join(category_names), '-'.join(rules_key)

        print('\t'.join(map(str, [id, error_message, category_id, category_name, rule])))


def engine_test():
    engine = Engine()
    engine.init()
    c, r = engine.execute_once("验证码出错初登录")
    print(c.category_id)
    print(c.category_name)
    print(r.word)

    rs = engine.execute_all("验证码出错初登录")
    print(rs)

def rule_test():
    #test regular
    rule = Rule("二手车")
    print(rule)
    print(rule.execute("哈哈二手"))

    #test and
    rule = Rule("二手车 {and} 验车")
    print(rule)
    print(rule.execute("二手车你好"))
    print(rule.execute("二手车你好验车城市"))

    #test 无
    rule = Rule("二手车 {无} 验车")
    print(rule)
    print(rule.execute("二手车你好"))
    print(rule.execute("二手车你好验车哈哈"))



if __name__ == '__main__':
    #rule_test()
    #engine_test()
    hive_transform()






