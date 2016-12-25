##maven使用笔记

### 1.如何把java目录下的资源文件打包到classes目录?

maven会自动将src/main/resources目录下的资源打包，如果要将java目录下也打包，配置如下
```java
<build>
    <resources>
        <resource>
            <directory>src/main/java</directory>
            <includes>
                <include>**/*.xml</include>
            </includes>
        </resource>
    </resources>
</build>
```

### 2.maven配置jetty插件
```java
<build>
        <finalName>chapter1</finalName> <plugins>
        <plugin>
            <groupId>org.mortbay.jetty</groupId>
            <artifactId>jetty-maven-plugin</artifactId>
            <version>7.1.6.v20100715</version>
            <configuration>
                <stopPort>9988</stopPort>
                <stopKey>foo</stopKey>
                <scanIntervalSeconds>5</scanIntervalSeconds>
                <connectors>
                    <connector implementation="org.eclipse.jetty.server.nio.SelectChannelConnector">
                        <port>8888</port>
                        <maxIdleTime>60000</maxIdleTime>
                    </connector>
                </connectors>
                <webAppConfig>
                    <contextPath>/</contextPath>
                </webAppConfig>
            </configuration>
        </plugin>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>2.4.2</version>
            <configuration>
                <skipTests>true</skipTests>
            </configuration>
        </plugin>

        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-war-plugin</artifactId>
            <version>2.4</version>
            <configuration>
                <webResources>
                    <resource>
                        <!-- 元配置文件的目录，相对于pom.xml文件的路径 -->
                        <directory>src/main/webapp/WEB-INF</directory>
                        <!-- 是否过滤文件，也就是是否启动auto-config的功能 -->
                        <filtering>true</filtering>
                        <!-- 目标路径 -->
                        <targetPath>WEB-INF</targetPath>
                    </resource>
                </webResources>
            </configuration>
        </plugin>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId>
            <version>3.1</version>
            <configuration>
                <source>1.7</source>
                <target>1.7</target>
                <encoding>UTF-8</encoding>
            </configuration>
        </plugin>
    </plugins>
</build>
```

