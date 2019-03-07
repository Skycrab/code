
import com.alibaba.ttl.threadpool.TtlExecutors;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.*;

@Configuration
public class FurionExecutor {
    /**
     * 查询线程池
     * 使用TtlExecutors线程池,传递ThreadLocal
     * referer: https://github.com/alibaba/transmittable-thread-local
     * */
    @Bean
    public Executor queryExecutor(){
        int corePoolSize = 50;
        int maximumPoolSize = 100;
        long keepAliveTime = 60;
        BlockingQueue<Runnable> queue = new LinkedBlockingQueue<>(2048);
        ExecutorService executorService = new ThreadPoolExecutor(corePoolSize, maximumPoolSize, keepAliveTime, TimeUnit.SECONDS,
                queue, new ThreadPoolExecutor.CallerRunsPolicy());
        executorService = TtlExecutors.getTtlExecutorService(executorService);

        return executorService;
    }
}
