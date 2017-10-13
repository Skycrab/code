##Map倾斜

  1.上游表文件大小不均匀,并且小文件特别多,导致当前表Map端读取数据分布不均匀,引起长尾

  合并小文件,调节mapper.merge.limit.size=64(map数量),mapper.split.size=256(map读取小文件个数)

  2.Map端做聚合，由于某些Map读取文件的某个值特别多而引起长尾,主要指count distinct

```
select ... from
(
  select * from where ds='$ds' distribute by rand()
)left outer join
(小的维度表)
...
```
  发生map join,但分配不均匀，通过'distribute by rand()'会将map端数据随机再分发一次


##Join倾斜

  1.Join的某条输入比较小，可以采用MapJoin,避免分发引起长尾

  2.Join的每条数据都比较大，且长尾是空值导致的，可以将空值处理成随机值，避免聚集
   ```
   select ...
   from a
   left outer join b
   on coalesce(a.key, rand()*999)=b.key
   ```

  3.Join的每条数据都比较大，且长尾是热点值导致的，可以将热点值和非热点值分别处理，再合并数据


##Reduce倾斜

  1.multi count distinct, 修改为group by









