
#######################################################Python基础知识################################################################################################################

#python语法：缩进并非大括号
#python重点错误：谨记函数调用与函数对象调用（会影响到成员变量变化，所以说多次调用结果不同）的区别，而函数调用每次调用完内存会释放掉，多次调用结果相同
#python关了 才释放对象对象对象
#python(key point): 万物皆对象,python解释器中的任何数值、字符串、数据结构、函数、类、模块都是python对象（可调用属性与方法）
#python函数可接受位置参数与关键字参数
#python a=[1,2,3,4] 创建了右边对象[1,2,3,4]的一个引用a，a=b不会产生复制行为，即创建对象[1,2,3,4]的另一个引用b, python按引用传递
#python强类型语言
#python常用函数：isinstance(a,(int,float)) 判断对象类型是否所属元组内的类型  
			# 	 getattr(a,'split') 用于访问对象的属性与方法 
			#	 a is b 判断两个引用是否指向一个对象  a is not b 相反  
			# 	 type(a) 判断某个对象的类型
			#    range()返回迭代器（可迭代对象） 返回一组间隔平均的整数  range(end)默认开始值为0,步长为1；range(start,end,step) start开始值(包含在内),end结束值(不包含在内),step为步长
			#	 len(序列&可迭代对象) 取得序列与可迭代对象的长度
			#	 b in a（序列&可迭代对象）判断b是否在a里面, 元组与序列需要进行线性扫描，而dict与set基于哈希表可瞬间判断，速度快多了
			#	 a.count(b) 其中a为序列或可迭代对象（note：集合set与字典dict不支持） 统计a中b的个数
			#	 同类型的序列或可迭代对象合并（note：集合set与字典dict不支持，可迭代对象貌似也不支持） a+b
			#    有序tuple与list 支持内置bisect模块实现二分查找以及对有序列表插入操作。bisect.bisect(a,b)返回元素b在a中的索引位置 bisect.insort(a,b) 在a中插入b
			#	 切片(序列&可迭代对象均可以进行切片) (一会再summarize)

			# 	 字符串函数split() split('特殊字符')按照特殊字符将字符串分开，放入一个列表中
			#  	 map(某函数,序列或可迭代对象) 将函数用在序列的各个元素，返回的也是一个可迭代对象 map(func,*iterables) filter(func,iterable)将func应用于iterable,返回结果为True的元素构成的迭代器
			#    apply()函数形式,使用方式 data.apply(某函数)  data必须是Series类型，调用时data作为参数传入函数中
			#    内置序列函数：enumerate(序列or可迭代对象) 返回一个可迭代对象,其元素为(i,vale)元组 for i,value in enumerate(collection):
							 # dict((v,i) for i,v in enumerate(some_list)) //生成一个字典
							 # sorted(序列或可迭代对象) 将其排序
							 # zip(seq1,seq2,...seqn)其中seq1,seq2,...seqn为序列或可迭代对象(字典慎用),返回一个可迭代对象，其中元素为元组
							 # for i,(a,b) in enumerate(zip(seq1,seq2))：print('%d:%s,%s' %(i,a,b))
							 # 对已压缩zipped序列，可以解压unzip  zip(*元素为元组的序列或可迭代对象) 结果是一个元素为元组的可迭代对象
							 # zip(*seq) 相当于 zip(seq[0],seq[1],...,seq[len(seq)-1])
				  			 # reversed(序列或可迭代对象) 按逆序迭代序列中的元素 返回一个可迭代对象
							 
				 

#import xxx.py 引入模块（包含函数&变量&类）
#python(对象可变&不可变) list对象所包含的对象&值是可被修改的，字符串&元组是不可变的
#python特定表达式：三元表达式：value=true-expr if condition else false-expr(其实是if结构简化格式) 
				 # 列表(集合、字典)推导式：[expr for val in collection if condition] 对collection元素进行过滤后转换 新的语法糖使代码更易读
				 #{key-expr:value-expr for key,value in collection if condition} 字典推导式,其中collection为元素为二元组的序列或可迭代对象，通常可以通过ennumerate(list)或zip(key_list,value_list)得到
				 #{expr for value in collection if condition} 集合推导式  gen=(x**2 for x in range(100)) 迭代器
				 #嵌套列表推导式  如 [name for names in strings for name in names if name.count('e')>=2]  for部分按嵌套顺序排列
				 

				 
#python基本运算符：+ - * / // **  （结果为值）  == != <= < > >=  (结果为bool类型)    & | ^ （结果为bool类型，运算符左右为bool类型对象）
#python标量类型：字符串str unicode(不同的字符串编码 python 2.x) str(相当于python 2.x中的unicode) bytes(相当于python2.x中str)(python 3.x)
				# None(NoneType 仅有实例对象None)  float Int long  bool（所有内置python类型都能在if语句中被解释为bool类型）
#python日期&时间：from datetime import datetime,date,time(稍后总结)
#python对象类型转化：str(a) 将对象强转化str类型  list(a) 将字符串对象转化成list对象
				# o   bool(a) 将对象转化成bool类型  float(a) 将对象转化成float int(a)将对象转化int类型
#python数据结构&序列(可迭代)(均从0开始索引)：字符串  元组(一维定长不可变序列)：tuple=() 列表：list=[]  字典：dic={key:value }  集合：set={}(集合里没有重复值) 


#python控制流:if elif else    for value in collection(序列&迭代器): 关键字continue使for循环提前进入下一循环，break表示退出for循环
							#若collection中的元素为元组或列表，可写作 for a,b,c in iterator:
							#while循环 while condition: 代码块 (condition为False是循环结束)（Pass为空操作）
							#异常处理：
										def attempt_float(x):
											try：return float(x)
											except(TypeError,ValueError):return x  #(TypeError,ValueError)由异常组成的元组
											finally:print('finished')
#python函数（重要代码组织与复用手段）：def fun_name(positional_paras,keyword_paras):  return xxx  关键字def声明函数,return表示函数返回值,函数可以返回多个值，若无便返回None
									   #positinal_paras为位置参数，keyword_paras为关键字参数,关键字参数位于位置参数的后面，顺序随意
									   #函数调用---创建局部命名空间---函数参数立即进入此空间---函数中的赋值变量也在此命名空间---函数执行完毕---局部命名空间销毁
									   #函数调用与对象方法调用：函数调用需要圆括号以及>=0个参数,可将返回值赋值给一个变量,如result=f(x,y,z);对象方法调用：obj.some_method(x,y,z)
									   #如果用getattr函数访问对象的属性与方法：b=getattr(a,'count'),由于count函数还需要参数，所以b在此仅仅为一个函数变量，调用时需要传入参数
									   #可在函数中对全局变量进行赋值操作，但这些变量必须用global关键字声明成全局
									   #嵌套的内层函数只有当外层函数被调用时才会被动态创建，外层函数结束执行，内层函数立即被销毁。所有函数都是某个作用域的局部函数，这个作用域可能刚好就是模块级的作用域
									   #返回多个值 def f():a=5 b=6 c=7 return a,b,c  这个函数结果是一个元组 a,b,c=f()元组拆包
									   #函数也为对象  若对同一批数据进行多个函数处理,可以将所用函数放在一个列表里面,进行for循环
									   #将字符标准化
									   states=['   Alibaba','georgia!','georigia','carolina###','west virginalia?'] 
									   import re   #导入正则表达式模块
									   def remove_punctuation(value):   #定义一个函数用于去除异常符号
											return re.sub('[!#?]','',value)
									   clean_ops=[str.strip,remove_punctuation,str.title] #将函数当成对象,放入一列表中
									   def clean_strings(strings,ops):    #函数声明
											result=[]
											for value in strings：
												for function in ops：
													value=function(value)
											result.append(value)
											return result
										clean_strings(states,clean_ops)  #函数调用	
									   
									   #lambda函数 匿名函数(没函数名,简单函数,仅由单条语句组成,该语句结果就是返回值,关键字lambda无实意义,仅表示在声明一个匿名函数)
									   #在数据分析工作中，很多数据转换函数都是以函数为参数的，直接传入lambda函数很方便
									   #def apply_to_list(some_list,f): return [f(x) for x in some_list]  apply_to_list(list,lambda x:x*2)
									   #闭包(返回函数的函数)(闭包可以看做是一个函数类):由其他函数动态生成并返回的函数。创建者执行完毕，闭包仍能继续访问其创建者的局部命名空间。闭包也可通过类实现
									   #定义一个闭包format_and_pad
									    def format_and_pad(template,space):
											def formatter(x)：
												return (template %x).rjust(space)
											return formatter
									    fmt=format_and_pad('%.4f',15)  #赋值一个函数对象fmt
										fmt(1.756) #调用函数fmt
									 
									   #技术限制：虽然可修改任何内部状态对象(如向字典添加键值对)，但不能绑定外层函数作用域中的变量，解决方法：通过修改字典或列表，而不是绑定变量
									   #闭包实际用处：在实际工作中，编写了带有大量选项的非常一般化函数，然后再组装出更为简单更专门化的函数
									   #扩展调用语法和*args、**kwargs:编写函数的时，位置参数与关键字参数会分别打包成元组args与字典kwargs,然后再内部悄悄进行转化
										def say_hello_then_call_f(f,*args,**kwargs):   #声明函数
											print('args is',args)
											print('kwargs is',kwargs)
											return f(*args,**kwargs)

										def g(x,y,z=1):			#声明函数
											return (x+y)/z

										say_hello_then_call_f(g,1,2,z=5.) #调用函数时,会自动将1,2组成元组赋值给*args,将z=5封装成字典赋值给**kwargs
																			   
	                                    #柯里化：部分参数应用(从现有函数派生出新函数的技术)
										# def add_numbers(x,y): return x+y
										# add_five=lambda y:add_numbers(5,y) 参数y为柯里化的
										# from functools import partial
										# add_five=partial(add_numbers,5)
										# 在讨论pandas和时间序列数据时，我们将创建专门的数据序列转换函数：ma60=lambda x:pandas.rolling_mean(x,60)
										
										
	
#python 变量：根据作用域可分为全局(global)和局部(local),变量作用域叫命名空间（namespace),函数中赋值变量被分配的局部命名空间（local namespace),局部命名空间是
#函数被调用时创建的,函数参数立即进入此空间。

#python的迭代器(iterator)&生成器(generator)：能一种一致方式对序列进行迭代,如for key in some_dict时，python解释器会从some_dict创建一个迭代器dict_iterator=iter(some_dict)
#大部分能接受列表之类的对象的方法也可以接受任何可迭代对象,min max sum等内置方法 list tuple等类型构造器
#生成器generator是构造新的可迭代对象一种简单方法,生成器以延迟方法返回一个值序列。创建生成器，需将函数中的return替换成yield
def squares(n=10):
	print('Generating squares from 1 to %d' %(n**2))
	for i in range(1,n+1):
		yield i**2

gen=squares()

#处理利用函数构成生成器,也可利用生成器表达式进行构造，将列表生成器进行变化即可, gen=(x**2 for x in range(100))
#生成器表达式可用于任何接收列表生成器的python函数：sum(x**2 for x in range(100)) dict((i,i**2) for i in range(5))
#标准库itertools模块中的函数groupby(序列,函数) 根据函数返回值对序列中的连续元组进行分组
import itertools
first_letter=lambda x:x[0]
names=['Alia','adam','will','Albert','Steven']
for letter,names in itertools.groupby(names,first_letter): #groupby函数 根据first_letter函数应用于序列names的去重结果对names进行分组，得到一个元素为二元组(函数去重结果，分好类的生成器)的生代器
		print(letter,list(names))

#itertools函数： itertools.combinations(iterable,k) 返回无序元素为k元元组的迭代器 itertools.permutations(iterable,k)返回有序元素为k元元组的迭代器 itertools.groupby(iterable[,keyfunc])为每个唯一键生成一个(key,sub-iterator)

#python文件&操作系统：f=open(path) path为绝对路径或相对路径,文件默认以只读模式r打开,f为文件句柄，可以看出是由文件中各行组成的列表,for line in f: pass
#从文件中取出的行都带有完整的行结束符（EOL) lines=[x.rstrip() for x in open(path)]
#文件读取模式：r(只读) w(只写,创建新文件删除同名文件) a(附加到现有文件,若无创建一个,用于追加内容) r+(读写模式) b(附加说明某模式用于二进制文件,即rb wb) U(通用换行模式，单独使用’U',或附加到其他模式，rU)
# 文件句柄的方法：read([size]) 以字符串形式返回文件数据,可选参数size表示读取的字节数  readlines([size]) 将文件返回为行列表
				# write(str) 将字符串写入文件,返回字符串长度        writelines(str) 将str写成行，实例中不支持
				# close() 关闭句柄 flush() 清空内部I/O缓存区,将数据强行写回磁盘  seek(pos)移动到指定文件位置  tell()以整数形式返回当前文件位置 closed 如果文件已关闭为True
				

#open是否需要每次都执行以下



################################################################Python重要对象总结#########################################################################################
###python对象总结#####
#字符串对象：a.replace('','')   s=r'dd\dfds\dfdsf' 所有字符按原来样子解释    
		   # 字符串格式化：'a is %.2f,b is %s,c is %d' %(a,b,c) 其实%.2f表示带2位小数的数字，%s表示字符串，%d表示整数
		   
#tuple对象(一维定长不可变序列)：tup=4,5,6 tup=(4,5,6) 这两张定义方法都可以  tuple(序列&可迭代对象)函数将之变成元组,对字典用该函数得到的是key的元组
#有种情况元组中的元素是可以改变的：元素为list,可进行append等系列操作
#(1,2,3)*4 相当于4个(1,2,3)相连接
#元组拆包：tup=(5,6,7) a,b,c=tup 在for循环里面用的多

#list对象（一维变长且内容可修改):list(序列&可迭代对象)函数将之转化成list对象,对字典用该函数得到的是key的列表  a.append(b)在b添加到a列表结尾
# a.insert(num,b) 在列表a的索引处num插入b  a.pop(num)将列表a指定索引处num的元素移除  a.remove(b) 将列表a中的元素b去掉
# a.extend(列表b) 这个相对于a+b好很多，不会太浪费资源  a.sort() 将列表中的元素进行排序 a.sort(key=len)按照元素长度进行排序,将key赋值成一个函数(此函数也可为匿名函数)
#list.sort() 若list的元素为元组,则按照元组第一个元素进行排序
# strings=['foo','card','bar','aaaa','abab'] strings.sort(key=lambda x:len(set(list(x))))
# key_point:这些函数都是在list的原始数据上进行操作的，不要赋值于另一个变量，这样too silly

 

 
#dict对象(大小可变的健值对集)
#empty_dict={}  a_dict={'a':1,'b':2} a_dict['c']=6增加字典元素 a_dict[key]访问  del a_dict[key]删除  a_dict.pop(key)删除并返回该key对应value
#a_dict.keys() 返回字典键迭代器  a_dict.values()返回字典值迭代器
#a_dict.update(b_dict) 将字典b_dict合并到字典a_dict中 如果两字典有相同键,后面的value会替代之前的
#创建字典 通过序列类型创建字典  mapping={} for key,value in zip(key_list,value_list):mapping[key]=value
		 #通过dict(元素为二元元组的序列或迭代器)函数创建 mapping=dict(zip(key_list,value_list)) 也可 mapping=dict((i,i**2) for i in range(5))
		 #some_dict.get(key,default_value)  some_dict.pop(key,default_value) 字典的get与pop方法可接受一个可供返回的默认值,key不存在，返回default_value，key存在返回key对应的value
		 #例子：将words=['apple','bat','bar','atom','book']按首字母分类
		  by_letter={}
		  for word in words:
			letter=word[0]
			if letter not in by_letter:
				by_letter[letter]=[word]
			else:
				by_letter[letter].append(word)
		#字典方法setdefault  by_letter.setdefault(letter,[]).append(word)可替代上面的if-else块, dict.setdefault(key,[])设置字典dict的默认value类型为列表[],返回dict[key]  
		#collections模块中有个类defaultdict（字典初始化器）      defaultdict方法使用： defaultdict(类型或函数) 生成字典value的默认值,返回一个可迭代对象，如counts=defaultdict(lambda:4)字典counts默认值为
		 by_letter=defaultdict(list)
		 for word in words:
			by_letter[word[0]].append(word)
		#字典key是不可变对象(整数、浮点数、字符串、元组(元素不可变))，即可哈希性，可以通过hash函数进行判断
	

#set集合对象（由唯一元素组成的无序集，相当于只有键的字典）
#集合创建方法：a={1,3,2,1,1}  也可用set函数: set(序列或可迭代对象)，对字典用该函数得到的是key的集合
#集合运算：并 交 差 对称差(异或)（将集合合并并去掉公共元素） set1|set2 等价于set1.union(set2)  set1&set2等价于set1.intersection(set2) 
#set1-set2 相当于set1.difference(set2)     set1^set2 相当于a.symmetric_difference(b)  判断集合set1是否为集合set2的子集 set1.issubset(set2) 判断集合set1是否为集合set2的父集  set1.issuperset(set2)  set1.isdisjoint(set2) 判断集合set1 set2是否有公共元素
#集合运算：set1.add(x)  set1.remove(x)  

#############################################################python函数中的默认参数#################################################################################
#函数调用就是对其应用数据,函数中的参数被声明为占位符(在定义函数时),用以代表函数调用时被实际传入的对象。默认值参数在定义时就已经求值
#函数调用需要传入实参,其实是传入的地址。
#python的变量是引用,即实际变量的内存地址,这意味python函数永远以"传址"方式工作,当调用一个函数时，并不是复制一份参数值来替代占位符,而是把占位符指向了变量本身
#python是多态的，函数参数不用声明类型
#Python里带*的参数就是用来接受可变数量参数的
#函数的参数和引用，是最大的错误源之一
#Python functions accept any variable without checking the type and rely on the variable itself to provide the correct methods
#Type system is strong because everything has a well-defined type that you can check with the type() built-in function
#Type system is dynamic since the type of a variable is not explicitly declared, but changes with the content
#Python EAFP principle(easier to ask for forgiveness then permission):Instead of checking if an object has a given attribute or method before actually accessing or using it, just trust the object to provide what you need and manage the error case. 
#Python polymorphism is based on delegation(delegation principle)  
#Since in Python everything is an object, everything is the instance of a class, even classes
#dir(object)可以得到对象的所有方法与属性


##################################################################Python OOP##########################################################################################
###Classes and members###
#Everything is an object.The class of an object is an object itself,it is stored somewhere in memory
#type(object)可得到object的类型,id(object)可得到object的内存地址

##定义类
class Door:
	color='brown'					# class attributes, shared among the class instances
	def __int__(self,number,status):#__int__类似于构造函数,self表示实例对象本身
		self.number=number			#attributes here are not stored in the class but in every instance,因为这儿涉及到实例对象self
		self.status=status          
	def open(self):
		self.status='open'
	def close(self):
		self.status='closed'
		
#创建实例对象
door1=Door(1,'closed') #在类实例化时,格式:类名(参数),其中参数为类中__int__函数中除self以为的参数
door2=Door(1,'closed') #类的不用实例化对象是独立不相关的，所以他们的内存地址肯定不一致，尽管创建时参数时一样的
door1.__class__  #类实例对象调用__class__属性得到相应的类,任何python对象都有这个属性，目标是获取其类
Door.color		#可以用类直接调用类属性
door1.color		#也可用类实例化对象调用类属性,若通过类直接改变类属性值，那么类实例化对象调用类属性值也会变化
door2.color   
#Any Python object is automatically given a __dict__ attribute, which contains its list of attributes. 
Door.__dict__  #类属性 color 会出现在 Door.__dict__中,而door1.__dict__仅仅出现number,states属性,那为什么instance会调用到类属性color,是通过
door1.__dict__ #__getattribute__()方法,在python中点语法会自动唤醒这个方法,比如door1.color python就会执行door1.__getattribute__('color')类似于查找属性
#首先会在instance的internal dictionary(__dict__)去找，door1.__dict__['color'],找不到就会去 door1.__class__.__dict__['color']去找
#当我们通过class的instance改变class attribute,就相当于在instance的__dict__中放入了这个key-value对。

Door.open  #<function Door.open at 0xb68604ac>
door1.open  #<bound method Door.open of <__main__.Door object at 0xb67e162c>>
#通过类调用类属性与通过实例调用类属性获取的都是同一地址的属性值
#但是通过类调用函数与通过实例调用函数得到的是不同地址的函数
#When you refer to a function as part of a class in Python 3 you get a plain function, without any difference from a function defined outside a class.
#When you get the function from an instance, however, it becomes a bound method. The name method simply means "a function inside an object"
#the method is linked to that instance. 
#python如何将一个function转化成bound method

Door.open() #直接用类调用函数会保持,因为函数需要的参数是类的实例化对象 TypeError: open() missing 1 required positional argument: 'self'D
Door.open(door1) #这样就可以 这个是function调用
door1.open()	#这个是bound method调用  bound method automatically passes the instance as an argument to the function.
#door1.open() 相当于 door1.__class__.open(door1)
#door1.__class__.__dict__['open'] 返回 function defined in the class，该函数对象中的函数__get__可将function转化成bound method
 door1.__class__.__dict__['open'].__get__ #<method-wrapper '__get__' of function object at 0xb68604ac>
door1.__class__.__dict__['open'].__get__(door1) #method-wrapper 调用 <bound method Door.open of <__main__.Door object at 0xb67e162c>>

###class method###(与class attribute一样)
#define a function that operates on the class instead of operating on the instance
# Class methods are functions that are bound to the class and not to an instance.
#Such a definition makes the method callable on both the instance and the class
class Door:
    colour = 'brown'

    def __init__(self, number, status):
        self.number = number
        self.status = status

    @classmethod
    def knock(cls):
        print("Knock!")

    @classmethod
    def paint(cls, colour):   #该class method可改变 class attribute
        cls.colour = colour

    def open(self):
        self.status = 'open'

    def close(self):
        self.status = 'closed'
		
Door.knock()
door1.knock()
door1.__class__.__dict__['knock'] #<classmethod object at 0xb67ff6ac>
door1.knock #<bound method type.knock of <class '__main__.Door'>>
Door.knock #<bound method type.knock of <class '__main__.Door'>>

#The class method can be called on the class, but this affects both the class and the instances
#Class methods can be called on instances too, however, and their effect is the same as before. The class method is bound to the class, so it works on this latter regardless of the actual object that calls it (class or instance).



###Polymorphism### Python polymorphism is based on delegation
###reference system##
#polymorphism refers to the ability of an object to adapt the code to the type of the data it is processing.
#two major applications:
#1.an object may provide different implementations of one of its methods depending on the type of the input parameters.
#2.code written for a given type of data may be used on data with a derived type, i.e. methods understand the class hierarchy of a type.
#(once you know how to interact with the most generic type (basic door) you can also interact with specialized types (window, car door) 
# as soon as they act like the ancestor type)
#polymorphism requires that code written for a given type may also be run on derived types.


# In Python the type of a variable is not explicitly declared.everything in Python has a type
#in other words they just tell the language where in memory a variable has been stored. What is stored at that address is not a business of the variable.
#In python variables  can contain only one type of data: a memory address. (key words)
#type() built-in function is smart enough to understand that we are not asking about the type of a (which is always a reference), but about the type of the content.
#type system is strong because everything has a well-defined type that you can check with the type() built-in function
#type system is dynamic since the type of a variable is not explicitly declared, but changes with the content
#function accepts a reference and returns a reference. In other words we just defined a sort of universal function, that does the same thing regardless of the input.
#There are two main strategies you can apply to get code that performs the same operation regardless of the input types：
#1. cover all cases
#2.  you ask the data itself to perform the operation, reversing the problem.
def sum(a,b):
	c=a+b		#c=a._add_(b) 这是python实际执行的，the sum operation is delegated to the first input variable
	return c	#there is no need to specify the type of the two input variables. The object a (the object contained in the variable a) shall be able to sum with the object b.

#As we already discovered Python functions accept any variable without checking the type and rely on the variable itself to provide the correct methods. But you already know that a subtype must provide the methods of the parent type, either redefining them or through implicit delegation, so as you can see Python implements subtype polymorphism from the very beginning.

####Metaclasses###
#object.__class__ 得到object所在类, object.__class__.__bases__ 求类的父类
#class hierarchy: 首先是 object类（the top of the class hierarchy),所有类都继承了object类
#type is the class that is instanced to get classes.
#object is the base of every object, type is the class of every type.
#at the very base of Python type system there are two things, object and type.object is an instance of type, and type inherits from object
#Metaclasses:
#a class itself is an instance of a (super)class, and this class is type.
#type is the default metaclass of all classes
#Once you get a subclass of type you need to instruct your class to use it as the metaclass instead of typeand you can do this by passing it as the metaclass keyword argument in the class definition.
#type是所有的class的metaclass, subclass of type也可以替代type作为class的metaclass,但是要将subclass of type作为新的class的metaclass keyword argument
class mytype(type):  #定义类mytype,他继承了class type 
	pass
class myspecialclass(metaclass=mytype): #定义类myspecialclass,并且它的metaclass为mytype
	pass

msp=myspecialclass()  #msp为类myspecialclass的一个instance
type(msp) #<class '__main__.MySpecialClass'>  
type(myspecialclass) #<class '__main__.MyType'>
type(mytype) #<class 'type'> 任何type是任何class的metaclass

##metaclass的例子Singleton。Singleton has one purpose: to return the same instance every time it is instanced, like a sort of object-oriented global variable.
#A task of metaclass is to build a class

class Singleton(type):  #定义类Singleton,继承了type类
	instance=None
	def __call__(cls,*args,**kw):
		if not cls.instance:
			cls.instance=super(Singleton,cls).__call__(*args,**kw) #override父类type中__call__方法,该方法是在我们调用class的时候被唤醒
		return cls.instance

class ASingleton(metaclass=Singleton):	#instruct class ASingleton to use Singleton as the metaclass
	pass								

a = ASingleton()	#在执行此语句时,就会调用类中__call__()方法
b = ASingleton()
a is b				#True  所以实现了目标

#当instance一个class时,会直接找到__init__()方法，我们叫做constructor, 其实class中也定义了destructor,当object被销毁时调用,为__del__()方法
#python constructor mechanism 是通过两种方法实现： __new()__()(用于实例化时操作行为) 与 __int__()(用于对象初始化)(更重要)
class MyClass():
    def __new__(cls, *args, **kwds):			#override父类中俄的__new__,与__int__不同，第一个参数为cls
        obj = super().__new__(cls, *args, **kwds)
        [put your code here]
        return obj

###Abstract Base Classes(ABC)###(解决由pure polymorphism引起的问题)
#Inspection means the ability for external code (outside of the object's methods) to examine the type or properties of that object, and make decisions on how to treat that object based on that information.
#isinstance() and issubclass() are built-in functions, not object methods, so we cannot simply override them providing a different implementation in a given class.
#the function  isinstance() can also walk the class hierarchy,but isinstance() does not check the content of the class or its behaviour, it just considers the class and its ancestors.
class Door:
	pass
class EnhanceDoor(Door): 创建类EnhanceDoor 继承了类Door
	pass

d=Door()
ed=EnhanceDoor()
isinstance(ed,Door) #walk the class hierarchy 判断instance ed是否为类Door的实例

#what is the best way to test that an object exposes a given interface?
#write inside an attribute of the object  the list of interfaces it promises to implement, and to agree that any time we want to test the behaviour of an object we simply have to check the content of this attribute. 
#Python provides two built-ins to inspect objects and classes, which are isinstance() and issubclass() and a solution to the inspection problem should allow the programmer to go on with using those two functions.
#Solution:metaclasses are the classes used to build classes, which means that they are the preferred way to change the structure of a class, and, in consequence, of its instances.

from abc import ABCMeta				#abc module ABCMeta为其中的类,此类实现了__instancecheck__()和__subclasschenck__()
class MyABC(metaclass=ABCMeta):		#类ABCMeta为类MyABC的Metaclass, 类MyABC为类ABCMeta的一个实例
	pass
MyABC.register(tuple)				#we record inside MyABC the fact that the tuple class shall be identified as a subclass of MyABC itself.可以看做tuple类继承了MyABC
assert issubclass(tuple,MyABC)		#MyABC.register(tuple)将tuple放入了MyABC._abc_registry attribute中
assert isinstance((),MyABC)			# registering a class in an Abstract Base Class with register() does not affect the class hierarchy.

MyABC._abc_registry					#{<weakref at 0xb682966c; to 'type' at 0x83dcca0 (tuple)>}

#################################################################Python重要包####################################################################################################


#####实战中用到的模块与函数###########
#import json   [json.loads(line) for line in open(path)]   json模块中的loads方法可将JSON字符串转化成python字典对象
#dict.item()  返回一个可迭代对象,其元素为元组(key,value)
#collections模块的defaultdict类  collections.defaultdict(类型或函数) 生成字典value的默认值或类型,返回一个可迭代对象
#collections模块的Counter类 Counter(序列) 统计序列中各元素出现次数，返回一个类似于字典(key为元素，value为元素出现次数）的可迭代对象,该迭代对象有个方法most_common(n),返回排名靠前n个,为列表，其元素为二元组（key，value）
#例子：	 为了找出出现最多的时区
#数据前期准备：.txt格式的原始数据----读取到列表中，元素为字典-----提取字典中的时区列tz组成列表，
#			    path='xxx.txt'----records=[json.loads(line) for line in open(path)]----time_zones=[rec['tz'] for rec in records if 'tz' in rec]]
#函数定义： 
#一般处理方法：返回一个字典：key为时区,value为时区出现的次数
			def get_counts(sequence):
				counts={}
				for x in sequence:
					if x in sequence:
						counts[x]+=1
					else:
						counts[x]=1
				return counts
#利用python标准库：
			from collections import defaultdict
			def get_counts2(sequence):
				 counts=defaultdict(int)
				 for x in sequence:
					counts[x]+=1
				 return counts
#取前10位的时区:方法1
			def top_counts(count_dict,n=10):
				value_key_pairs=[(count,tz) for tz,count in count_dict.item()]
				value_key_pairs.sort()
				return value_key_pairs[-n:]
#				方法2		
			from collections import Counter
				counts=Counter(time_zones)
				counts.most_common(10)
						
#####pandas模块##########
# DataFrame  Series类
# 将列表records(其中元素为字典),DataFrame将records变成DataFrame结构，字典中key就变成为列字段,某行在某字段没值,自动填充为NaN
# frame=DataFrame(records)  frame['tz'] (也可用frame.tz) 得到一个Series对象,对应着tz列, Series对象有value_counts()方法,用于对Series进行统计(类似于透视表),结果还是Series对象
#Series对象的函数fillna(str) 将Series中NaN替换成指定的str; 而未知值(空字符串) 也可用布尔型数值索引加以替换 clean_tz[clean_tz=='']='Unknown’  Series对象还有plot()函数用来作图
# DataFrame与Series都可以用布尔型数值索引进行替换选取DataFrame[condition] Series[condition] 返回有condition为True的元素组成的新DataFrame 或 Series
#Series 对象的函数dropna()去掉序列中NaN,仍返回Series 
#Series对象调用函数是将函数逐个用到Series的每个元素,然后将结果重新合成一个序列
#DataFrame与Series对象索引都是从1开始的
#pylab pylab为matplotlib的一部分  import matplotlib.pylab as plt 导入

 





#####numpy包(高性能科学计算和数据分析的基础包)(最后精通面向数组的编程)##########
#numpy ndarray 多维数组(具有矢量算术运算)
#numpy 有用于对整组数据进行快速运算的标准数学函数（无需编写循环）
#numpy 有用于读写磁盘数据的工具以及用于操作内存映射文件的工具
#numpy 线性代数、随机数生成以及傅里叶变化功能
#numpy 用于集成由C C++ Fortran等语言编写的代码的工具
#numpy 提供了一个简单易用的C API,很容易将数据传递给由低级语言编写的外部库，外部库也能以numpy数组形式将数据返回给python
import numpy as np   from numpy import *
np.array()  #将输入数据（列表 元组 数组和其他序列）转化成ndarray,可以显式指定dtype
#ndarray N维数组对象,为大数据集容器,可以利用这种数组对整块数据执行一些数学运算,其语法跟标量元素之间的运算一样。ndarray是个通用的同构数据多维容器
arr.shape	#arr为一个n维数组,返回一个元组tuple(rows,colums)
arr.dtype	#返回数组元素类型，如dtype('int64') 被保存在一个特殊对象dtype对象中,没有特别指定一般为float64
arr.ndim    #返回数组行数
#创建ndarray对象 利用np.array(list 或 list of list)函数  list of list为等长列表组成的列表,会被转换为一个多维数组
np.zeros(10) np.zeros((3,6)) np.zeros([3,6]) #得到全是0
np.zeros_like((1,3,4)) # 得到array([0,0,0]) 以另一数组为参数,根据其形状与dtype创建一个全0数组
np.ones(10)  #得到全是1
np.ones_like([1,2,3]) #得到array([1,1,1]) 以另一数组为参数,根据其形状与dtype创建一个全1数组
np.empty((2,3,2)) #不一定返回的全是0，返回的都是一些未初始化的垃圾值
np.empty_like((1,2,3)) #以另一数组为参数,根据其形状与dtype创建一个数组,其值为一些未初始化的垃圾值
np.arange(n)   #返回0到n-1的array，类似于range()
np.asarray()   #将输入转化成ndarray

















#numpy.where(condition,true-expr,false-expr)  返回numpy array数组




#####################################################python内存机制#############################################################################################
#python的内存机制跟C语言是有区别的,变量更像附在对象上的标签(和引用定义类似)。当变量被绑定在一个对象上时,该变量的引用计数为1.系统会自动维护这些
#标签，并定时扫描，当某标签的引用计数变成0时，该对象就会被回收

