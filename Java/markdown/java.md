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


5.Spring mvc统一异常处理入口
```java
package com.eagle.api.config;

import com.eagle.util.JsonUtil;
import com.eagle.util.response.ResponseUtil;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.Signature;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Configuration;

/**
 * Created by yihaibo on 18/1/3.
 */
@Aspect
@Configuration
public class LogAspect {
    private static final Logger logger = LoggerFactory.getLogger(LogAspect.class);

    @Pointcut("@annotation(org.springframework.web.bind.annotation.PostMapping)")
    public void postMappingPointCut() {}

    @Pointcut("@annotation(org.springframework.web.bind.annotation.GetMapping)")
    public void getMappingPointCut() {}

    @Pointcut("@annotation(org.springframework.web.bind.annotation.RequestMapping)")
    public void requestMappingPointCut() {}

    @Around("postMappingPointCut() || getMappingPointCut() || requestMappingPointCut()")
    public Object logControllerInAndOut(ProceedingJoinPoint joinPoint) throws Throwable {
        Object result;
        long start = System.currentTimeMillis();
        Signature signature = joinPoint.getSignature();
        String param = JsonUtil.encode(joinPoint.getArgs());
        try{
            result = joinPoint.proceed();
            long end = System.currentTimeMillis();
            logger.info("method={}||execute_time={}||param={}||result={}", signature.toString(), end-start, param, JsonUtil.encode(result));
        }catch (Exception e) {
            long end = System.currentTimeMillis();
            result = ResponseUtil.fail();
            logger.error("method={}||execute_time={}||param={}||error=", signature.toString(), end-start, param, e);
        }
        return result;
    }

    @Around("execution(* com.api.service.*.*(..))")
    public Object logServiceInAndOut(ProceedingJoinPoint joinPoint) throws Throwable {
        Object result = null;
        long start = System.currentTimeMillis();
        Signature signature = joinPoint.getSignature();
        String param = JsonUtil.encode(joinPoint.getArgs());
        try{
            result = joinPoint.proceed();
            long end = System.currentTimeMillis();
            logger.info("method={}||execute_time={}||param={}||result={}", signature.toString(), end-start, param, JsonUtil.encode(result));
        }catch (Exception e) {
            long end = System.currentTimeMillis();
            logger.error("method={}||execute_time={}||param={}||error=", signature.toString(), end-start, param, e);
        }
        return result;
    }
}

```





