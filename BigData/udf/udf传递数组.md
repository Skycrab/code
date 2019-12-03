## 需求

计算向量间余弦相似度
```sql
add jar hdfs:///xxxx.jar;
create temporary function  CosSim as 'xxx.udf.CosSim';
select CosSim(array(1.0, 2.0), array(4.0, 1.0));
```

## 实现
传递array的udf需要继承GenericUDF

```java
import org.apache.hadoop.hive.ql.exec.UDFArgumentException;
import org.apache.hadoop.hive.ql.metadata.HiveException;
import org.apache.hadoop.hive.ql.udf.generic.GenericUDF;
import org.apache.hadoop.hive.serde2.objectinspector.ListObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspectorUtils;
import org.apache.hadoop.hive.serde2.objectinspector.PrimitiveObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.primitive.PrimitiveObjectInspectorFactory;

import java.util.List;

public class CosSim extends GenericUDF {
  ListObjectInspector left = null;
  ListObjectInspector right = null;

  @Override
  public ObjectInspector initialize(ObjectInspector[] objectInspectors) throws UDFArgumentException {
    left = (ListObjectInspector)objectInspectors[0];
    right = (ListObjectInspector)objectInspectors[1];
    return PrimitiveObjectInspectorFactory.javaDoubleObjectInspector;
  }

  @Override
  public Object evaluate(DeferredObject[] deferredObjects) throws HiveException {
    List<?> a = (List<?>) ObjectInspectorUtils.copyToStandardObject(deferredObjects[0].get(), left);
    List<?> b = (List<?>) ObjectInspectorUtils.copyToStandardObject(deferredObjects[1].get(), right);

    double point_multi = 0;
    double sum_multi1 = 0;
    double sum_multi2 = 0;
    for (int i = 0; i < a.size(); i++) {
      Object lobj = ((PrimitiveObjectInspector)(left.getListElementObjectInspector())).getPrimitiveJavaObject(a.get(i));
      Object robj = ((PrimitiveObjectInspector)(right.getListElementObjectInspector())).getPrimitiveJavaObject(b.get(i));

      double aa = 0;
      double bb = 0;
      if(lobj instanceof Number && robj instanceof Number) {
        Number lnum = (Number) lobj;
        Number rnum = (Number) robj;
        aa = lnum.doubleValue();
        bb = rnum.doubleValue();
      }else {
        aa = Double.parseDouble(lobj.toString());
        bb = Double.parseDouble(robj.toString());
      }

      point_multi += aa * bb;
      sum_multi1 += aa * aa;
      sum_multi2 += bb * bb;
    }
    double result = point_multi / Math.sqrt(sum_multi1 * sum_multi2);
    return result;
  }

  @Override
  public String getDisplayString(String[] strings) {
    return new String();
  }

  //求同维度向量间余弦相似度
  public double evaluate2(double[] a, double[] b) {
    double point_multi = 0;
    double sum_multi1 = 0;
    double sum_multi2 = 0;
    for (int i = 0; i < a.length; i++) {
      point_multi += a[i] * b[i];
      sum_multi1 += a[i] * a[i];
      sum_multi2 += b[i] * b[i];
    }
    return point_multi / Math.sqrt(sum_multi1 * sum_multi2);
  }
}


```
