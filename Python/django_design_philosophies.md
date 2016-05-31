#django 设计哲学
    [来源](https://docs.djangoproject.com/en/1.8/misc/design-philosophies/)
    本文档说明了开发者在创建Django框架时使用的一些本质哲学。目的是解释过去并引导未来。

#总览

##松耦合
Django技术栈的一个基本目标是[松耦合高内聚](http://c2.com/cgi/wiki?CouplingAndCohesion)。框架的不同层除非绝对必要不应该知道其它层。

例如，模板系统对Web请求一无所知，数据库层不知道数据如何显示，视图不关心开发者使用的是哪个模板系统。

虽然Django为了方便设计成全栈的，但不同层会尽可能不依赖其它层。

##更少的代码
Django应用尽可能使用更少的代码，不需要样例模板文件。应该充分利用Python的动态性，如反射。

##快速开发
21世纪Web框架的要点是让Web开发中乏味的地方开发迅速。Django能让你拥有不可置信的开发速度。

##

