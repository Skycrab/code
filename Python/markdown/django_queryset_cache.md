#缘起
看着我们单表记录快7000万行，突破亿行已经指日可待了，于是打算数据库分表，对应用层相对透明的做法就是引入数据库中间件，业界虽然有一些方案，比如阿里，360的，但大部分都是java或c的，最后看向了https://github.com/flike/kingshard，这是golang写的，代码质量还是挺高的，对我的胃口，于是先把kingshard当做代理用起来，发现了以前一直没有发现的问题。

###django竟然没有数据库连接池
用kingshard做proxy后发现，连接到kingshard的socket状态都是time_wait，只有kingshard到mysql是一直establish的，这让我很好奇，怀疑django没有使用数据库连接池(当然我们用的django版本比较老，是1.4的)。查询了一下的确是这样，貌似只有1.6版本以后才提供CONN_MAX_AGE这个参数。具体可以参考http://www.huochai.mobi/p/d/752667/?share_tid=85a118bfb04b&fmid=0

###django 在queryset里面再次get(filter)会再次发起sql查询
```
for register_day_obj in self.data['UserRegisterDayObj']:
    xxxxxx
    pay_day_obj = self.data['UserPayDayObj'].get(gameid=register_day_obj.gameid)
    xxxxxx
```
self.data里面都是django的queryset，这样会导致有多少次for循环就会再发多少次sql查询，就是不能忍受的。

为什么在我们项目中一直没有发现呢？ 主要是因为我们系统是bi系统，一次查询都会获取很多数据，由于都是索引查询，一条大的sql语句和100条拆开的sql语句查询时间差不多，由于查询很快，一直也没触发数据库慢查询。这也说明了orm一定要查看发出去的sql语句，django也提供了debug的配置。

那如果修改呢？ 我们知道django的queryset在每次for循环时是缓存的，也就是第一次for时会发出sql请求，以后的for循环会使用已请求的缓存。
那做法就简单了，自定义cache_filter,cache_get方法
```
def cache_filter(queryset, **option):
    """queryset 缓存filter"""
    return [query for query in queryset if all(getattr(query, k) == v for k, v in option.iteritems())]


def cache_get(queryset, **option):
    """queryset 缓存get"""
    result = cache_filter(queryset, **option)
    if len(result) != 1:
        raise ValueError("get should return one record, but now:%s" % len(result))
    return result[0]
```
通过for循环去做，时间复杂度O(n)，尤其是外层还有个for循环，我们可以使用字典去优化一下
```
def fast_cache_filter(queryset, *keys):
    """使用字典加速cache filter"""
    cache = defaultdict(list)

    for query in queryset:
        v = [getattr(query, key) for key in keys]
        cache[tuple(v)].append(query)

    def query_filter(**option):
        assert len(keys)==len(option), "filter keys and option must same"
        return cache.get([option[key] for key in keys], [])

    return query_filter


def fast_cache_get(queryset, *keys):
    """使用字典加速cache get"""
    query_filter = fast_cache_filter(queryset, *keys)

    def query_get(**option):
        result = query_filter(**option)
        if len(result) != 1:
            raise ValueError("get should return one record, but now:%s" % len(result))
        return result[0]

    return query_get
```
当然使用第二种方案侵入性要比第一种高，必须先告诉fast_cache_get函数你的queryset和get的key,fast_cache_get会返回一个函数，这个函数使用就类似了cache_get的用法，典型的闭包。

经过比较，fast版本稍微快10%-20%，但侵入性大，最后我们放弃fast版本，使用for循环的版本。至于为什么只快10%-20%，这个就不是一言两语能够说明白的，这也说明了不要主观判断，一切以数据说话。
