Django编码风格([referer](https://docs.djangoproject.com/en/1.8/internals/contributing/writing-code/coding-style/))

#编码风格
写Django项目时请遵守下面的代码标准

##Python编码风格
* 除非另有规定，不然请遵守[PEP8](https://www.python.org/dev/peps/pep-0008)

    使用工具[flake8](https://pypi.python.org/pypi/flake8)检查出现的问题。我们看到Django项目下的
    [setup.cfg](https://github.com/django/django/blob/master/setup.cfg)文件包含了一些排除文件(
    清理后会弃用的模块以及Django使用的一些第三方代码)以及排除了一些我们认为不是严重违反PEP8的错误。
    记住，PEP8只是一个指南，代码的一个主要目标是遵守该指南。

    我们和PEP8一个不同点在行长度上。限制一行79个字符会让代码看起来特别丑陋，而且很难阅读。我们允许119个字符，
    因为这是github代码评审是展示的宽度；再长一点需要拖动滚动条，这导致更难评审。文档，注释和文档字符串应该
    包裹在79个字符，虽然PEP8建议72个字符。

* 使用4个空格缩进

* 变量，函数，方法使用下划线而不是骆驼拼写法（例如，poll.get_unique_voters()，而不是poll.getUniqueVoters)。

*


