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

