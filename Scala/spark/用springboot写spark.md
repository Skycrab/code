## 打包
可参加pom.xml
需用maven-shade-plugin

## profile

applicaton.properties: spring.profiles.active=@activatedProperties@

application-dev.yaml/application-online.yaml

## 入口

```scala
import com.mnt.feature.monitor.bean.InputParameter
import com.mnt.feature.monitor.handler.HandlerPipeLine
import org.apache.spark.internal.Logging
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.autoconfigure.gson.GsonAutoConfiguration
import org.springframework.boot.autoconfigure.{EnableAutoConfiguration, SpringBootApplication}
import org.springframework.boot.{CommandLineRunner, SpringApplication}

object BootApplication  {
  def main(args: Array[String]): Unit = {
    SpringApplication.run(classOf[Monitor], args:_*)
  }

}

/**
  * 部分版本自动配置依赖版本过高，spark自带版本低，如无需使用，可exclude
  */
@SpringBootApplication
@EnableAutoConfiguration(exclude = Array(classOf[GsonAutoConfiguration]))
class Monitor extends CommandLineRunner with Logging {
  override def run(args: String*): Unit = {
    if(args.length < 1) {
      return
    }
  }

}

```

## 详情

scala bean定义用BeanProperty
```scala
@ConfigurationProperties(prefix = "notify.sms")
@Component
class SmsConfig extends Logging {
  @BeanProperty var url: String = _
}

```

当所有bean都加载完
```scala
@Component
class SourceServiceFactory extends ApplicationListener[ContextRefreshedEvent] with Logging {
  private var sourceMap: Map[String, SourceService] = _

  override def onApplicationEvent(e: ContextRefreshedEvent): Unit = {
    if(e.getApplicationContext.getParent == null) {
      val context = e.getApplicationContext
      val sources = context.getBeansOfType(classOf[SourceService])
      sourceMap = sources.map{case (_, v) => (v.sourceName, v)}.toMap
      logInfo("SourceServiceFactory init")
    }
  }

  def getSourceService(name: String): SourceService = {
    sourceMap.getOrElse(name, throw new MonitorException(s"无${name}数据源，可用类型${sourceMap.keys.toList}"))
  }
}
```

针对一个接口有多个实现的，可以根据名字抽象出通用的具名工场

```
trait HasName {
  def name: String

}


import com.mnt.feature.monitor.bean.MonitorException
import org.apache.spark.internal.Logging
import org.springframework.context.ApplicationListener
import org.springframework.context.event.ContextRefreshedEvent

import scala.collection.JavaConversions.mapAsScalaMap
import scala.reflect._

/**
  * Created by yihaibo on 2019-12-24.
  *
  * 当所有bean加载完执行
  */
class NamedFactory[T <: HasName : ClassTag] extends ApplicationListener[ContextRefreshedEvent] with Logging {
  private var nameMap: Map[String, T] = _

  override def onApplicationEvent(e: ContextRefreshedEvent): Unit = {
    if(e.getApplicationContext.getParent == null) {
      val context = e.getApplicationContext
      val beans = context.getBeansOfType(classTag[T].runtimeClass.asInstanceOf[Class[T]])
      nameMap = beans.map{case (_, v) => (v.name, v)}.toMap
    }
  }

  def getByName(name: String): T = {
    nameMap.getOrElse(name, throw new MonitorException(s"无${name}服务，可用${nameMap.keys.toList}"))
  }

}


trait ProcessStrategy extends HasName{
  /**
    * 处置方法
    * @param columnPsi
    * @param threshold
    */
  def process(columnPsi: ColumnPsi, threshold: Double): Unit

}


@Component
class ProcessStrategyNamedFactory extends NamedFactory[ProcessStrategy]

```

有的时候希望加载用户提供的配置文件，可用PropertySource解决，注意PropertySource默认只支持xml, 通过factory支持yaml

```
/**
 * Created by yihaibo on 2019-12-23.
  *
  * System.setProperty("psi.config", "test");
  *
  * java -jar -Dpsi.config="/home/mkyon/test" example.jar
  *
  * spark-submit: --driver-java-options "-Dlog4j.configuration=file:log4j.properties -Dpsi.config=file:psiConfig.yaml"
  *
  *
 */
@Configuration
@PropertySource(value = Array("${psi.config}"), factory = classOf[ResourceFactory])
@ConfigurationProperties(prefix = "monitor")
class PsiMonitorConfig extends InitializingBean with Logging {

  /**
    * 模式，eager，lazy
    */
  @BeanProperty
  var mode: String = _
}



import org.springframework.beans.factory.config.YamlPropertiesFactoryBean
import org.springframework.core.env.{PropertiesPropertySource, PropertySource}
import org.springframework.core.io.support.{DefaultPropertySourceFactory, EncodedResource}

class ResourceFactory extends DefaultPropertySourceFactory {

  override def createPropertySource(name: String, resource: EncodedResource): PropertySource[_] = {
    val sourceName = if (name == null) resource.getResource.getFilename else name
    assert(sourceName != null)
    if (sourceName.endsWith(".yml") || sourceName.endsWith(".yaml")) {
      val factory = new YamlPropertiesFactoryBean
      factory.setResources(resource.getResource)
      factory.afterPropertiesSet()
      val properties = factory.getObject
      assert(properties != null)
      return new PropertiesPropertySource(sourceName, properties)
    }
    super.createPropertySource(name, resource)
  }
}

```



## 测试

使用thrown
```scala
class InputTest {
  val _thrown = ExpectedException.none
  @Rule
  def thrown = _thrown

  @Test
  def dateErrorTest(): Unit = {
    thrown.expect(classOf[MonitorException])
    thrown.expectMessage("date format must")
    val input = InputParameter("table", "201909-09", "json", "day", "[]")
  }
```

使用MockBean,MockIo
```scala
@RunWith(classOf[SpringRunner])
@SpringBootTest
class FeaturePsiDayImplTest {
  @MockBean
  var catalogService: CatalogService = _

  @Before
  def before(): Unit = {
    val p:Array[Map[String, _]] = Array(
      ListMap("year" -> "2019", "month" -> "09", "day" -> "09")
    )
    when(catalogService.partitions(anyString())).thenReturn(p)
  }

  @Test(expected = classOf[NoSuchDatabaseException])
  def dayPsiTest(): Unit = {
    val input = InputParameter("test", "2019-09-10", "hive", "day", "[]")
    println(catalogService.partitions("test").toList)
  }
}

```

## spark log4j

```shell
spark-submit --class xxx.BootApplication --queue xxx --driver-java-options "-Dlog4j.configuration=file:log4j.properties" --files log4j.properties,application-online.yaml xxx.jar $*
```
```xml
log4j.rootLogger=error, console

log4j.appender.console=org.apache.log4j.ConsoleAppender
log4j.appender.console.target=System.err
log4j.appender.console.layout=org.apache.log4j.PatternLayout
log4j.appender.console.layout.ConversionPattern=%d{yy/MM/dd HH:mm:ss} %p %c{1}: %m%n

log4j.logger.org.springframework=info

log4j.logger.com.mnt=debug, app
log4j.additivity.com.mnt=false
log4j.appender.app=org.apache.log4j.ConsoleAppender
log4j.appender.app.target=System.err
log4j.appender.app.layout=org.apache.log4j.PatternLayout
log4j.appender.app.layout.ConversionPattern=%d{yy/MM/dd HH:mm:ss} %p %c{1}: %m%n
```

## 使用drools
pom.xml一定注意要append kie.conf

```scala
@Configuration
class DroolsConfig {
  @Bean
  def kieContainer(): KieContainer = {
    val kc = KieServices.Factory.get().getKieClasspathContainer()
    kc
  }
}
```

META-INF/kmodule.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<kmodule xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xmlns="http://www.drools.org/xsd/kmodule">
    <kbase packages="com.mnt.feature.monitor.rules.psi">
        <ksession name="psi"/>
    </kbase>

</kmodule>
```

drl定义
```java
package com.mnt.feature.monitor.rules.psi;
global Notify notify;

rule "psi > 0.2"
    when
        $p: ColumnPsi(psi > 0.2);
    then
        notify.notify("PSI超过0.2预警, 详情:" +$p.toReadable());
end
```

```scala
@Service
class PsiColumnListener extends InitializingBean {

  @Autowired
  var kc: KieContainer = _

  @Autowired
  var eventBus: EventBus = _

  @Autowired
  var nt: Notify = _

  override def afterPropertiesSet(): Unit = {
    eventBus.register(this)
  }

  @Subscribe
  def processColumnPsi(columnPsi: ColumnPsi): Unit = {
    val ks = kc.newKieSession("psi")
    ks.setGlobal("notify", nt)
    ks.insert(columnPsi)
    try{
      ks.fireAllRules()
    }finally {
      ks.dispose()
    }
  }
}

```

















