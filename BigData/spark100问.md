# rdd多次map是一次循环还是多次循环?

一次循环

rdd的对给定分区调用compute获取数据源
```
def compute(split: Partition, context: TaskContext): Iterator[T]
```
对map操作是对Iterator调用map操作返回一个Iterator
```
def map[U: ClassTag](f: T => U): RDD[U] = withScope {
    val cleanF = sc.clean(f)
    new MapPartitionsRDD[U, T](this, (context, pid, iter) => iter.map(cleanF))
}
```
而针对Iterator的多次map操作其实是一次循环,看代码也很容易看出来,这里要注意scala原生容器多次map是多个循环
对比如下：

```
    val s = Array(1, 2).iterator
    s.map{x =>
      println(s"a$x")
      x + 1
    }.map{ x =>
      println(s"b$x")
      x + 1
    }.foreach(println)
```
```
a1
b2
3
a2
b3
4
```
如果去掉.iterator，那么就是多次循环了，那对scala集合这两种方案到底谁快？这个问题留给读者了。




