1.jdk动态代理
依托于接口，会生成接口的子类，子类调用invodehandler.invoke方法

method.invoke是接口，即可调用
```
interface UserService {
    public void add();
}

class UserServiceImpl implements UserService {
    public void add() {
        System.out.println("add");
    }
}

/**
 * Unit test for simple App.
 */
public class AppTest {
    @Test
    public void testMethod() throws Exception {
        Object[] args = null;
        UserService userService = new UserServiceImpl();
        Method m = UserService.class.getMethod("add", new Class[0]);
        m.invoke(userService, args);
    }

}

```

2.json序列化/反序列化typereference

fastJson
```
HttpData<Rule> data = JSON.parseObject(ret, new TypeReference<HttpData<Rule>>() {})
```

Jackson
```
String jsonString="[{'id':'1'},{'id':'2'}]";
ObjectMapper mapper = new ObjectMapper();
List<Bean> beanList = mapper.readValue(jsonString, new TypeReference<List<Bean>>() {});
```

3.单例模式
```
import java.util.Properties;

/**
 * Created by didi on 17/6/7.
 */
public class Conf {
    private static Properties prop = new Properties();
    private static class Holder {
        private static final Conf INSTANCE = new Conf();
    }
    private Conf (){
        try {
            prop.load(Conf.class.getResourceAsStream("/application.properties"));
        }catch (Exception e){
            e.printStackTrace();
        }
    }
    public static final Conf getInstance() {
        return Holder.INSTANCE;
    }
    public String get(String key){
        return prop.getProperty(key);
    }
}

```
4.Fatal error compiling: 无效的目标发行版: 1.8 ->

Perference->Build->Maven->Runner->JRE -> 1.8

Project Setting->Modules->1.8





